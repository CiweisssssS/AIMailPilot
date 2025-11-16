import argparse
import csv
import json
import os
import re
from statistics import mean, median
from typing import Dict, List, Tuple, Optional

from .pipeline import load_dataset, run_pipeline_for_email


COMBOS = {
    "S1": {
        "summarizer_fast": "google:gemini-flash",
        "extractor_fast": "openai:gpt-4o-mini-high-throughput",
        "extractor_fallback_time": "openai:gpt-4o",
        "summarizer_fallback_struct": "anthropic:claude-3-5-haiku",
    },
    "S2": {
        "summarizer_fast": "google:gemini-flash",
        "extractor_fast": "openai:gpt-4o",
        "extractor_fallback_time": "openai:gpt-4o",
        "summarizer_fallback_struct": "anthropic:claude-3-5-haiku",
    },
    "S3": {
        "summarizer_fast": "anthropic:claude-3-5-haiku",
        "extractor_fast": "openai:gpt-4o",
        "extractor_fallback_time": "openai:gpt-4o",
        "summarizer_fallback_struct": "anthropic:claude-3-5-haiku",
    },
}


def _normalize_text(s) -> str:
    if s is None:
        return ""
    # Coerce non-strings
    if isinstance(s, list):
        s = " ".join(str(x) for x in s)
    elif not isinstance(s, str):
        s = str(s)
    s = s.strip().lower()
    # remove extra punctuation
    s = re.sub(r"[^\w\s:/\-]+", "", s)
    # simple synonyms
    synonyms = {
        "submit": "send",
        "send out": "send",
        "approval": "sign off",
        "approve": "sign off",
        "deck": "presentation",
        "slide deck": "presentation",
        "meeting": "sync",
    }
    for k, v in synonyms.items():
        s = s.replace(k, v)
    s = re.sub(r"\s+", " ", s)
    return s


def _normalize_owner(s: str) -> str:
    s = _normalize_text(s)
    if s in ("you", "recipient", "assignee", "your", "yourself", ""):
        return "me"
    return s


def _normalize_date(s: str) -> str:
    if not isinstance(s, str):
        return ""
    s = s.strip()
    if "T" in s:
        s = s.split("T", 1)[0]
    return s


def slot_acc(
    pred: Dict,
    gt: Dict,
    lenient: bool = False,
    very_lenient: bool = False,
    sim_threshold: float = 0.6,
) -> Dict[str, float]:
    keys = ["actor", "action", "object", "deadline"]
    correct = {k: 0 for k in keys}
    total = {k: 0 for k in keys}
    for k in keys:
        total[k] += 1
        p = (pred or {}).get(k)
        g = (gt or {}).get(k)
        if very_lenient:
            if k == "deadline":
                ok = _normalize_date(p) == _normalize_date(g)
            elif k in ("action", "object"):
                ok = _similarity(p or "", g or "") >= sim_threshold
            else:
                ok = _normalize_text(p or "") == _normalize_text(g or "")
        elif lenient:
            if k == "deadline":
                ok = _normalize_date(p) == _normalize_date(g)
            else:
                ok = _normalize_text(p or "") == _normalize_text(g or "")
        else:
            ok = p == g
        if ok:
            correct[k] += 1
    return {k: (correct[k] / total[k] if total[k] else 0.0) for k in keys}


def _token_set(s: str) -> set:
    return set(_normalize_text(s).split())


def _similarity(a: str, b: str) -> float:
    A = _token_set(a)
    B = _token_set(b)
    if not A and not B:
        return 1.0
    if not A or not B:
        return 0.0
    inter = len(A & B)
    union = len(A | B)
    return inter / union


def due_date_correctness(tasks_pred: List[Dict], tasks_gt: List[Dict]) -> float:
    # order-invariant, date-only comparison
    pred_dates = set(_normalize_date((t or {}).get("deadline")) for t in tasks_pred if (t or {}).get("deadline"))
    gt_dates = set(_normalize_date((t or {}).get("deadline")) for t in tasks_gt if (t or {}).get("deadline"))
    if not gt_dates and not pred_dates:
        return 1.0
    if not gt_dates or not pred_dates:
        return 0.0
    inter = len(pred_dates & gt_dates)
    return inter / max(len(gt_dates), 1)


def prf_tasks(
    pred_tasks: List[Dict],
    gt_tasks: List[Dict],
    lenient: bool = False,
    very_lenient: bool = False,
    sim_threshold: float = 0.6,
    task_match_k: int = 2,
) -> Tuple[float, float, float]:
    # naive stringification for overlap
    def norm(t: Dict) -> str:
        if not lenient:
            return json.dumps(
                {
                    "owner": (t or {}).get("owner"),
                    "action": (t or {}).get("action"),
                    "object": (t or {}).get("object"),
                    "deadline": (t or {}).get("deadline"),
                },
                sort_keys=True,
            )
        return json.dumps(
            {
                "owner": _normalize_owner((t or {}).get("owner")),
                "action": _normalize_text((t or {}).get("action") or ""),
                "object": _normalize_text((t or {}).get("object") or ""),
                "deadline": _normalize_date((t or {}).get("deadline")),
            },
            sort_keys=True,
        )

    if not very_lenient:
        pred_set = set(norm(t) for t in pred_tasks)
        gt_set = set(norm(t) for t in gt_tasks)
        tp = len(pred_set & gt_set)
        fp = len(pred_set - gt_set)
        fn = len(gt_set - pred_set)
    else:
        # Greedy best-match with k-of-4 fields rule (owner/action/object/deadline)
        used_gt = set()
        tp = 0
        for i, p in enumerate(pred_tasks):
            best_j = None
            best_score = -1
            for j, g in enumerate(gt_tasks):
                if j in used_gt:
                    continue
                match_count = 0
                # owner
                if _normalize_owner(p.get("owner")) == _normalize_owner(g.get("owner")) or (
                    _normalize_owner(p.get("owner")) in {"me", ""} and _normalize_owner(g.get("owner")) in {"me", ""}
                ):
                    match_count += 1
                # action
                if _similarity(p.get("action") or "", g.get("action") or "") >= sim_threshold:
                    match_count += 1
                # object
                if _similarity(p.get("object") or "", g.get("object") or "") >= sim_threshold:
                    match_count += 1
                # deadline
                if _normalize_date(p.get("deadline")) == _normalize_date(g.get("deadline")):
                    match_count += 1
                if match_count > best_score:
                    best_score = match_count
                    best_j = j
            if best_j is not None and best_score >= task_match_k:
                tp += 1
                used_gt.add(best_j)
        fp = max(len(pred_tasks) - tp, 0)
        fn = max(len(gt_tasks) - tp, 0)
    # Robust handling of empty predictions/ground truth using counts only
    if (tp + fp) == 0:
        precision = 1.0 if (tp == 0 and fn == 0) else 0.0
    else:
        precision = tp / (tp + fp)
    if (tp + fn) == 0:
        recall = 1.0 if (tp == 0 and fp == 0) else 0.0
    else:
        recall = tp / (tp + fn)
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
    return precision, recall, f1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True, help="Path to JSONL dataset")
    parser.add_argument("--output_dir", required=True, help="Directory for results")
    parser.add_argument("--combos", default="S1,S2,S3", help="Comma-separated combos to run")
    parser.add_argument("--overlong_threshold", type=int, default=2500, help="Email length to trigger fallback")
    parser.add_argument("--lenient", action="store_true", help="Use lenient matching (normalized text/date) for metrics")
    parser.add_argument("--very_lenient", action="store_true", help="Use similarity-based matching for slots and tasks")
    parser.add_argument("--sim_threshold", type=float, default=0.6, help="Similarity threshold for very-lenient mode")
    parser.add_argument("--task_match_k", type=int, default=2, help="Fields (of 4) required to match a task in very-lenient")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    samples = load_dataset(args.dataset)

    summary_md_lines = ["## Pipeline Results"]

    for combo_name in args.combos.split(","):
        combo = COMBOS[combo_name]
        combo_dir = os.path.join(args.output_dir, combo_name)
        os.makedirs(combo_dir, exist_ok=True)

        latencies = []
        json_ok = 0
        slot_hits = {"actor": 0, "action": 0, "object": 0, "deadline": 0}
        slot_total = {"actor": 0, "action": 0, "object": 0, "deadline": 0}
        task_pr_list = []
        task_rc_list = []
        task_f1_list = []
        due_match_list = []

        errors_path = os.path.join(combo_dir, "errors.jsonl")
        with open(errors_path, "w", encoding="utf-8") as errf:
            for s in samples:
                out, elapsed_ms = run_pipeline_for_email(
                    s,
                    summarizer_fast=combo["summarizer_fast"],
                    extractor_fast=combo["extractor_fast"],
                    extractor_fallback_time=combo["extractor_fallback_time"],
                    summarizer_fallback_struct=combo["summarizer_fallback_struct"],
                    overlong_threshold=args.overlong_threshold,
                )
                latencies.append(elapsed_ms)
                if out.json_compliant:
                    json_ok += 1

                gt_sum = (s.ground_truth or {}).get("summary", {})
                sa = slot_acc(
                    out.summary_json,
                    gt_sum,
                    lenient=args.lenient,
                    very_lenient=args.very_lenient,
                    sim_threshold=args.sim_threshold,
                )
                for k, v in sa.items():
                    slot_hits[k] += v
                    slot_total[k] += 1

                gt_tasks = (s.ground_truth or {}).get("tasks", [])
                p, r, f1 = prf_tasks(
                    out.tasks_json,
                    gt_tasks,
                    lenient=args.lenient,
                    very_lenient=args.very_lenient,
                    sim_threshold=args.sim_threshold,
                    task_match_k=args.task_match_k,
                )
                task_pr_list.append(p)
                task_rc_list.append(r)
                task_f1_list.append(f1)
                due_match_list.append(due_date_correctness(out.tasks_json, gt_tasks))

                if not out.json_compliant:
                    errf.write(
                        json.dumps(
                            {
                                "id": s.id,
                                "issue": "json_non_compliant",
                                "raw_summary": out.raw_summary_text,
                                "raw_tasks": out.raw_tasks_text,
                            },
                            ensure_ascii=False,
                        )
                        + "\n"
                    )
                else:
                    # Log mismatches to help diagnosis
                    if f1 < 1.0 or any(v < 1.0 for v in sa.values()):
                        errf.write(
                            json.dumps(
                                {
                                    "id": s.id,
                                    "issue": "mismatch",
                                    "summary_slots": sa,
                                    "task_precision": p,
                                    "task_recall": r,
                                    "task_f1": f1,
                                    "due_match": due_date_correctness(out.tasks_json, gt_tasks),
                                    "pred_summary": out.summary_json,
                                    "gt_summary": gt_sum,
                                    "pred_tasks": out.tasks_json,
                                    "gt_tasks": gt_tasks,
                                },
                                ensure_ascii=False,
                            )
                            + "\n"
                        )

        agg = {
            "combo": combo_name,
            "latency_avg_ms": mean(latencies) if latencies else 0,
            "latency_med_ms": median(latencies) if latencies else 0,
            "json_compliance_rate": json_ok / len(samples) if samples else 1.0,
            "slot_actor_acc": slot_hits["actor"] / slot_total["actor"] if slot_total["actor"] else 0.0,
            "slot_action_acc": slot_hits["action"] / slot_total["action"] if slot_total["action"] else 0.0,
            "slot_object_acc": slot_hits["object"] / slot_total["object"] if slot_total["object"] else 0.0,
            "slot_deadline_acc": slot_hits["deadline"] / slot_total["deadline"] if slot_total["deadline"] else 0.0,
            "task_precision": mean(task_pr_list) if task_pr_list else 1.0,
            "task_recall": mean(task_rc_list) if task_rc_list else 1.0,
            "task_f1": mean(task_f1_list) if task_f1_list else 1.0,
            "due_date_correctness": mean(due_match_list) if due_match_list else 1.0,
        }

        with open(os.path.join(combo_dir, "aggregate.json"), "w", encoding="utf-8") as f:
            json.dump(agg, f, ensure_ascii=False, indent=2)

        summary_md_lines.append(
            f"- {combo_name}: avg {agg['latency_avg_ms']:.0f} ms, F1 {agg['task_f1']:.2f}, "
            f"Slots A/A/O/D = {agg['slot_actor_acc']:.2f}/{agg['slot_action_acc']:.2f}/{agg['slot_object_acc']:.2f}/{agg['slot_deadline_acc']:.2f}, "
            f"JSON {agg['json_compliance_rate']:.2f}, Due {agg['due_date_correctness']:.2f}"
        )

    with open(os.path.join(args.output_dir, "SUMMARY.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(summary_md_lines) + "\n")


if __name__ == "__main__":
    main()


