import argparse
import asyncio
import csv
import importlib
import inspect
import json
import math
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple


AgentFn = Callable[..., Awaitable[Any]]
ALLOWED_PRIORITIES = {"P1", "P2", "P3"}
FALLBACK_REASONS = {
    "High urgency based on deadline and urgent terms",
    "Action required based on request terms",
    "Low priority or informational content",
}
URGENCY_TERMS = {
    "urgent",
    "deadline",
    "time-sensitive",
    "critical",
    "asap",
    "immediate",
    "today",
    "now",
    "high priority",
    "escalation",
}
STOP_WORDS = {
    "the",
    "and",
    "for",
    "with",
    "that",
    "this",
    "from",
    "have",
    "will",
    "your",
    "please",
    "make",
    "makes",
    "but",
    "not",
    "into",
    "about",
    "need",
    "needs",
    "sent",
    "send",
    "request",
    "requests",
    "priority",
    "reason",
    "because",
    "there",
    "their",
    "them",
    "they",
    "you",
    "are",
    "its",
    "it's",
    "due",
    "before",
    "after",
    "next",
    "week",
    "month",
    "day",
    "deadline",
    "time",
    "within",
    "soon",
    "today",
}


@dataclass
class CaseResult:
    email_id: str
    gold_priority: str
    predicted_priority: str
    gold_reason: str
    predicted_reason: str
    reason_quality: float
    has_urgency_signal: bool
    label_valid: bool
    score_valid: bool
    json_parse_ok: bool
    fallback_used: bool


@dataclass
class AggregateResult:
    cases: List[CaseResult]
    confusion: Dict[Tuple[str, str], int]
    json_errors: int

    @property
    def accuracy(self) -> float:
        correct = sum(1 for c in self.cases if c.gold_priority == c.predicted_priority)
        total = len(self.cases)
        return correct / total if total else 0.0

    @property
    def mean_reason_quality(self) -> float:
        if not self.cases:
            return 0.0
        return sum(c.reason_quality for c in self.cases) / len(self.cases)

    @property
    def fallback_rate(self) -> float:
        if not self.cases:
            return 0.0
        return sum(1 for c in self.cases if c.fallback_used) / len(self.cases)

    def recall_by_label(self, label: str) -> float:
        """Recall = TP / (TP + FN) for a given gold label."""
        tp = self.confusion.get((label, label), 0)
        fn = sum(
            self.confusion.get((label, pred), 0)
            for pred in ALLOWED_PRIORITIES
            if pred != label
        )
        denom = tp + fn
        return tp / denom if denom else 0.0

    @property
    def macro_recall(self) -> float:
        """Mean recall across all allowed priority labels."""
        if not ALLOWED_PRIORITIES:
            return 0.0
        recalls = [self.recall_by_label(label) for label in ALLOWED_PRIORITIES]
        return sum(recalls) / len(recalls)


def load_agent(path: str) -> AgentFn:
    if ":" not in path:
        raise ValueError("--agent must be in 'module:function' format")
    module_name, func_name = path.split(":", 1)
    module = importlib.import_module(module_name)
    func = getattr(module, func_name, None)
    if func is None:
        raise AttributeError(f"Function '{func_name}' not found in module '{module_name}'")
    if not callable(func):
        raise TypeError(f"Loaded object '{func_name}' is not callable")
    return func  # type: ignore[return-value]


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def load_python_dataset(target: str) -> List[Dict[str, Any]]:
    """
    Allow users to point to a python list (e.g. tests.data.priority_test_emails:PRIORITY_TEST_EMAILS)
    so we can keep curated datasets in code without exporting JSONL.
    """
    if ":" not in target:
        raise ValueError("--py_data must be in 'module:attribute' format")
    module_name, attr_name = target.split(":", 1)
    module = importlib.import_module(module_name)
    data = getattr(module, attr_name, None)
    if data is None:
        raise AttributeError(f"Attribute '{attr_name}' not found in module '{module_name}'")
    if not isinstance(data, list):
        raise TypeError("--py_data target must resolve to a list of dict cases")
    return data


def ensure_parent_dir(path: Optional[Path]) -> None:
    if path is None:
        return
    if path.name:
        path.parent.mkdir(parents=True, exist_ok=True)


def tokenize_meaningful(text: str) -> List[str]:
    tokens = re.findall(r"[a-zA-Z']+", text.lower())
    return [t for t in tokens if len(t) > 2 and t not in STOP_WORDS]


def keyword_overlap_score(gold_reason: str, pred_reason: str) -> float:
    gold_tokens = tokenize_meaningful(gold_reason)
    if not gold_tokens:
        return 0.0
    pred_tokens = set(tokenize_meaningful(pred_reason))
    overlap = sum(1 for token in gold_tokens if token in pred_tokens)
    return overlap / len(gold_tokens)


def detect_urgency(reason: str) -> bool:
    reason_lower = reason.lower()
    return any(term in reason_lower for term in URGENCY_TERMS)


def extract_prediction_fields(result: Any) -> Tuple[str, str, Optional[float], bool, bool, bool]:
    label: Optional[str] = None
    reason: str = ""
    score: Optional[float] = None
    json_ok = True
    fallback_used = False
    label_valid = True

    def update_from_dict(data: Dict[str, Any]) -> None:
        nonlocal label, reason, score
        if label is None:
            label = data.get("label") or data.get("priority") or data.get("priority_label")
        if not reason:
            if isinstance(data.get("reasons"), list) and data["reasons"]:
                reason_candidate = data["reasons"][0]
                if isinstance(reason_candidate, str):
                    reason = reason_candidate
            if not reason and isinstance(data.get("reason"), str):
                reason = data["reason"]
        if score is None:
            raw_score = data.get("score")
            if isinstance(raw_score, (int, float)):
                score = float(raw_score)

    if isinstance(result, dict):
        update_from_dict(result)
    elif hasattr(result, "dict") and callable(result.dict):
        try:
            data = result.dict()
            update_from_dict(data)
        except Exception:
            json_ok = False
    elif isinstance(result, str):
        parsed: Optional[Any] = None
        try:
            parsed = json.loads(result)
        except json.JSONDecodeError:
            json_ok = False
        if isinstance(parsed, dict):
            update_from_dict(parsed)
        else:
            if not reason:
                reason = result
    else:
        if hasattr(result, "label"):
            label = getattr(result, "label")
        if hasattr(result, "reasons"):
            reasons_value = getattr(result, "reasons")
            if isinstance(reasons_value, list) and reasons_value:
                reason_candidate = reasons_value[0]
                if isinstance(reason_candidate, str):
                    reason = reason_candidate
        elif hasattr(result, "reason"):
            reason_attr = getattr(result, "reason")
            if isinstance(reason_attr, str):
                reason = reason_attr
        if hasattr(result, "score"):
            score_value = getattr(result, "score")
            if isinstance(score_value, (int, float)):
                score = float(score_value)

    if label is None:
        label = "UNKNOWN"
        label_valid = False
    else:
        label = str(label)
        if label not in ALLOWED_PRIORITIES:
            label_valid = False

    fallback_used = reason in FALLBACK_REASONS

    return label, reason, score, json_ok, fallback_used, label_valid


def validate_score(label: str, score: Optional[float]) -> bool:
    if score is None:
        return False
    if not isinstance(score, (int, float)):
        return False
    if math.isnan(score) or math.isinf(score):
        return False
    expected = {"P1": 0.85, "P2": 0.55, "P3": 0.25}
    if label in expected:
        return abs(score - expected[label]) <= 0.15
    return False


def format_messages(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    formatted = []
    for msg in messages:
        formatted.append(
            {
                "subject": msg.get("subject", ""),
                "from_": msg.get("from_", ""),
                "clean_body": msg.get("clean_body", msg.get("body", "")),
            }
        )
    return formatted


async def invoke_agent(agent: AgentFn, signature: inspect.Signature, row: Dict[str, Any]) -> Any:
    kwargs: Dict[str, Any] = {}
    params = signature.parameters
    if "messages" in params:
        kwargs["messages"] = row.get("messages", [])
    if "tasks" in params:
        kwargs["tasks"] = row.get("tasks", [])
    if "personalized_keywords" in params:
        kwargs["personalized_keywords"] = row.get("personalized_keywords", [])
    result = await agent(**kwargs)  # type: ignore[misc]
    return result


async def evaluate_dataset(
    data: List[Dict[str, Any]],
    agent: AgentFn,
    csv_out: Optional[Path],
    json_out: Optional[Path],
) -> AggregateResult:
    signature = inspect.signature(agent)
    cases: List[CaseResult] = []
    confusion: Dict[Tuple[str, str], int] = defaultdict(int)
    csv_rows: List[Dict[str, str]] = []
    json_records: List[Dict[str, Any]] = []
    json_errors = 0

    for row in data:
        result = await invoke_agent(agent, signature, row)
        label, reason, score, json_ok, fallback_used, label_valid = extract_prediction_fields(result)
        if not json_ok:
            json_errors += 1

        score_valid = validate_score(label, score)
        has_urgency = detect_urgency(reason)
        reason_score = keyword_overlap_score(row.get("gold_reason", ""), reason)
        gold_priority = row.get("gold_priority", "UNKNOWN")
        confusion[(gold_priority, label)] += 1

        cases.append(
            CaseResult(
                email_id=row.get("id", ""),
                gold_priority=gold_priority,
                predicted_priority=label,
                gold_reason=row.get("gold_reason", ""),
                predicted_reason=reason,
                reason_quality=reason_score,
                has_urgency_signal=has_urgency,
                label_valid=label_valid,
                score_valid=score_valid,
                json_parse_ok=json_ok,
                fallback_used=fallback_used,
            )
        )

        if label != gold_priority:
            csv_rows.append(
                {
                    "email_id": row.get("id", ""),
                    "gold_priority": gold_priority,
                    "predicted_priority": label,
                    "gold_reason": row.get("gold_reason", ""),
                    "predicted_reason": reason,
                }
            )

        json_records.append(
            {
                "id": row.get("id", ""),
                "messages": format_messages(row.get("messages", [])),
                "gold_priority": gold_priority,
                "predicted_priority": label,
                "gold_reason": row.get("gold_reason", ""),
                "predicted_reason": reason,
                "reason_quality_score": reason_score,
                "has_urgency_signal": has_urgency,
                "confusion_bucket": f"{gold_priority}->{label}",
                "label_valid": label_valid,
                "score_valid": score_valid,
                "json_parse_ok": json_ok,
                "fallback_used": fallback_used,
                "raw_score": score,
            }
        )

    if csv_out:
        ensure_parent_dir(csv_out)
        with csv_out.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "email_id",
                    "gold_priority",
                    "predicted_priority",
                    "gold_reason",
                    "predicted_reason",
                ],
            )
            writer.writeheader()
            writer.writerows(csv_rows)

    if json_out:
        ensure_parent_dir(json_out)
        with json_out.open("w", encoding="utf-8") as handle:
            json.dump(json_records, handle, ensure_ascii=False, indent=2)

    return AggregateResult(cases=cases, confusion=dict(confusion), json_errors=json_errors)


def print_confusion_matrix(confusion: Dict[Tuple[str, str], int]) -> None:
    labels = sorted(ALLOWED_PRIORITIES)
    print("Confusion Matrix (gold -> predicted)")
    header = "        " + " ".join(f"{label:>6}" for label in labels)
    print(header)
    for gold in labels:
        row = [f"{gold:>6}"]
        for pred in labels:
            row.append(f"{confusion.get((gold, pred), 0):>6}")
        print(" ".join(row))


def print_summary(aggregate: AggregateResult) -> None:
    total = len(aggregate.cases)
    print("\nPrioritizer Evaluation Summary")
    print("--------------------------------")
    print(f"Total cases evaluated: {total}")
    print(f"Priority Accuracy (overall): {aggregate.accuracy:.4f}")
    print("Recall by priority label:")
    for label in sorted(ALLOWED_PRIORITIES):
        print(f"  {label}: {aggregate.recall_by_label(label):.4f}")
    print(f"Macro Recall: {aggregate.macro_recall:.4f}")
    print(f"Mean Reason Quality Score: {aggregate.mean_reason_quality:.4f}")
    print(f"Fallback Rate: {aggregate.fallback_rate:.2%}")
    print(f"JSON Parse Errors: {aggregate.json_errors}")
    label_valid_rate = sum(1 for c in aggregate.cases if c.label_valid) / total if total else 0.0
    score_valid_rate = sum(1 for c in aggregate.cases if c.score_valid) / total if total else 0.0
    urgency_rate = sum(1 for c in aggregate.cases if c.has_urgency_signal) / total if total else 0.0
    print(f"Label Validity Rate: {label_valid_rate:.2%}")
    print(f"Score Validity Rate: {score_valid_rate:.2%}")
    print(f"Urgency Signal Presence: {urgency_rate:.2%}")
    print_confusion_matrix(aggregate.confusion)


async def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate prioritizer outputs against gold annotations.")
    parser.add_argument(
        "--data",
        type=Path,
        default=Path("tests/data/prioritizer_gold.jsonl"),
        help="Path to prioritizer gold JSONL dataset.",
    )
    parser.add_argument(
        "--agent",
        required=True,
        help="Agent function in 'module:function' format.",
    )
    parser.add_argument(
        "--py_data",
        help="Optional python dataset reference in 'module:LIST_NAME' format. Overrides --data when provided.",
    )
    parser.add_argument(
        "--csv_out",
        type=Path,
        default=None,
        help="Optional path for CSV export of FP/FN cases.",
    )
    parser.add_argument(
        "--per_case_dump",
        type=Path,
        default=None,
        help="Optional path for per-case JSON dump.",
    )

    args = parser.parse_args()

    if args.py_data:
        data = load_python_dataset(args.py_data)
    else:
        if not args.data.exists():
            raise FileNotFoundError(f"Data file not found: {args.data}")
        data = read_jsonl(args.data)

    agent = load_agent(args.agent)

    aggregate = await evaluate_dataset(
        data=data,
        agent=agent,
        csv_out=args.csv_out,
        json_out=args.per_case_dump,
    )

    print_summary(aggregate)


if __name__ == "__main__":
    asyncio.run(main())
