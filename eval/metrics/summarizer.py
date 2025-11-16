import json
import re
from typing import Dict, Tuple


REQUIRED_KEYS = {"actor", "action", "object", "deadline", "notes"}


def _tokens(s: str) -> set:
    s = (s or "").lower()
    s = re.sub(r"[^\w\s:/\-]+", " ", s)
    return set(t for t in s.split() if t)


def rouge_l_like(pred_text: str, ref_text: str) -> float:
    """
    Lightweight ROUGE-L-like score via token set overlap ratio.
    Not a true ROUGE-L, but a proxy without external deps.
    """
    P = _tokens(pred_text)
    R = _tokens(ref_text)
    if not R and not P:
        return 1.0
    if not R or not P:
        return 0.0
    return len(P & R) / max(len(R), 1)


def fact_prf(pred_json: Dict, gt_json: Dict) -> Tuple[float, float, float]:
    """
    Simple factual PRF over concatenated fields of summary.
    Treats (actor, action, object, deadline, notes tokens) as 'facts' bag.
    """
    def flatten(j: Dict) -> str:
        values = [str(j.get(k) or "") for k in ["actor", "action", "object", "deadline", "notes"]]
        return " ".join(values)

    P = _tokens(flatten(pred_json or {}))
    R = _tokens(flatten(gt_json or {}))
    if not P and not R:
        return 1.0, 1.0, 1.0
    tp = len(P & R)
    precision = tp / len(P) if P else 0.0
    recall = tp / len(R) if R else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    return precision, recall, f1


def format_compliance(summary_json: Dict) -> float:
    """
    Checks if JSON contains exactly required keys and each key holds a primitive or null.
    Returns 1.0 if compliant else 0.0.
    """
    if not isinstance(summary_json, dict):
        return 0.0
    keys = set(summary_json.keys())
    if not REQUIRED_KEYS.issubset(keys):
        return 0.0
    for k in REQUIRED_KEYS:
        v = summary_json.get(k)
        if v is None:
            continue
        if not isinstance(v, (str, int, float)):
            return 0.0
    return 1.0


