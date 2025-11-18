import argparse
import asyncio
import csv
import importlib
import inspect
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, Iterable, List, Optional, Tuple

# Import eval logic for consistency
sys.path.insert(0, str(Path(__file__).parent.parent))
from eval.run_pipeline import slot_acc
from eval.metrics.summarizer import fact_prf, format_compliance, rouge_l_like
from eval.pipeline import postprocess_summary, _extract_sender_name


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
    """
    Evaluate dataset using eval script logic (structured JSON comparison).
    This matches the evaluation approach in eval/run_summarizer_*.py scripts.
    """
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
    
    # Import EmailSample for postprocess_summary
    from eval.common.types import EmailSample
    
    for row in data:
        # Get structured JSON from agent (matching eval script logic)
        pred_json, json_ok = await invoke_agent(agent, signature, row, max_words)
        
        # Create EmailSample for postprocess_summary
        email_sample = EmailSample(
            id=row.get("id", ""),
            subject=row.get("subject", ""),
            from_addr=row.get("sender", ""),
            to_addrs=[],
            cc_addrs=[],
            received_at=row.get("received_at", ""),
            body_text=row.get("body", "") or format_thread_text(row.get("messages", [])),
            ground_truth={},
        )
        
        # Apply postprocessing (same as eval script)
        if json_ok and isinstance(pred_json, dict):
            pred_json = postprocess_summary(pred_json, email_sample)
        
        # Get ground truth (expecting same format as eval script)
        gt_json = row.get("ground_truth", {}).get("summary", {})
        if not gt_json and row.get("key_facts"):
            # Convert key_facts format to summary format
            gt_json = {
                "actor": row.get("key_facts", {}).get("actor"),
                "action": row.get("key_facts", {}).get("action"),
                "object": row.get("key_facts", {}).get("object"),
                "deadline": row.get("key_facts", {}).get("deadline"),
                "notes": None,
            }
        
        # Use eval script's slot_acc for slot-level accuracy
        sa = slot_acc(
            pred_json if json_ok else {},
            gt_json,
            lenient=False,  # Can be made configurable
            very_lenient=False,  # Can be made configurable
            sim_threshold=0.6,
        )
        
        # Use eval script's fact_prf for fact-level metrics
        fact_p, fact_r, fact_f1 = fact_prf(pred_json if json_ok else {}, gt_json)
        
        # Use eval script's format_compliance
        fmt_ok = format_compliance(pred_json if json_ok else {})
        
        # ROUGE-like score (using eval script's rouge_l_like)
        # Convert JSON to text for ROUGE
        pred_text = json.dumps(pred_json if json_ok else {}, ensure_ascii=False)
        gt_text = json.dumps(gt_json, ensure_ascii=False)
        rouge_l_score = rouge_l_like(pred_text, gt_text)
        
        # Calculate fact-level metrics (matching eval script approach)
        # Count TP/FP/FN based on slot accuracy
        slot_correct = {k: sa[k] for k in FACT_KEYS}
        case_strict_tp = 0
        case_partial_tp = 0
        case_fp = 0
        case_fn = 0
        
        for key in FACT_KEYS:
            per_fact_totals[key] += 1
            if slot_correct[key] >= 1.0:  # Exact match
                per_fact_strict[key] += 1
                case_strict_tp += 1
            elif slot_correct[key] > 0.0:  # Partial match
                per_fact_partial[key] += 1
                case_partial_tp += 1
            else:  # Mismatch
                # Check if it's FP (predicted but wrong) or FN (missing)
                if pred_json.get(key) and not gt_json.get(key):
                    case_fp += 1
                elif gt_json.get(key) and not pred_json.get(key):
                    case_fn += 1
                else:
                    # Both present but mismatch
                    case_fp += 1
                    case_fn += 1
        
        # Accumulate totals
        strict_tp_total += case_strict_tp
        partial_tp_total += case_partial_tp
        fp_total += case_fp
        fn_total += case_fn
        
        # Extract summary text for compliance checks (if available)
        summary_text = ""
        if isinstance(pred_json, dict):
            # Try to get summary text if available
            summary_text = str(pred_json.get("summary", ""))
            if not summary_text:
                # Build summary from structured fields
                actor = str(pred_json.get("actor", ""))
                action = str(pred_json.get("action", ""))
                obj = str(pred_json.get("object", ""))
                deadline = str(pred_json.get("deadline", ""))
                parts = [p for p in [actor, action, obj] if p]
                if deadline:
                    parts.append(f"by {deadline}")
                summary_text = " ".join(parts)
        
        contains_action = has_action(summary_text) if summary_text else False
        sender_starts = starts_with_sender(summary_text, row.get("sender", "")) if summary_text else False
        length_ok = word_count(summary_text) <= max_words if summary_text else False
        ends_period = ends_with_period(summary_text) if summary_text else False
        wc = word_count(summary_text) if summary_text else 0
        
        # ROUGE-1 (approximate, using token overlap)
        ref_tokens = tokenize(gt_text)
        hyp_tokens = tokenize(pred_text)
        rouge1 = rouge_n_recall(ref_tokens, hyp_tokens, n=1) if ref_tokens and hyp_tokens else 0.0

        # case_strict_tp, case_partial_tp, case_fp, case_fn already calculated above
        
        results.append(
            CaseResult(
                email_id=row.get("id", ""),
                rouge1=rouge1,
                rouge_l=rouge_l_score,
                fact_precision=fact_p,
                fact_recall=fact_r,
                fact_strict_tp=case_strict_tp,
                fact_partial_tp=case_partial_tp,
                fact_fp=case_fp,
                fact_fn=case_fn,
                has_action_verb=contains_action,
                starts_with_sender=sender_starts,
                length_ok=length_ok,
                ends_with_period=ends_period,
                json_parse_ok=json_ok and fmt_ok > 0.0,
                word_count=wc,
            )
        )

        per_case_dump.append(
            {
                "id": row.get("id", ""),
                "subject": row.get("subject", ""),
                "pred_json": pred_json if json_ok else {},
                "gt_json": gt_json,
                "slot_acc": sa,
                "fact_precision": fact_p,
                "fact_recall": fact_r,
                "fact_f1": fact_f1,
                "rouge_l": rouge_l_score,
                "rouge1": rouge1,
                "format_ok": fmt_ok,
                "json_ok": json_ok,
                "has_action_verb": contains_action,
                "starts_with_sender": sender_starts,
                "length_ok": length_ok,
                "ends_with_period": ends_period,
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


async def invoke_agent(agent: AgentFn, signature: inspect.Signature, row: Dict[str, Any], max_words: int) -> Tuple[Dict[str, Any], bool]:
    """
    Invoke agent and extract structured JSON (actor, action, object, deadline) from response.
    Returns (structured_json, json_ok) instead of (summary_text, json_ok) to match eval script logic.
    """
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

    # Try to get structured JSON directly from LLM if agent is summarize_text
    # This matches eval script logic which calls LLM directly
    agent_name = getattr(agent, '__name__', '')
    if agent_name == 'summarize_text':
        try:
            from app.core.llm import LLMProvider
            from app.core.prompts import get_summary_system_prompt, SUMMARY_FEW_SHOT_EXAMPLES
            from app.services.summarizer import extract_sender_name
            
            llm_provider = LLMProvider()
            subject = kwargs.get("subject", "")
            text = kwargs.get("text", "")
            sender = kwargs.get("sender", "")
            sender_name = extract_sender_name(sender)
            
            system_prompt = get_summary_system_prompt(max_words)
            user_message = f"""Subject: {subject}
From: {sender_name}
Body (trimmed): {text}

Return JSON only with keys: summary, actor, action, object, deadline."""
            
            messages = [
                {"role": "system", "content": system_prompt}
            ]
            messages.extend(SUMMARY_FEW_SHOT_EXAMPLES)
            messages.append({"role": "user", "content": user_message})
            
            response = await llm_provider.call_with_json_mode(
                messages=messages,
                temperature=0.2
            )
            
            if isinstance(response, str):
                response_data = json.loads(response)
            else:
                response_data = response
            
            # Extract structured fields
            structured_json = {
                "actor": response_data.get("actor"),
                "action": response_data.get("action"),
                "object": response_data.get("object"),
                "deadline": response_data.get("deadline"),
                "notes": response_data.get("notes"),
            }
            return structured_json, True
        except Exception:
            # Fall back to regular agent call
            pass

    result = await agent(**kwargs)  # type: ignore[misc]

    json_ok = True
    structured_json: Dict[str, Any] = {}

    # Extract structured JSON from response
    if isinstance(result, dict):
        # Check if it already has structured fields
        if any(k in result for k in ["actor", "action", "object", "deadline"]):
            structured_json = {
                "actor": result.get("actor"),
                "action": result.get("action"),
                "object": result.get("object"),
                "deadline": result.get("deadline"),
                "notes": result.get("notes"),
            }
        else:
            # Try to extract from summary text (fallback)
            summary_text = str(result.get("summary", ""))
            if summary_text:
                structured_json = extract_predicted_facts(summary_text)
    elif isinstance(result, str):
        parsed: Optional[Any] = None
        try:
            parsed = json.loads(result)
            if isinstance(parsed, dict):
                if any(k in parsed for k in ["actor", "action", "object", "deadline"]):
                    structured_json = {
                        "actor": parsed.get("actor"),
                        "action": parsed.get("action"),
                        "object": parsed.get("object"),
                        "deadline": parsed.get("deadline"),
                        "notes": parsed.get("notes"),
                    }
                elif "summary" in parsed:
                    structured_json = extract_predicted_facts(str(parsed.get("summary", "")))
                else:
                    structured_json = extract_predicted_facts(result)
            else:
                structured_json = extract_predicted_facts(result)
        except json.JSONDecodeError:
            json_ok = False
            structured_json = extract_predicted_facts(result)
    else:
        json_ok = False
        structured_json = {}

    return structured_json, json_ok


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
