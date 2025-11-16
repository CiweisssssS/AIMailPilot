import argparse
import os
import sys
from . import run_pipeline as rp


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True, help="Path to JSONL dataset")
    parser.add_argument("--output_dir", required=True, help="Directory for results")
    parser.add_argument("--overlong_threshold", type=int, default=2500)
    parser.add_argument("--lenient", action="store_true")
    parser.add_argument("--very_lenient", action="store_true")
    parser.add_argument("--sim_threshold", type=float, default=None)
    parser.add_argument("--task_match_k", type=int, default=None)
    args = parser.parse_args()

    argv = [
        "eval.run_pipeline",
        "--dataset",
        args.dataset,
        "--output_dir",
        args.output_dir,
        "--combos",
        "S2",
        "--overlong_threshold",
        str(args.overlong_threshold),
    ]
    if args.lenient:
        argv.append("--lenient")
    if args.very_lenient:
        argv.append("--very_lenient")
    if args.sim_threshold is not None:
        argv.extend(["--sim_threshold", str(args.sim_threshold)])
    if args.task_match_k is not None:
        argv.extend(["--task_match_k", str(args.task_match_k)])
    sys.argv = argv
    rp.main()

    # Also persist a per-combo summary file to avoid overwrite by other runs
    summary_path = os.path.join(args.output_dir, "SUMMARY.md")
    summary_s2_path = os.path.join(args.output_dir, "SUMMARY_S2.md")
    try:
        with open(summary_path, "r", encoding="utf-8") as f:
            content = f.read()
        with open(summary_s2_path, "w", encoding="utf-8") as f:
            f.write(content)
    except Exception:
        pass


if __name__ == "__main__":
    main()


