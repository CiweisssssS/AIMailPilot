### AIMailPilot Pipeline Combo Testing (S1–S3)

This folder contains a minimal harness to run Stage 1 only:
- Pipeline combo tests (Fast Path + Smart Fallback) for S1–S3

Goal: identify the fastest and most accurate pipeline while keeping JSON stability and due-date parsing high and costs reasonable.


### Models to test (within pipeline combos)
- Summarizer: Gemini Flash, Claude 3.5 Haiku
- Extractor: GPT-4o-mini-high-throughput, GPT-4o (base)


### Setup
1) Create and export API keys (examples; adjust to your env):

```bash
export OPENAI_API_KEY="..."
export ANTHROPIC_API_KEY="..."
export GOOGLE_API_KEY="..."      # Gemini
```

2) Optional: Create a Python venv and install deps (only stdlib used here; integrate your SDKs as needed).

Env setup (recommended):
- Copy `eval/env.template` to project root as `.env`, fill your keys, then load:
  ```bash
  export $(grep -v '^#' .env | xargs)
  ```
  Ensure `.env` is git-ignored (already covered in `.gitignore`).


### Dataset
Provide a JSONL file at `eval/dataset/emails.jsonl` with entries like:

```json
{
  "id": "email_001",
  "subject": "Project sync next Tuesday",
  "from": "alice@example.com",
  "to": ["me@example.com"],
  "cc": [],
  "received_at": "2025-11-10T09:30:00Z",
  "body_text": "Hi, can you send the draft by EOW? Also schedule a sync next Tuesday afternoon.",
  "ground_truth": {
    "summary": {
      "actor": "Alice",
      "action": "request",
      "object": "draft",
      "deadline": "2025-11-14",             // ISO date if known
      "notes": "Schedule sync next Tuesday afternoon"
    },
    "tasks": [
      {
        "owner": "me",
        "action": "send draft",
        "object": "project draft",
        "deadline": "2025-11-14",
        "priority": "medium"
      },
      {
        "owner": "me",
        "action": "schedule meeting",
        "object": "project sync",
        "deadline": null
      }
    ]
  }
}
```

Place ~20 emails to run S1–S3 with the same test set.


### Running

Stage 1 — Pipeline（分别运行 S1、S2、S3）

```bash
# S1: Gemini Flash + GPT-4o-mini
python -m eval.run_pipeline_s1 \
  --dataset eval/dataset/emails.jsonl \
  --output_dir eval/results/pipeline

# S2: Gemini Flash + GPT-4o
python -m eval.run_pipeline_s2 \
  --dataset eval/dataset/emails.jsonl \
  --output_dir eval/results/pipeline

# S3: Claude Haiku + GPT-4o
python -m eval.run_pipeline_s3 \
  --dataset eval/dataset/emails.jsonl \
  --output_dir eval/results/pipeline

# 仍可一次性跑多组合：
python -m eval.run_pipeline \
  --dataset eval/dataset/emails.jsonl \
  --output_dir eval/results/pipeline \
  --combos S1,S2,S3
```


### Single-model tests

- Summarizer
  - Gemini Flash
    ```bash
    python -m eval.run_summarizer_gemini \
      --dataset eval/dataset/emails.jsonl \
      --output eval/results/summarizer_gemini.csv \
      --very_lenient --sim_threshold 0.6
    ```
  - GPT-4o-mini
    ```bash
    python -m eval.run_summarizer_gpt4omini \
      --dataset eval/dataset/emails.jsonl \
      --output eval/results/summarizer_gpt4omini.csv \
      --very_lenient --sim_threshold 0.6
    ```
  - Claude 3.5 Haiku
    ```bash
    python -m eval.run_summarizer_claude_haiku \
      --dataset eval/dataset/emails.jsonl \
      --output eval/results/summarizer_claude_haiku.csv \
      --very_lenient --sim_threshold 0.6
    ```

- Extractor
  - Gemini Flash
    ```bash
    python -m eval.run_extractor_gemini \
      --dataset eval/dataset/emails.jsonl \
      --output eval/results/extractor_gemini.csv \
      --very_lenient --sim_threshold 0.6 --task_match_k 2
    ```
  - GPT-4o (base)
    ```bash
    python -m eval.run_extractor_gpt4o \
      --dataset eval/dataset/emails.jsonl \
      --output eval/results/extractor_gpt4o.csv \
      --very_lenient --sim_threshold 0.6 --task_match_k 2
    ```

Records for each combo:
- total_latency_ms (per email and aggregate)
- summary_slot_accuracy (actor/action/object/deadline)
- extractor_task_precision/recall/f1 + due_date correctness
- json_compliance
- error_examples.jsonl



### Fallback triggers in pipeline
- Relative time phrases (e.g., "next Tuesday", "by EOW")
- Overlong email (body exceeds threshold)
- Multi-action chain detected (multiple actionable requests)
- Fast-path model low confidence
- Due date unparsed/missing

These are implemented in `eval/pipeline.py` and can be tuned via CLI flags.


### Reporting
Aggregate reports are written to `eval/results/`.
- Per-combo summary files: `eval/results/pipeline/SUMMARY_S1.md`, `SUMMARY_S2.md`, `SUMMARY_S3.md`
- Combined summary (overwrites each run): `eval/results/pipeline/SUMMARY.md`
- Each combo directory contains `aggregate.json` and `errors.jsonl`


