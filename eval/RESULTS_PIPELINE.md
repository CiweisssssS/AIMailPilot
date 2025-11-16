## Pipeline (Combo) Evaluation

This document captures:
- What the combo tests evaluate (Fast Path + Smart Fallback)
- How metrics are computed
- How to run S1–S3
- A concise readout of the latest snapshot and which capability each combo is strongest at


### 1) What the pipeline tests do

We evaluate end-to-end behavior for three combos (Summarizer → Extractor), including “fast path” and targeted fallbacks:
- S1: Gemini Flash + GPT‑4o‑mini (fast path baseline)
- S2: Gemini Flash + GPT‑4o (time-understanding fallback)
- S3: Claude 3.5 Haiku + GPT‑4o (structure fallback)

Fallback triggers (implemented in `eval/pipeline.py`):
- Relative-time phrases (“next Tuesday”, “by EOW”, etc.)
- Overlong emails (configurable threshold)
- Multi-action chain detected
- Low summarizer confidence
- Missing/Unparsed due date

For each email:
1) Summarizer runs (fast; fallback if triggered)
2) Extractor runs (fast; falls back to time-strong model if relative time or missing due persists)
3) We measure latency and compute accuracy metrics against ground-truth


### 2) Metrics

- Latency
  - Per-sample wall time (ms), aggregated avg/median per combo
- JSON compliance
  - Whether summary/tasks parse as valid JSON with the expected schema
- Summary slot accuracy (actor/action/object/deadline)
  - strict: exact equality
  - `--lenient`: normalization + small synonym map; deadline compares as date-only
  - `--very_lenient`: as lenient plus similarity threshold for action/object (`--sim_threshold`); actor remains conservative
- Extractor task metrics
  - Precision / Recall / F1
    - strict: set overlap on normalized task dicts
    - `--lenient`: normalization
    - `--very_lenient`: similarity-threshold match for action/object + k-of-4 field rule (`--task_match_k`) across owner/action/object/deadline
  - Due date correctness
    - Order-invariant date-set overlap (YYYY‑MM‑DD)
- Errors
  - `errors.jsonl` includes non-compliance and mismatch cases with predicted vs ground-truth for quick diagnosis


### 3) How to run

Strict:
```bash
python -m eval.run_pipeline_s1 --dataset eval/dataset/emails.jsonl --output_dir eval/results/pipeline
python -m eval.run_pipeline_s2 --dataset eval/dataset/emails.jsonl --output_dir eval/results/pipeline
python -m eval.run_pipeline_s3 --dataset eval/dataset/emails.jsonl --output_dir eval/results/pipeline
```
Lenient / Very-lenient (diagnostic upper bound):
```bash
# append any of the following flags
--lenient
--very_lenient --sim_threshold 0.5 --task_match_k 1
```
Artifacts:
- Per combo: `eval/results/pipeline/Sx/{aggregate.json, errors.jsonl}`
- Summary table: `eval/results/pipeline/SUMMARY_Sx.md` and `SUMMARY.md`


### 4) Latest snapshot (examples from your runs)

Note: exact numbers will vary as prompts and normalizers improve; refer to the files above for your ground truth.

- S1 (Gemini Flash + 4o‑mini)
  - Strength: speed, JSON discipline
  - Observed gaps: actor/action slot alignment with GT schema (actor entity naming; action intent label vs task-verb phrase)
  - Latency: typically lowest when not rate-limited

- S2 (Gemini Flash + 4o)
  - Strength: due-date parsing and time understanding (4o fallback)
  - Balanced trade‑off between accuracy and latency

- S3 (Claude Haiku + 4o)
  - Strength: structural stability (well-formed summaries) and consistent object granularity
  - Often slightly higher latency than S1; accuracy on slots may edge up for structured inputs


### 5) Which combo is strongest at what

- Fastest user experience → S1
  - Use when throughput/latency is the top priority, while retaining fallbacks for difficult time cases
- Most robust time understanding → S2
  - 4o base serves as a strong fallback for relative-time and absolute deadline resolution
- Most stable structure → S3
  - Haiku tends to be stricter with JSON structure and consistent slot formatting, benefiting downstream extraction

Recommendation:
- Start with S1 as fast path; enable fallbacks as already implemented (relative-time/missing due/low confidence) to S2 and S3 behaviors. Validate with `--lenient` during iteration; report final numbers with strict/lenient for comparability.


