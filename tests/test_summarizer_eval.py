import argparse
import asyncio
import csv
import importlib
import inspect
import json
import re
from collections import Counter
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, Iterable, List, Optional, Tuple


RougeScores = Tuple[float, float]
FactDict = Dict[str, Optional[str]]
AgentFn = Callable[..., Awaitable[Any]]


ACTION_VERBS = {
    "ask", "asks", "remind", "reminds", "invite", "invites",
    "announce", "announces", "notify", "notifies", "request", "requests",
    "report", "reports", "lead", "leads", "coordinate", "coordinates",
    "discuss", "discusses", "promise", "promises", "share", "shares",
    "guide", "guides", "confirm", "confirms", "review", "reviews",
    "submit", "submits", "upload", "uploads", "draft", "drafts",
    "align", "aligns", "prepare", "prepares", "finalize", "finalizes"
}

FACT_KEYS = ("actor", "action", "object", "deadline")

STRICT_MATCH_THRESHOLD = 0.78
PARTIAL_MATCH_THRESHOLD = 0.55
FACT_STOPWORDS = {"the", "a", "an", "to", "for", "with", "on", "at"}


def normalize_fact_text(value: Optional[str]) -> str:
    if not value:
        return ""
    lowered = value.lower().strip()
    cleaned = re.sub(r"[^\w\s]", " ", lowered)
    tokens = [tok for tok in cleaned.split() if tok and tok not in FACT_STOPWORDS]
    return " ".join(tokens)


def fact_similarity(gold: Optional[str], pred: Optional[str]) -> float:
    if not gold or not pred:
        return 0.0
    gold_norm = normalize_fact_text(gold)
    pred_norm = normalize_fact_text(pred)
    if not gold_norm or not pred_norm:
        return 0.0
    if gold_norm in pred_norm or pred_norm in gold_norm:
        return 1.0
    return SequenceMatcher(None, gold_norm, pred_norm).ratio()


@dataclass
class CaseResult:
    email_id: str
    rouge1: float
    rouge_l: float
    fact_precision: float
    fact_recall: float
    fact_strict_tp: int
    fact_partial_tp: int
    fact_fp: int
    fact_fn: int
    has_action_verb: bool
    starts_with_sender: bool
    length_ok: bool
    ends_with_period: bool
    json_parse_ok: bool
    word_count: int

    @property
    def fact_tp(self) -> int:
        return self.fact_strict_tp + self.fact_partial_tp


@dataclass
class AggregateResult:
    cases: List[CaseResult]
    strict_tp: int = 0
    partial_tp: int = 0
    fp: int = 0
    fn: int = 0
    per_fact_totals: Dict[str, int] = field(default_factory=lambda: {key: 0 for key in FACT_KEYS})
    per_fact_strict: Dict[str, int] = field(default_factory=lambda: {key: 0 for key in FACT_KEYS})
    per_fact_partial: Dict[str, int] = field(default_factory=lambda: {key: 0 for key in FACT_KEYS})

    @property
    def rouge1_mean(self) -> float:
        return _mean([c.rouge1 for c in self.cases])

    @property
    def rougel_mean(self) -> float:
        return _mean([c.rouge_l for c in self.cases])

    @property
    def fact_precision(self) -> float:
        tp = self.strict_tp + self.partial_tp
        denom = tp + self.fp
        return tp / denom if denom else 0.0

    @property
    def fact_recall(self) -> float:
        tp = self.strict_tp + self.partial_tp
        denom = tp + self.fn
        return tp / denom if denom else 0.0

    @property
    def fact_f1(self) -> float:
        prec = self.fact_precision
        rec = self.fact_recall
        denom = prec + rec
        return 2 * prec * rec / denom if denom else 0.0

    def fact_accuracy(self, fact_type: str, include_partial: bool = False) -> Optional[float]:
        total = self.per_fact_totals.get(fact_type, 0)
        if not total:
            return None
        strict = self.per_fact_strict.get(fact_type, 0)
        partial = self.per_fact_partial.get(fact_type, 0) if include_partial else 0
        return (strict + partial) / total

    def compliance_rate(self, attr: str) -> float:
        values = [getattr(c, attr) for c in self.cases]
        return sum(1 for v in values if v) / len(values) if values else 0.0


def _mean(values: Iterable[float]) -> float:
    values = list(values)
    return sum(values) / len(values) if values else 0.0


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


def extract_sender_name(sender: str) -> str:
    if not sender:
        return "They"
    match = re.match(r"^([^<]+)", sender)
    if match:
        name = match.group(1).strip()
        return name.split()[0] if name else "They"
    email_match = re.match(r"^([^@]+)", sender)
    if email_match:
        username = email_match.group(1)
        return username.split(".")[0].capitalize()
    return "They"


def tokenize(text: str) -> List[str]:
    return re.findall(r"[\w']+", text.lower())


def rouge_n_recall(reference: List[str], hypothesis: List[str], n: int = 1) -> float:
    if len(reference) < n:
        return 0.0
    ref_ngrams = Counter(tuple(reference[i : i + n]) for i in range(len(reference) - n + 1))
    hyp_ngrams = Counter(tuple(hypothesis[i : i + n]) for i in range(len(hypothesis) - n + 1))
    overlap = sum(min(count, hyp_ngrams[gram]) for gram, count in ref_ngrams.items())
    total = sum(ref_ngrams.values())
    return overlap / total if total else 0.0


def lcs_length(a: List[str], b: List[str]) -> int:
    if not a or not b:
        return 0
    dp = [0] * (len(b) + 1)
    for token in a:
        prev = 0
        for j, other in enumerate(b, 1):
            temp = dp[j]
            if token == other:
                dp[j] = prev + 1
            else:
                dp[j] = max(dp[j], dp[j - 1])
            prev = temp
    return dp[-1]


def rouge_l_recall(reference: List[str], hypothesis: List[str]) -> float:
    if not reference:
        return 0.0
    lcs = lcs_length(reference, hypothesis)
    return lcs / len(reference)


def extract_predicted_facts(summary: str) -> FactDict:
    facts: FactDict = {key: None for key in FACT_KEYS}
    text = summary.strip()
    if not text:
        return facts

    verb_pattern = "|".join(sorted(ACTION_VERBS, key=len, reverse=True))
    actor_regex = re.compile(rf"^(?P<actor>.+?)\s+(?P<verb>{verb_pattern})\b", re.IGNORECASE)
    actor_match = actor_regex.search(text)
    rest_start = 0
    if actor_match:
        raw_actor = actor_match.group("actor").strip(" ,")
        facts["actor"] = raw_actor
        verb = actor_match.group("verb").lower()
        facts["action"] = normalize_action_verb(verb)
        rest_start = actor_match.end()
    else:
        actor_only = re.match(r"([A-Z][\w]*(?:\s+[A-Z][\w]*)*)", text)
        if actor_only:
            facts["actor"] = actor_only.group(1)
        rest_start = len(actor_only.group(0)) if actor_only else 0

    rest = text[rest_start:].strip()
    if rest:
        to_match = re.search(r"\bto\s+([^.;]+)", rest, re.IGNORECASE)
        if to_match:
            action_phrase = to_match.group(1).strip()
            verb_match = re.match(r"([a-z]+(?:\s+and\s+[a-z]+)?)", action_phrase, re.IGNORECASE)
            if verb_match:
                facts["action"] = facts["action"] or verb_match.group(1).lower()
                object_phrase = action_phrase[verb_match.end():].strip(" ,.")
                facts["object"] = object_phrase if object_phrase else facts["object"]
            else:
                facts["object"] = action_phrase
        else:
            about_match = re.search(r"\babout\s+([^.;]+)", rest, re.IGNORECASE)
            if about_match:
                facts["object"] = about_match.group(1).strip(" ,.")

    deadline_match = re.search(r"\b(by|before|on|at|from|today|tonight|tomorrow|eod|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b[^.]*", text, re.IGNORECASE)
    if deadline_match:
        facts["deadline"] = deadline_match.group(0).strip(" ,.")

    return facts


def normalize_action_verb(verb: str) -> str:
    verb = verb.lower()
    replacements = {
        "asks": "ask",
        "reminds": "remind",
        "invites": "invite",
        "announces": "announce",
        "notifies": "notify",
        "requests": "request",
        "reports": "report",
        "leads": "lead",
        "coordinates": "coordinate",
        "discusses": "discuss",
        "promises": "promise",
        "shares": "share",
        "guides": "guide",
        "confirms": "confirm",
        "reviews": "review",
        "submits": "submit",
        "uploads": "upload",
        "drafts": "draft",
        "aligns": "align",
        "prepares": "prepare",
        "finalizes": "finalize"
    }
    return replacements.get(verb, verb)


@dataclass
class FactScore:
    strict_tp: int
    partial_tp: int
    fp: int
    fn: int
    field_totals: Dict[str, int]
    field_strict: Dict[str, int]
    field_partial: Dict[str, int]
    detail_rows: List[Dict[str, Any]]
    fn_records: List[Dict[str, str]]
    fp_records: List[Dict[str, str]]


def score_facts(gold: Dict[str, str], pred: FactDict) -> FactScore:
    strict_tp = partial_tp = fp = fn = 0
    field_totals = {key: 0 for key in FACT_KEYS}
    field_strict = {key: 0 for key in FACT_KEYS}
    field_partial = {key: 0 for key in FACT_KEYS}
    detail_rows: List[Dict[str, Any]] = []
    fn_records: List[Dict[str, str]] = []
    fp_records: List[Dict[str, str]] = []

    for key in FACT_KEYS:
        gold_val = gold.get(key)
        pred_val = pred.get(key)

        if gold_val:
            field_totals[key] += 1

        if gold_val and pred_val:
            similarity = fact_similarity(gold_val, pred_val)
            if similarity >= STRICT_MATCH_THRESHOLD:
                strict_tp += 1
                field_strict[key] += 1
                detail_rows.append({
                    "fact_type": key,
                    "status": "strict",
                    "similarity": similarity,
                    "gold": gold_val,
                    "pred": pred_val,
                })
            elif similarity >= PARTIAL_MATCH_THRESHOLD:
                partial_tp += 1
                field_partial[key] += 1
                detail_rows.append({
                    "fact_type": key,
                    "status": "partial",
                    "similarity": similarity,
                    "gold": gold_val,
                    "pred": pred_val,
                })
            else:
                fn += 1
                fp += 1
                detail_rows.append({
                    "fact_type": key,
                    "status": "mismatch",
                    "similarity": similarity,
                    "gold": gold_val,
                    "pred": pred_val,
                })
                fn_records.append({
                    "fact_type": key,
                    "status": "mismatch",
                    "gold": gold_val,
                    "pred": pred_val,
                })
                fp_records.append({
                    "fact_type": key,
                    "status": "mismatch",
                    "gold": gold_val,
                    "pred": pred_val,
                })
        elif gold_val and not pred_val:
            fn += 1
            detail_rows.append({
                "fact_type": key,
                "status": "missing_pred",
                "similarity": 0.0,
                "gold": gold_val,
                "pred": "",
            })
            fn_records.append({
                "fact_type": key,
                "status": "missing_pred",
                "gold": gold_val,
                "pred": "",
            })
        elif pred_val and not gold_val:
            fp += 1
            detail_rows.append({
                "fact_type": key,
                "status": "spurious",
                "similarity": 0.0,
                "gold": "",
                "pred": pred_val,
            })
            fp_records.append({
                "fact_type": key,
                "status": "spurious",
                "gold": "",
                "pred": pred_val,
            })

    return FactScore(
        strict_tp=strict_tp,
        partial_tp=partial_tp,
        fp=fp,
        fn=fn,
        field_totals=field_totals,
        field_strict=field_strict,
        field_partial=field_partial,
        detail_rows=detail_rows,
        fn_records=fn_records,
        fp_records=fp_records,
    )


def has_action(summary: str) -> bool:
    text = summary.lower()
    return any(verb in text for verb in ACTION_VERBS)


def starts_with_sender(summary: str, sender: str) -> bool:
    expected = extract_sender_name(sender).lower()
    actual = summary.strip().lower()
    return actual.startswith(expected)


def ends_with_period(summary: str) -> bool:
    return summary.strip().endswith(".")


def word_count(summary: str) -> int:
    return len(summary.strip().split()) if summary.strip() else 0


def ensure_parent_dir(path: Optional[Path]) -> None:
    if path is None:
        return
    if path.name:
        path.parent.mkdir(parents=True, exist_ok=True)


async def evaluate_dataset(
    data: List[Dict[str, Any]],
    agent: AgentFn,
    max_words: int,
    csv_out: Optional[Path],
    json_out: Optional[Path],
    max_examples: int,
) -> AggregateResult:
    results: List[CaseResult] = []
    per_case_dump: List[Dict[str, Any]] = []
    csv_rows: List[Dict[str, str]] = []
    strict_tp_total = partial_tp_total = fp_total = fn_total = 0
    per_fact_totals = {key: 0 for key in FACT_KEYS}
    per_fact_strict = {key: 0 for key in FACT_KEYS}
    per_fact_partial = {key: 0 for key in FACT_KEYS}
    fn_examples: List[Dict[str, Any]] = []
    fp_examples: List[Dict[str, Any]] = []
    signature = inspect.signature(agent)
    for row in data:
        summary, json_ok = await invoke_agent(agent, signature, row, max_words)
        summary = summary.strip()
        gold_summary = row.get("gold_summary", "").strip()

        ref_tokens = tokenize(gold_summary)
        hyp_tokens = tokenize(summary)
        rouge1 = rouge_n_recall(ref_tokens, hyp_tokens, n=1)
        rouge_l = rouge_l_recall(ref_tokens, hyp_tokens)

        pred_facts = extract_predicted_facts(summary)
        gold_facts = row.get("key_facts", {})
        fact_score = score_facts(gold_facts, pred_facts)

        strict_tp_total += fact_score.strict_tp
        partial_tp_total += fact_score.partial_tp
        fp_total += fact_score.fp
        fn_total += fact_score.fn
        for key in FACT_KEYS:
            per_fact_totals[key] += fact_score.field_totals[key]
            per_fact_strict[key] += fact_score.field_strict[key]
            per_fact_partial[key] += fact_score.field_partial[key]

        fact_tp = fact_score.strict_tp + fact_score.partial_tp
        pred_count = fact_tp + fact_score.fp
        gold_count = fact_tp + fact_score.fn
        fact_prec = fact_tp / pred_count if pred_count else 0.0
        fact_rec = fact_tp / gold_count if gold_count else 0.0

        for detail in fact_score.detail_rows:
            if detail["status"] == "strict":
                continue
            csv_rows.append({
                "email_id": row.get("id", ""),
                "subject": row.get("subject", ""),
                "fact_type": detail["fact_type"],
                "status": detail["status"],
                "similarity": f"{detail['similarity']:.2f}",
                "gold": detail["gold"],
                "pred": detail["pred"],
            })
        for fn_record in fact_score.fn_records:
            fn_examples.append({
                "email_id": row.get("id", ""),
                "subject": row.get("subject", ""),
                **fn_record,
            })
        for fp_record in fact_score.fp_records:
            fp_examples.append({
                "email_id": row.get("id", ""),
                "subject": row.get("subject", ""),
                **fp_record,
            })

        contains_action = has_action(summary)
        sender_starts = starts_with_sender(summary, row.get("sender", ""))
        length_ok = word_count(summary) <= max_words
        ends_period = ends_with_period(summary)
        wc = word_count(summary)

        results.append(
            CaseResult(
                email_id=row.get("id", ""),
                rouge1=rouge1,
                rouge_l=rouge_l,
                fact_precision=fact_prec,
                fact_recall=fact_rec,
                fact_strict_tp=fact_score.strict_tp,
                fact_partial_tp=fact_score.partial_tp,
                fact_fp=fact_score.fp,
                fact_fn=fact_score.fn,
                has_action_verb=contains_action,
                starts_with_sender=sender_starts,
                length_ok=length_ok,
                ends_with_period=ends_period,
                json_parse_ok=json_ok,
                word_count=wc,
            )
        )

        per_case_dump.append(
            {
                "id": row.get("id", ""),
                "subject": row.get("subject", ""),
                "body": row.get("body") or row.get("messages"),
                "sender": row.get("sender", ""),
                "gold_summary": gold_summary,
                "predicted_summary": summary,
                "rouge1": rouge1,
                "rougeL": rouge_l,
                "gold_facts": gold_facts,
                "pred_facts": pred_facts,
                "fact_precision": fact_prec,
                "fact_recall": fact_rec,
                "fact_strict_tp": fact_score.strict_tp,
                "fact_partial_tp": fact_score.partial_tp,
                "fact_fp": fact_score.fp,
                "fact_fn": fact_score.fn,
                "fact_details": fact_score.detail_rows,
                "has_action_verb": contains_action,
                "starts_with_sender": sender_starts,
                "length_ok": length_ok,
                "ends_with_period": ends_period,
                "json_parse_ok": json_ok,
                "word_count": wc,
            }
        )

    if csv_out:
        ensure_parent_dir(csv_out)
        with csv_out.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["email_id", "subject", "fact_type", "status", "similarity", "gold", "pred"],
            )
            writer.writeheader()
            writer.writerows(csv_rows)

    if json_out:
        ensure_parent_dir(json_out)
        with json_out.open("w", encoding="utf-8") as handle:
            json.dump(per_case_dump, handle, ensure_ascii=False, indent=2)

    _report_examples(fn_examples[:max_examples], fp_examples[:max_examples])

    return AggregateResult(
        cases=results,
        strict_tp=strict_tp_total,
        partial_tp=partial_tp_total,
        fp=fp_total,
        fn=fn_total,
        per_fact_totals=per_fact_totals,
        per_fact_strict=per_fact_strict,
        per_fact_partial=per_fact_partial,
    )


def _report_examples(fn_examples: List[Dict[str, Any]], fp_examples: List[Dict[str, Any]]) -> None:
    if fn_examples:
        print("\nSample fact FN cases:")
        for example in fn_examples:
            print(
                "  - "
                f"id={example.get('email_id')} | subject={example.get('subject')!r} | "
                f"type={example.get('fact_type')} | status={example.get('status')} | "
                f"gold={example.get('gold')!r} | pred={example.get('pred')!r}"
            )
    if fp_examples:
        print("\nSample fact FP cases:")
        for example in fp_examples:
            print(
                "  - "
                f"id={example.get('email_id')} | subject={example.get('subject')!r} | "
                f"type={example.get('fact_type')} | status={example.get('status')} | "
                f"gold={example.get('gold')!r} | pred={example.get('pred')!r}"
            )


async def invoke_agent(agent: AgentFn, signature: inspect.Signature, row: Dict[str, Any], max_words: int) -> Tuple[str, bool]:
    kwargs: Dict[str, Any] = {}
    params = signature.parameters

    if "subject" in params:
        kwargs["subject"] = row.get("subject", "")
    if "text" in params:
        if "body" in row:
            kwargs["text"] = row.get("body", "")
        elif "messages" in row:
            kwargs["text"] = format_thread_text(row["messages"])
    if "sender" in params:
        kwargs["sender"] = row.get("sender", "")
    if "messages" in params and "messages" in row:
        kwargs["messages"] = row["messages"]
    if "max_length" in params:
        kwargs["max_length"] = max_words

    # Fallback: if agent expects "text" but none provided, synthesize from messages
    if "text" in params and "text" not in kwargs and "messages" in row:
        kwargs["text"] = format_thread_text(row["messages"])

    result = await agent(**kwargs)  # type: ignore[misc]

    json_ok = True
    summary_text: str

    if isinstance(result, dict):
        summary_text = str(result.get("summary", ""))
    elif isinstance(result, str):
        parsed: Optional[Any] = None
        try:
            parsed = json.loads(result)
        except json.JSONDecodeError:
            json_ok = False
        if isinstance(parsed, dict) and "summary" in parsed:
            summary_text = str(parsed.get("summary", ""))
        else:
            summary_text = result
    else:
        json_ok = False
        summary_text = str(result)

    return summary_text, json_ok


def format_thread_text(messages: List[Dict[str, Any]]) -> str:
    parts = []
    for msg in messages:
        speaker = msg.get("from_", "")
        body = msg.get("clean_body") or msg.get("body") or ""
        parts.append(f"{speaker}: {body}")
    return "\n".join(parts)


def print_summary(aggregate: AggregateResult, total_cases: int) -> None:
    print("\nSummarizer Evaluation Summary")
    print("--------------------------------")
    print(f"Total cases evaluated: {total_cases}")
    print(f"Mean ROUGE-1 Recall: {aggregate.rouge1_mean:.4f}")
    print(f"Mean ROUGE-L Recall: {aggregate.rougel_mean:.4f}")
    print(f"Fact TP (strict): {aggregate.strict_tp}")
    print(f"Fact TP (partial): {aggregate.partial_tp}")
    print(f"Fact FP: {aggregate.fp}")
    print(f"Fact FN: {aggregate.fn}")
    print(f"Key Fact Precision: {aggregate.fact_precision:.4f}")
    print(f"Key Fact Recall: {aggregate.fact_recall:.4f}")
    print(f"Key Fact F1: {aggregate.fact_f1:.4f}")
    print("Fact Slot Accuracy (strict only):")
    for key in FACT_KEYS:
        acc = aggregate.fact_accuracy(key)
        display = f"{acc:.2%}" if acc is not None else "N/A"
        print(f"  {key.title()}: {display}")
    print("Fact Slot Coverage (strict+partial):")
    for key in FACT_KEYS:
        acc = aggregate.fact_accuracy(key, include_partial=True)
        display = f"{acc:.2%}" if acc is not None else "N/A"
        print(f"  {key.title()}: {display}")
    print("Compliance Rates:")
    print(f"  Action Verb: {aggregate.compliance_rate('has_action_verb'):.2%}")
    print(f"  Starts With Sender: {aggregate.compliance_rate('starts_with_sender'):.2%}")
    print(f"  Length OK: {aggregate.compliance_rate('length_ok'):.2%}")
    print(f"  Ends With Period: {aggregate.compliance_rate('ends_with_period'):.2%}")
    print(f"  JSON Parse OK: {aggregate.compliance_rate('json_parse_ok'):.2%}")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate summarizer outputs against gold data.")
    parser.add_argument(
        "--data",
        type=Path,
        default=Path("tests/data/summarizer_gold.jsonl"),
        help="Path to summarizer gold JSONL dataset.",
    )
    parser.add_argument(
        "--agent",
        required=True,
        help="Agent function in 'module:function' format.",
    )
    parser.add_argument(
        "--csv_out",
        type=Path,
        default=None,
        help="Optional path for CSV export of fact mismatches.",
    )
    parser.add_argument(
        "--per_case_dump",
        type=Path,
        default=None,
        help="Optional path for per-case JSON dump.",
    )
    parser.add_argument(
        "--max_words",
        type=int,
        default=80,
        help="Maximum allowed word count for compliance checks (default: 80).",
    )
    parser.add_argument(
        "--max_examples",
        type=int,
        default=5,
        help="Number of sample fact FP/FN cases to print (default: 5).",
    )

    args = parser.parse_args()

    if not args.data.exists():
        raise FileNotFoundError(f"Data file not found: {args.data}")

    agent = load_agent(args.agent)
    data = read_jsonl(args.data)

    aggregate = await evaluate_dataset(
        data=data,
        agent=agent,
        max_words=args.max_words,
        csv_out=args.csv_out,
        json_out=args.per_case_dump,
        max_examples=args.max_examples,
    )

    print_summary(aggregate, len(data))


if __name__ == "__main__":
    asyncio.run(main())
