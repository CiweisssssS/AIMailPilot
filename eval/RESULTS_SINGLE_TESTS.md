## Single-Model Evaluation (Summarizer & Extractor)

This document captures:
- What each single-model script evaluates
- How metrics are computed (strict/lenient/very-lenient)
- How to run them
- A concise readout of current snapshot results and takeaways


### 1) What the tests do

1.1 Summarizer (three scripts; logic identical)
- Inputs: For each email, prepend “Received at (UTC): <ISO>” to help resolve relative time.
- Model call: `summarize(email)` → expects STRICT JSON with keys `actor, action, object, deadline, notes`.
- Metrics per email:
  - Slot accuracy: actor/action/object/deadline
    - strict: exact equality
    - `--lenient`: lowercase, punctuation/space normalization, small synonym map; deadline compares as date-only
    - `--very_lenient`: same as lenient, plus similarity threshold for action/object (token Jaccard), configurable via `--sim_threshold`
  - ROUGE-like (proxy): token-overlap ratio between model raw text and ground-truth summary JSON string
  - Fact P/R/F1: bag-of-words across the five fields (actor/action/object/deadline/notes)
  - JSON parse rate
  - Format compliance: requires exactly the five keys with primitive-or-null values
  - Latency (ms): per-sample latency; aggregated avg/median

Outputs:
- CSV with per-sample metrics (+ latency_ms)
- `<output>.aggregate.json` with averages
- `<output>.errors.jsonl` for non-perfect slot cases


1.2 Extractor (two scripts; logic identical)
- Inputs: prepend “Received at (UTC): <ISO>” to aid absolute date resolution.
- Model call: `extract(email)` → STRICT JSON:
  ```json
  { "tasks": [ { "owner": string|null, "action": string|null, "object": string|null, "deadline": string|null, "priority": "high"|"medium"|"low"|"fyi"|null } ] }
  ```
- Metrics per email:
  - Task Precision / Recall / F1
    - strict: set overlap of normalized task dicts
    - `--lenient`: text/date normalization
    - `--very_lenient`: similarity-threshold match for action/object + k-of-4 field match across owner/action/object/deadline, controlled by `--sim_threshold` and `--task_match_k`
  - Due date match: set overlap on YYYY-MM-DD dates (order-invariant)
  - Owner match: set overlap after owner normalization (`you/recipient/assignee` → `me`)
  - JSON parse rate

Outputs:
- CSV with per-sample precision/recall/F1, due/owner/json_ok
- `<output>.aggregate.json` with averages


### 2) How to run

Summarizer:
```bash
# Gemini Flash
python -m eval.run_summarizer_gemini \
  --dataset eval/dataset/emails.jsonl \
  --output eval/results/summarizer_gemini.csv \
  --very_lenient --sim_threshold 0.6

# GPT-4o-mini
python -m eval.run_summarizer_gpt4omini \
  --dataset eval/dataset/emails.jsonl \
  --output eval/results/summarizer_gpt4omini.csv \
  --very_lenient --sim_threshold 0.6

# Claude 3.5 Haiku
python -m eval.run_summarizer_claude_haiku \
  --dataset eval/dataset/emails.jsonl \
  --output eval/results/summarizer_claude.csv \
  --very_lenient --sim_threshold 0.6
```

Extractor:
```bash
# Gemini Flash
python -m eval.run_extractor_gemini \
  --dataset eval/dataset/emails.jsonl \
  --output eval/results/extractor_gemini.csv \
  --very_lenient --sim_threshold 0.6 --task_match_k 2

# GPT-4o (base)
python -m eval.run_extractor_gpt4o \
  --dataset eval/dataset/emails.jsonl \
  --output eval/results/extractor_gpt4o.csv \
  --very_lenient --sim_threshold 0.6 --task_match_k 2
```

Notes:
- Use `--lenient` for moderate normalization; use `--very_lenient` to include semantic similarity + k-of-4 task matching (diagnostic and upper-bound checks). For final product scoring, prefer strict/lenient for comparability.


### 3) Current snapshot results (from your latest runs)

3.1 Summarizer — Gemini Flash (example aggregate)
```json
{
  "model": "google:gemini-flash",
  "slot_actor_acc": 0.00,
  "slot_action_acc": 0.05,
  "slot_object_acc": 0.30,
  "slot_deadline_acc": 0.80,
  "json_parse_rate": 1.00,
  "format_compliance": 1.00,
  "rouge_like": 0.69,
  "fact_precision": 0.40,
  "fact_recall": 0.46,
  "fact_f1": 0.40
}
```
Interpretation:
- Strong on deadline normalization and JSON discipline.
- Main gaps are actor/action alignment with the ground-truth schema (actor entity naming, action intent label vs task-verb phrase). Prompt guidance and light post-processing rules are being expanded to lift these.

3.2 Extractor — GPT‑4o (base)
- Generally higher time understanding and more stable absolute date parsing (best fallback candidate). See `eval/results/extractor_gpt4o.aggregate.json` for your exact numbers after a run.

3.3 Extractor — Gemini Flash
- Now switched from a placeholder to a real JSON extraction call; scores will no longer be all zeros. See `eval/results/extractor_gemini.aggregate.json` after re-running.


### 4) Brief capability comparison (based on design intent and current snapshot)

- Summarizer:
  - Gemini Flash: Fast with good time resolution and robust JSON; needs more guidance to align actor naming and action labeling with our schema.
  - GPT-4o-mini: Strong “fast baseline” for summary; typically balanced formatting and content faithfulness.
  - Claude 3.5 Haiku: Often more stable in structure; tends to be careful about action/object granularity.

- Extractor:
  - GPT‑4o (base): Most stable for time understanding (absolute deadlines) → best fallback for time-sensitive tasks.
  - Gemini Flash: Fastest path for extraction; now that it returns real structured tasks, it should be paired with lenient evaluation or verb/object normalization for best F1.


### 5) Where to look for artifacts
- Per-model CSV: under `eval/results/`, named by your `--output`
- Aggregates: same path with `.aggregate.json`
- Summarizer errors: `.errors.jsonl` siblings next to CSV

These scripts share the same normalization and (optional) semantic matching used in the pipeline evaluation, so single-model results are directly comparable to pipeline components. To keep pipeline scores conservative, prefer strict/lenient for final comparisons; use very-lenient to diagnose semantic near-misses before tuning prompts and post-processing.


