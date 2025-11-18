import argparse
import csv
import json
import time
from statistics import mean, median

from .pipeline import load_dataset, postprocess_summary
from .models.registry import get_model_client
from .run_pipeline import slot_acc
from .metrics.summarizer import rouge_l_like, fact_prf, format_compliance


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--output", required=True, help="CSV path for per-sample results")
    parser.add_argument("--lenient", action="store_true")
    parser.add_argument("--very_lenient", action="store_true")
    parser.add_argument("--sim_threshold", type=float, default=0.6)
    args = parser.parse_args()

    model_id = "anthropic:claude-3-5-haiku"
    client = get_model_client(model_id)
    samples = load_dataset(args.dataset)

    rows = []
    json_ok = []
    fmt_ok = []
    slot_actor = []
    slot_action = []
    slot_object = []
    slot_deadline = []
    rouge_list = []
    fact_p_list = []
    fact_r_list = []
    fact_f1_list = []
    latency = []
    processed_summaries = []  # Store processed summaries for error reporting

    for s in samples:
        prompt_text = f"Received at (UTC): {s.received_at}\n\nEmail:\n{s.body_text}"
        start = time.time()
        raw, summary_json, _ = client.summarize(prompt_text)
        latency.append((time.time() - start) * 1000.0)
        ok = isinstance(summary_json, dict)
        json_ok.append(1.0 if ok else 0.0)
        # Apply same postprocessing as pipeline to ensure consistency
        if ok:
            summary_json = postprocess_summary(summary_json, s)
        processed_summaries.append(summary_json if ok else {})
        gt_sum = (s.ground_truth or {}).get("summary", {})
        sa = slot_acc(
            summary_json if ok else {},
            gt_sum,
            lenient=args.lenient,
            very_lenient=args.very_lenient,
            sim_threshold=args.sim_threshold,
            received_at=s.received_at,
        )
        slot_actor.append(sa["actor"])
        slot_action.append(sa["action"])
        slot_object.append(sa["object"])
        slot_deadline.append(sa["deadline"])
        rouge = rouge_l_like(raw or "", json.dumps(gt_sum, ensure_ascii=False))
        p_f, r_f, f1_f = fact_prf(summary_json if ok else {}, gt_sum)
        fmt = format_compliance(summary_json if ok else {})
        rouge_list.append(rouge)
        fact_p_list.append(p_f)
        fact_r_list.append(r_f)
        fact_f1_list.append(f1_f)
        fmt_ok.append(fmt)
        rows.append(
            {
                "id": s.id,
                "model": model_id,
                "slot_actor": sa["actor"],
                "slot_action": sa["action"],
                "slot_object": sa["object"],
                "slot_deadline": sa["deadline"],
                "json_ok": 1.0 if ok else 0.0,
                "format_ok": fmt,
                "rouge_like": rouge,
                "fact_precision": p_f,
                "fact_recall": r_f,
                "fact_f1": f1_f,
                "latency_ms": latency[-1],
            }
        )

    with open(args.output, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "id","model","slot_actor","slot_action","slot_object","slot_deadline",
            "json_ok","format_ok","rouge_like","fact_precision","fact_recall","fact_f1",
            "latency_ms"
        ])
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    agg = {
        "model": model_id,
        "slot_actor_acc": mean(slot_actor) if slot_actor else 0.0,
        "slot_action_acc": mean(slot_action) if slot_action else 0.0,
        "slot_object_acc": mean(slot_object) if slot_object else 0.0,
        "slot_deadline_acc": mean(slot_deadline) if slot_deadline else 0.0,
        "json_parse_rate": mean(json_ok) if json_ok else 1.0,
        "format_compliance": mean(fmt_ok) if fmt_ok else 1.0,
        "rouge_like": mean(rouge_list) if rouge_list else 0.0,
        "fact_precision": mean(fact_p_list) if fact_p_list else 0.0,
        "fact_recall": mean(fact_r_list) if fact_r_list else 0.0,
        "fact_f1": mean(fact_f1_list) if fact_f1_list else 0.0,
        "latency_avg_ms": mean(latency) if latency else 0.0,
        "latency_med_ms": median(latency) if latency else 0.0,
    }
    agg_path = args.output.replace(".csv", ".aggregate.json")
    with open(agg_path, "w", encoding="utf-8") as f:
        json.dump(agg, f, ensure_ascii=False, indent=2)

    err_path = args.output.replace(".csv", ".errors.jsonl")
    with open(err_path, "w", encoding="utf-8") as ef:
        for row, s, pred_sum in zip(rows, samples, processed_summaries):
            if row["slot_actor"] < 1.0 or row["slot_action"] < 1.0 or row["slot_object"] < 1.0 or row["slot_deadline"] < 1.0:
                gt_sum = (s.ground_truth or {}).get("summary", {})
                ef.write(json.dumps({
                    "id": s.id,
                    "summary_slots": {
                        "actor": row["slot_actor"],
                        "action": row["slot_action"],
                        "object": row["slot_object"],
                        "deadline": row["slot_deadline"],
                    },
                    "pred_summary": pred_sum,
                    "gt_summary": gt_sum,
                }, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()


