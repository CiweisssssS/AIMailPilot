"""
Single-model evaluation script for Summarizer.
Tests app.services.summarizer:summarize_text using eval script logic.
"""

import argparse
import asyncio
import csv
import json
import re
import time
from pathlib import Path
from statistics import mean, median
from typing import Dict, List

from .pipeline import load_dataset, postprocess_summary
from .run_pipeline import slot_acc
from .metrics.summarizer import rouge_l_like, fact_prf, format_compliance
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


async def main():
    parser = argparse.ArgumentParser(description="Evaluate summarizer single model")
    parser.add_argument("--dataset", required=True, help="Path to JSONL dataset")
    parser.add_argument("--output", required=True, help="CSV path for per-sample results")
    parser.add_argument("--lenient", action="store_true", help="Use lenient matching")
    parser.add_argument("--very_lenient", action="store_true", help="Use very lenient matching")
    parser.add_argument("--sim_threshold", type=float, default=0.75, help="Similarity threshold (stricter: 0.75)")
    args = parser.parse_args()

    # Import actual summarizer function
    from app.services.summarizer import summarize_text
    
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
    processed_summaries = []

    for s in samples:
        # Prepare input for summarize_text
        subject = s.subject
        text = s.body_text
        sender = s.from_addr
        
        start = time.time()
        try:
            # Call LLM directly to get structured fields (same as summarizer does internally)
            from app.core.llm import LLMProvider
            from app.core.prompts import get_summary_system_prompt, SUMMARY_FEW_SHOT_EXAMPLES
            from app.services.summarizer import extract_sender_name
            
            llm_provider = LLMProvider()
            sender_name = extract_sender_name(sender)
            max_words = settings.summary_max_words
            
            # Call LLM directly (matching what summarizer does internally)
            system_prompt = get_summary_system_prompt(max_words)
            # Enhanced prompt with clear field requirements
            enhanced_system_prompt = f"""You are an email summarizer. Extract key facts from the email.

**Output Format:**
Return JSON with keys: summary, actor, action, object, deadline.

**Field Requirements:**

1. **actor**: The sender's name (first name or full name, extracted from email address if needed)
   - DO NOT include "Team", "Department", "Group" suffixes
   - Examples: "Alice" (not "Alice Team"), "Legal" (not "Legal Team"), "John" (not "john@example.com")

2. **action**: Use intent labels, NOT task verbs
   - Use "request" for: send, submit, share, review, check, approve, schedule, prepare, update, etc.
   - Use "remind" for: remind, prepare (when it's a reminder)
   - Use "notify" or "inform" for: notify, inform, alert, announce, approve (when notifying about approval)
   - Examples: "request" (not "send"), "remind" (not "prepare"), "notify" (not "approve")

3. **object**: The core thing being requested/mentioned (be concise, avoid extra details)
   - Extract the main noun phrase, not the full description
   - Examples: "project draft" (not "project draft and sync"), "contract feedback" (not "client contract and sales alignment"), "slide deck review" (not just "slide deck")

4. **deadline**: MUST be in ISO format (YYYY-MM-DD) or null
   - Convert relative time to ISO dates based on received_at
   - "EOW" → Friday of current week
   - "tomorrow" → next day
   - "next Wednesday" → calculate the date
   - Examples: "2025-11-14" (not "EOW"), "2025-11-11" (not "tomorrow")

**Examples:**
- Email: "Could you send the draft by EOW?" → {{"actor": "Alice", "action": "request", "object": "draft", "deadline": "2025-11-14"}}
- Email: "Please prepare status update for tomorrow" → {{"actor": "PM", "action": "remind", "object": "status update", "deadline": "2025-11-11"}}
"""
            user_message = f"""Subject: {subject}
From: {sender_name}
Received at (UTC): {s.received_at}
Body (trimmed): {text}

Return JSON only with keys: summary, actor, action, object, deadline."""
            
            # Don't use few-shot examples that might confuse the model
            # The enhanced prompt is clear enough
            messages = [
                {"role": "system", "content": enhanced_system_prompt},
                {"role": "user", "content": user_message}
            ]
            
            response = await llm_provider.call_with_json_mode(
                messages=messages,
                temperature=0.2
            )
            
            latency.append((time.time() - start) * 1000.0)
            
            # Parse structured fields from LLM response
            summary_json = {}
            json_ok_flag = False
            try:
                if isinstance(response, str):
                    # Try to extract JSON from response (handle cases where LLM adds extra text)
                    response_clean = response.strip()
                    
                    # Remove markdown code blocks if present
                    if '```json' in response_clean:
                        response_clean = response_clean.split('```json')[1].split('```')[0].strip()
                    elif '```' in response_clean:
                        response_clean = response_clean.split('```')[1].split('```')[0].strip()
                    
                    # Try to find JSON object boundaries
                    if response_clean.startswith('{'):
                        # Find the matching closing brace
                        brace_count = 0
                        json_end = -1
                        for i, char in enumerate(response_clean):
                            if char == '{':
                                brace_count += 1
                            elif char == '}':
                                brace_count -= 1
                                if brace_count == 0:
                                    json_end = i + 1
                                    break
                        
                        if json_end > 0:
                            response_clean = response_clean[:json_end]
                    
                    # Try parsing
                    try:
                        response_data = json.loads(response_clean)
                    except json.JSONDecodeError:
                        # If still fails, try to extract JSON using regex
                        import re
                        json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response_clean)
                        if json_match:
                            response_data = json.loads(json_match.group(0))
                        else:
                            raise
                else:
                    response_data = response
                
                summary_json = {
                    "actor": response_data.get("actor"),
                    "action": response_data.get("action"),
                    "object": response_data.get("object"),
                    "deadline": response_data.get("deadline"),
                    "notes": response_data.get("notes"),
                }
                json_ok_flag = True
            except (json.JSONDecodeError, AttributeError, ValueError) as e:
                logger.warning(f"Failed to parse LLM response for {s.id}: {e}")
                # Try to extract fields using regex as fallback
                try:
                    if isinstance(response, str):
                        actor_match = re.search(r'"actor"\s*:\s*"([^"]+)"', response)
                        action_match = re.search(r'"action"\s*:\s*"([^"]+)"', response)
                        object_match = re.search(r'"object"\s*:\s*"([^"]+)"', response)
                        deadline_match = re.search(r'"deadline"\s*:\s*"([^"]+)"', response) or re.search(r'"deadline"\s*:\s*(null)', response)
                        
                        if actor_match or action_match or object_match:
                            summary_json = {
                                "actor": actor_match.group(1) if actor_match else None,
                                "action": action_match.group(1) if action_match else None,
                                "object": object_match.group(1) if object_match else None,
                                "deadline": deadline_match.group(1) if deadline_match and deadline_match.group(1) != 'null' else None,
                                "notes": None,
                            }
                            json_ok_flag = True
                except Exception:
                    summary_json = {}
            
        except Exception as e:
            print(f"Error processing {s.id}: {e}")
            latency.append((time.time() - start) * 1000.0)
            summary_json = {}
            json_ok_flag = False
        
        json_ok.append(1.0 if json_ok_flag else 0.0)
        
        # Apply same postprocessing as pipeline to ensure consistency
        if json_ok_flag:
            summary_json = postprocess_summary(summary_json, s)
        processed_summaries.append(summary_json if json_ok_flag else {})
        
        gt_sum = (s.ground_truth or {}).get("summary", {})
        sa = slot_acc(
            summary_json if json_ok_flag else {},
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
        rouge = rouge_l_like(
            json.dumps(summary_json if json_ok_flag else {}, ensure_ascii=False),
            json.dumps(gt_sum, ensure_ascii=False)
        )
        p_f, r_f, f1_f = fact_prf(summary_json if json_ok_flag else {}, gt_sum)
        fmt = format_compliance(summary_json if json_ok_flag else {})
        rouge_list.append(rouge)
        fact_p_list.append(p_f)
        fact_r_list.append(r_f)
        fact_f1_list.append(f1_f)
        fmt_ok.append(fmt)
        rows.append(
            {
                "id": s.id,
                "model": "app.services.summarizer:summarize_text",
                "slot_actor": sa["actor"],
                "slot_action": sa["action"],
                "slot_object": sa["object"],
                "slot_deadline": sa["deadline"],
                "json_ok": 1.0 if json_ok_flag else 0.0,
                "format_ok": fmt,
                "rouge_like": rouge,
                "fact_precision": p_f,
                "fact_recall": r_f,
                "fact_f1": f1_f,
                "latency_ms": latency[-1],
            }
        )

    # Write CSV output
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "id", "model", "slot_actor", "slot_action", "slot_object", "slot_deadline",
            "json_ok", "format_ok", "rouge_like", "fact_precision", "fact_recall", "fact_f1",
            "latency_ms"
        ])
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    # Write aggregate results
    agg = {
        "model": "app.services.summarizer:summarize_text",
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
    agg_path = output_path.with_suffix(".aggregate.json")
    with open(agg_path, "w", encoding="utf-8") as f:
        json.dump(agg, f, ensure_ascii=False, indent=2)

    # Write errors
    err_path = output_path.with_suffix(".errors.jsonl")
    with open(err_path, "w", encoding="utf-8") as ef:
        for row, s, pred_summary, gt_summary in zip(rows, samples, processed_summaries, 
                                                     [(s.ground_truth or {}).get("summary", {}) for s in samples]):
            if row["slot_actor"] < 1.0 or row["slot_action"] < 1.0 or row["slot_object"] < 1.0 or row["slot_deadline"] < 1.0:
                ef.write(json.dumps({
                    "id": s.id,
                    "pred_summary": pred_summary,
                    "gt_summary": gt_summary,
                    "summary_slots": {
                        "actor": row["slot_actor"],
                        "action": row["slot_action"],
                        "object": row["slot_object"],
                        "deadline": row["slot_deadline"],
                    }
                }, ensure_ascii=False) + "\n")

    # Print summary
    print(f"\nSummarizer Single Model Evaluation")
    print(f"Model: app.services.summarizer:summarize_text")
    print(f"Total cases: {len(samples)}")
    print(f"Slot Accuracy:")
    print(f"  Actor: {agg['slot_actor_acc']:.4f}")
    print(f"  Action: {agg['slot_action_acc']:.4f}")
    print(f"  Object: {agg['slot_object_acc']:.4f}")
    print(f"  Deadline: {agg['slot_deadline_acc']:.4f}")
    print(f"Fact Metrics:")
    print(f"  Precision: {agg['fact_precision']:.4f}")
    print(f"  Recall: {agg['fact_recall']:.4f}")
    print(f"  F1: {agg['fact_f1']:.4f}")
    print(f"ROUGE-like: {agg['rouge_like']:.4f}")
    print(f"JSON Parse Rate: {agg['json_parse_rate']:.4f}")
    print(f"Format Compliance: {agg['format_compliance']:.4f}")
    print(f"Avg Latency: {agg['latency_avg_ms']:.2f} ms")


if __name__ == "__main__":
    asyncio.run(main())

