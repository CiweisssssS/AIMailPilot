import argparse
import csv
import json
from statistics import mean

from .pipeline import load_dataset
from .models.registry import get_model_client
from .run_pipeline import prf_tasks, due_date_correctness, _normalize_owner


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--output", required=True, help="CSV path for per-sample results")
    parser.add_argument("--lenient", action="store_true")
    parser.add_argument("--very_lenient", action="store_true")
    parser.add_argument("--sim_threshold", type=float, default=0.6)
    parser.add_argument("--task_match_k", type=int, default=2)
    args = parser.parse_args()

    model_id = "google:gemini-flash"
    client = get_model_client(model_id)
    samples = load_dataset(args.dataset)

    rows = []
    pr_list = []
    rc_list = []
    f1_list = []
    due_list = []
    owner_list = []
    json_ok_list = []

    def owner_match(pred_tasks, gt_tasks) -> float:
        pred_owners = set(_normalize_owner((t or {}).get("owner")) for t in pred_tasks if (t or {}).get("owner") is not None)
        gt_owners = set(_normalize_owner((t or {}).get("owner")) for t in gt_tasks if (t or {}).get("owner") is not None)
        if not pred_owners and not gt_owners:
            return 1.0
        if not pred_owners or not gt_owners:
            return 0.0
        inter = len(pred_owners & gt_owners)
        return inter / max(len(gt_owners), 1)

    for s in samples:
        prompt_text = f"Received at (UTC): {s.received_at}\n\nEmail:\n{s.body_text}"
        raw, tasks_json, _ = client.extract(prompt_text)
        pred_tasks = tasks_json.get("tasks", []) if isinstance(tasks_json, dict) else []
        gt_tasks = (s.ground_truth or {}).get("tasks", [])
        p, r, f1 = prf_tasks(
            pred_tasks, gt_tasks, lenient=args.lenient, very_lenient=args.very_lenient, sim_threshold=args.sim_threshold, task_match_k=args.task_match_k
        )
        pr_list.append(p)
        rc_list.append(r)
        f1_list.append(f1)
        due_list.append(due_date_correctness(pred_tasks, gt_tasks))
        owner_list.append(owner_match(pred_tasks, gt_tasks))
        json_ok_list.append(1.0 if isinstance(tasks_json, dict) else 0.0)
        rows.append(
            {
                "id": s.id,
                "model": model_id,
                "precision": p,
                "recall": r,
                "f1": f1,
                "due_match": due_list[-1],
                "owner_match": owner_list[-1],
                "json_ok": json_ok_list[-1],
            }
        )

    with open(args.output, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "model", "precision", "recall", "f1", "due_match", "owner_match", "json_ok"])
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    agg = {
        "model": model_id,
        "task_precision": mean(pr_list) if pr_list else 0.0,
        "task_recall": mean(rc_list) if rc_list else 0.0,
        "task_f1": mean(f1_list) if f1_list else 0.0,
        "due_date_correctness": mean(due_list) if due_list else 0.0,
        "owner_match": mean(owner_list) if owner_list else 0.0,
        "json_parse_rate": mean(json_ok_list) if json_ok_list else 1.0,
    }
    agg_path = args.output.replace(".csv", ".aggregate.json")
    with open(agg_path, "w", encoding="utf-8") as f:
        json.dump(agg, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()


