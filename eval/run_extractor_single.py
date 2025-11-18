"""
Single-model evaluation script for Extractor.
Tests app.services.extractor:extract_tasks_from_text using eval script logic.
"""

import argparse
import asyncio
import csv
import json
import time
from pathlib import Path
from statistics import mean
from typing import Dict, List

from .pipeline import load_dataset
from .run_pipeline import prf_tasks, due_date_correctness, _normalize_owner


async def main():
    parser = argparse.ArgumentParser(description="Evaluate extractor single model")
    parser.add_argument("--dataset", required=True, help="Path to JSONL dataset")
    parser.add_argument("--output", required=True, help="CSV path for per-sample results")
    parser.add_argument("--lenient", action="store_true", help="Use lenient matching")
    parser.add_argument("--very_lenient", action="store_true", help="Use very lenient matching")
    parser.add_argument("--sim_threshold", type=float, default=0.75, help="Similarity threshold (stricter: 0.75)")
    parser.add_argument("--task_match_k", type=int, default=3, help="Minimum fields to match (k-of-4, stricter: 3)")
    args = parser.parse_args()

    # Import actual extractor function
    from app.services.extractor import extract_tasks_from_text
    
    samples = load_dataset(args.dataset)

    rows = []
    pr_list = []
    rc_list = []
    f1_list = []
    due_list = []
    owner_list = []
    json_ok_list = []

    def owner_match(pred_tasks, gt_tasks) -> float:
        # Normalize all owners (including None -> "me")
        pred_owners = set(_normalize_owner((t or {}).get("owner")) for t in pred_tasks)
        gt_owners = set(_normalize_owner((t or {}).get("owner")) for t in gt_tasks)
        if not pred_owners and not gt_owners:
            return 1.0
        if not pred_owners or not gt_owners:
            return 0.0
        inter = len(pred_owners & gt_owners)
        return inter / max(len(gt_owners), 1)

    for s in samples:
        # Prepare input for extract_tasks_from_text
        text = s.body_text
        subject = s.subject
        sent_date = s.received_at
        
        start = time.time()
        try:
            # Call actual extractor function
            result = await extract_tasks_from_text(text=text, subject=subject, sent_date=sent_date)
            latency_ms = (time.time() - start) * 1000.0
            
            # Extract tasks from result
            pred_tasks_raw = result.get("tasks", []) if isinstance(result, dict) else []
            json_ok_flag = isinstance(result, dict)
            
            # Get raw LLM response to preserve original due text
            pred_tasks = []
            try:
                from app.core.llm import LLMProvider
                from app.core.prompts import EXTRACTION_PROMPT
                
                llm_provider = LLMProvider()
                combined_text = f"Subject: {subject}\n\n{text}" if subject else text
                
                llm_messages = [
                    {"role": "system", "content": EXTRACTION_PROMPT},
                    {"role": "user", "content": combined_text}
                ]
                
                # Get raw response from LLM
                model_id = llm_provider.default_extractor_model
                response = await llm_provider._call_model(llm_messages, model_id=model_id, temperature=0.3)
                
                # Parse response to get raw tasks with original due
                try:
                    if response.strip().startswith('['):
                        raw_tasks = json.loads(response)
                    elif response.strip().startswith('{'):
                        raw_tasks = [json.loads(response)]
                    else:
                        response_clean = response.strip()
                        if '```json' in response_clean:
                            response_clean = response_clean.split('```json')[1].split('```')[0].strip()
                        elif '```' in response_clean:
                            response_clean = response_clean.split('```')[1].split('```')[0].strip()
                        raw_tasks = json.loads(response_clean)
                    
                    # Convert to eval format: {owner, action, object, deadline}
                    for raw_task in raw_tasks:
                        title = raw_task.get("title", "")
                        owner = raw_task.get("owner")
                        due = raw_task.get("due")
                        
                        # Parse action and object from title
                        # Title format: [VERB OBJECT OWNER] or natural language
                        action, obj = parse_action_object_from_title(title)
                        
                        pred_tasks.append({
                            "owner": owner,
                            "action": action,
                            "object": obj,
                            "deadline": due,
                        })
                except json.JSONDecodeError:
                    # Fallback: use formatted tasks
                    pred_tasks = convert_tasks_to_eval_format(pred_tasks_raw)
            except Exception:
                # Fallback: use formatted tasks
                pred_tasks = convert_tasks_to_eval_format(pred_tasks_raw)
            
        except Exception as e:
            print(f"Error processing {s.id}: {e}")
            latency_ms = (time.time() - start) * 1000.0
            pred_tasks = []
            json_ok_flag = False
        
        gt_tasks = (s.ground_truth or {}).get("tasks", [])
        
        # Convert GT tasks to eval format if needed
        gt_tasks_eval = []
        for task in gt_tasks:
            if "action" in task and "object" in task:
                # Already in eval format
                gt_tasks_eval.append({
                    "owner": task.get("owner"),
                    "action": task.get("action"),
                    "object": task.get("object"),
                    "deadline": task.get("deadline") or task.get("due_raw"),
                })
            else:
                # Convert from title format
                title = task.get("title", "")
                owner = task.get("owner")
                due = task.get("due_raw")
                action, obj = parse_action_object_from_title(title)
                gt_tasks_eval.append({
                    "owner": owner,
                    "action": action,
                    "object": obj,
                    "deadline": due,
                })
        
        p, r, f1 = prf_tasks(
            pred_tasks, gt_tasks_eval,
            lenient=args.lenient,
            very_lenient=args.very_lenient,
            sim_threshold=args.sim_threshold,
            task_match_k=args.task_match_k,
            received_at=s.received_at
        )
        pr_list.append(p)
        rc_list.append(r)
        f1_list.append(f1)
        due_list.append(due_date_correctness(pred_tasks, gt_tasks_eval))
        owner_list.append(owner_match(pred_tasks, gt_tasks_eval))
        json_ok_list.append(1.0 if json_ok_flag else 0.0)
        rows.append(
            {
                "id": s.id,
                "model": "app.services.extractor:extract_tasks_from_text",
                "precision": p,
                "recall": r,
                "f1": f1,
                "due_match": due_list[-1],
                "owner_match": owner_list[-1],
                "json_ok": json_ok_list[-1],
                "latency_ms": latency_ms,
            }
        )

    # Write CSV output
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "id", "model", "precision", "recall", "f1", "due_match", "owner_match", "json_ok", "latency_ms"
        ])
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    # Write aggregate results
    agg = {
        "model": "app.services.extractor:extract_tasks_from_text",
        "task_precision": mean(pr_list) if pr_list else 0.0,
        "task_recall": mean(rc_list) if rc_list else 0.0,
        "task_f1": mean(f1_list) if f1_list else 0.0,
        "due_date_correctness": mean(due_list) if due_list else 0.0,
        "owner_match": mean(owner_list) if owner_list else 0.0,
        "json_parse_rate": mean(json_ok_list) if json_ok_list else 1.0,
    }
    agg_path = output_path.with_suffix(".aggregate.json")
    with open(agg_path, "w", encoding="utf-8") as f:
        json.dump(agg, f, ensure_ascii=False, indent=2)

    # Print summary
    print(f"\nExtractor Single Model Evaluation")
    print(f"Model: app.services.extractor:extract_tasks_from_text")
    print(f"Total cases: {len(samples)}")
    print(f"Task Metrics:")
    print(f"  Precision: {agg['task_precision']:.4f}")
    print(f"  Recall: {agg['task_recall']:.4f}")
    print(f"  F1: {agg['task_f1']:.4f}")
    print(f"Due Date Correctness: {agg['due_date_correctness']:.4f}")
    print(f"Owner Match: {agg['owner_match']:.4f}")
    print(f"JSON Parse Rate: {agg['json_parse_rate']:.4f}")


def parse_action_object_from_title(title: str):
    """Parse action and object from title field."""
    import re
    if not title:
        return None, None
    
    # Try to parse [VERB OBJECT OWNER] format
    bracket_match = re.match(r'\[([^\]]+)\]', title)
    if bracket_match:
        content = bracket_match.group(1).strip()
        parts = content.split()
        if len(parts) >= 2:
            action = parts[0].lower()
            if len(parts) >= 3 and parts[-1][0].isupper() and len(parts[-1]) <= 15:
                object_parts = parts[1:-1]
            else:
                object_parts = parts[1:]
            obj = " ".join(object_parts).lower() if object_parts else None
            return action, obj
    
    # Try to parse natural language format
    verb_pattern = r'^(review|submit|send|schedule|prepare|update|complete|approve|finalize|upload|export|remove|attach|check|verify|revise|refresh|resend|align|sync|meet|discuss|decide|agree|propose|edit|look|take|make|ensure|remember|double-check|fix|attend|provide|return|circulate|distribute|transmit|draft|create|write|compile|develop|generate|modify|amend|correct|confirm|acknowledge|validate|affirm|synchronize|reconcile|request|ask|need|require|solicit|petition|remind|notify|alert|inform|announce|report|troubleshoot|resolve|debug|investigate|escalate|process|handle|manage|deal with|address)'
    verb_match = re.match(verb_pattern, title.lower())
    if verb_match:
        action = verb_match.group(1)
        remaining = title[verb_match.end():].strip()
        and_verb_match = re.match(r'^\s+and\s+(send|submit|upload|provide|return)', remaining.lower())
        if and_verb_match:
            obj = remaining[and_verb_match.end():].strip()
        else:
            obj = remaining
        obj = re.sub(r'^(the|a|an|your|our|updated|new|latest)\s+', '', obj, flags=re.IGNORECASE)
        obj = re.sub(r'\s+(and|by|before|on|at|from|to|for|with).*$', '', obj, flags=re.IGNORECASE)
        obj = obj.strip()
        return action, obj if obj else None
    
    # Fallback: first word as action, rest as object
    parts = title.split()
    if len(parts) >= 2:
        return parts[0].lower(), " ".join(parts[1:]).lower()
    elif len(parts) == 1:
        return parts[0].lower(), None
    
    return None, None


def convert_tasks_to_eval_format(tasks: List[Dict]) -> List[Dict]:
    """Convert tasks from {title, owner, due_iso} to {owner, action, object, deadline} format."""
    result = []
    for task in tasks:
        title = task.get("title", "")
        owner = task.get("owner")
        due_iso = task.get("due_iso")
        due = task.get("due")
        
        action, obj = parse_action_object_from_title(title)
        
        result.append({
            "owner": owner,
            "action": action,
            "object": obj,
            "deadline": due or due_iso,
        })
    return result


if __name__ == "__main__":
    asyncio.run(main())

