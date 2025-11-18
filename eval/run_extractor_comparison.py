"""
Compare Gemini Flash vs GPT-4o-mini for extractor using eval dataset
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


async def test_model(model_id: str, samples, lenient: bool, very_lenient: bool, sim_threshold: float, task_match_k: int):
    """Test a specific model and return results"""
    from app.core.llm import LLMProvider
    from app.core.prompts import EXTRACTION_PROMPT
    
    llm_provider = LLMProvider()
    
    pr_list = []
    rc_list = []
    f1_list = []
    due_list = []
    owner_list = []
    json_ok_list = []
    strict_tp_list = []
    partial_tp_list = []
    
    def owner_match(pred_tasks, gt_tasks) -> float:
        pred_owners = set(_normalize_owner((t or {}).get("owner")) for t in pred_tasks)
        gt_owners = set(_normalize_owner((t or {}).get("owner")) for t in gt_tasks)
        if not pred_owners and not gt_owners:
            return 1.0
        if not pred_owners or not gt_owners:
            return 0.0
        inter = len(pred_owners & gt_owners)
        return inter / max(len(gt_owners), 1)
    
    for s in samples:
        text = s.body_text
        subject = s.subject
        sent_date = s.received_at
        
        try:
            combined_text = f"Subject: {subject}\n\n{text}" if subject else text
            llm_messages = [
                {"role": "system", "content": EXTRACTION_PROMPT},
                {"role": "user", "content": combined_text}
            ]
            
            # Get raw response from LLM
            response = await llm_provider._call_model(llm_messages, model_id=model_id, temperature=0.3)
            
            # Parse response
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
                
                # Convert to eval format
                pred_tasks = []
                for raw_task in raw_tasks:
                    title = raw_task.get("title", "")
                    owner = raw_task.get("owner")
                    due = raw_task.get("due")
                    action, obj = parse_action_object_from_title(title)
                    pred_tasks.append({
                        "owner": owner,
                        "action": action,
                        "object": obj,
                        "deadline": due,
                    })
                json_ok_flag = True
            except json.JSONDecodeError:
                pred_tasks = []
                json_ok_flag = False
        except Exception as e:
            print(f"Error processing {s.id}: {e}")
            pred_tasks = []
            json_ok_flag = False
        
        # Convert GT tasks to eval format
        gt_tasks = (s.ground_truth or {}).get("tasks", [])
        gt_tasks_eval = []
        for task in gt_tasks:
            if "action" in task and "object" in task:
                gt_tasks_eval.append({
                    "owner": task.get("owner"),
                    "action": task.get("action"),
                    "object": task.get("object"),
                    "deadline": task.get("deadline") or task.get("due_raw"),
                })
            else:
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
        
        # Calculate metrics
        result = prf_tasks(
            pred_tasks, gt_tasks_eval,
            lenient=lenient,
            very_lenient=very_lenient,
            sim_threshold=sim_threshold,
            task_match_k=task_match_k,
            received_at=sent_date
        )
        
        # prf_tasks returns (precision, recall, f1) tuple
        p, r, f1 = result
        
        # Calculate strict/partial TP
        from eval.run_pipeline import _normalize_text, _normalize_date
        import json as json_lib
        
        pred_set = set(json_lib.dumps({
            "owner": _normalize_owner(t.get("owner")),
            "action": _normalize_text(t.get("action") or ""),
            "object": _normalize_text(t.get("object") or ""),
            "deadline": _normalize_date(t.get("deadline"), received_at=sent_date),
        }, sort_keys=True) for t in pred_tasks)
        
        gt_set = set(json_lib.dumps({
            "owner": _normalize_owner(t.get("owner")),
            "action": _normalize_text(t.get("action") or ""),
            "object": _normalize_text(t.get("object") or ""),
            "deadline": _normalize_date(t.get("deadline"), received_at=sent_date),
        }, sort_keys=True) for t in gt_tasks_eval)
        
        strict_tp = len(pred_set & gt_set)
        
        # Calculate total TP from prf_tasks
        total_pred = len(pred_tasks)
        total_gt = len(gt_tasks_eval)
        
        if not very_lenient:
            total_tp = len(pred_set & gt_set)
        else:
            # Use greedy matching
            from eval.run_pipeline import _similarity
            used_gt = set()
            total_tp = 0
            for p in pred_tasks:
                best_j = None
                best_score = -1
                for j, g in enumerate(gt_tasks_eval):
                    if j in used_gt:
                        continue
                    match_count = 0
                    if _normalize_owner(p.get("owner")) == _normalize_owner(g.get("owner")) or (
                        _normalize_owner(p.get("owner")) in {"me", ""} and _normalize_owner(g.get("owner")) in {"me", ""}
                    ):
                        match_count += 1
                    if _similarity(p.get("action") or "", g.get("action") or "") >= sim_threshold:
                        match_count += 1
                    if _similarity(p.get("object") or "", g.get("object") or "") >= sim_threshold:
                        match_count += 1
                    if _normalize_date(p.get("deadline"), received_at=sent_date) == _normalize_date(g.get("deadline"), received_at=sent_date):
                        match_count += 1
                    if match_count > best_score:
                        best_score = match_count
                        best_j = j
                if best_j is not None and best_score >= task_match_k:
                    total_tp += 1
                    used_gt.add(best_j)
        
        partial_tp = max(0, total_tp - strict_tp)
        
        # Ensure p, r, f1 are floats
        pr_list.append(float(p) if p is not None else 0.0)
        rc_list.append(float(r) if r is not None else 0.0)
        f1_list.append(float(f1) if f1 is not None else 0.0)
        due_list.append(due_date_correctness(pred_tasks, gt_tasks_eval))
        owner_list.append(owner_match(pred_tasks, gt_tasks_eval))
        json_ok_list.append(1.0 if json_ok_flag else 0.0)
        strict_tp_list.append(strict_tp)
        partial_tp_list.append(partial_tp)
    
    return {
        "model": model_id,
        "task_precision": mean(pr_list) if pr_list else 0.0,
        "task_recall": mean(rc_list) if rc_list else 0.0,
        "task_f1": mean(f1_list) if f1_list else 0.0,
        "due_date_correctness": mean(due_list) if due_list else 0.0,
        "owner_match": mean(owner_list) if owner_list else 0.0,
        "json_parse_rate": mean(json_ok_list) if json_ok_list else 1.0,
        "strict_tp": sum(strict_tp_list),
        "partial_tp": sum(partial_tp_list),
        "total_tp": sum(strict_tp_list) + sum(partial_tp_list),
    }


async def main():
    parser = argparse.ArgumentParser(description="Compare extractor models")
    parser.add_argument("--dataset", required=True, help="Path to JSONL dataset")
    parser.add_argument("--lenient", action="store_true", help="Use lenient matching")
    parser.add_argument("--very_lenient", action="store_true", help="Use very lenient matching")
    parser.add_argument("--sim_threshold", type=float, default=0.75, help="Similarity threshold (stricter: 0.75)")
    parser.add_argument("--task_match_k", type=int, default=3, help="Minimum fields to match (k-of-4, stricter: 3)")
    args = parser.parse_args()
    
    samples = load_dataset(args.dataset)
    
    print("=" * 70)
    print("Extractor Model Comparison")
    print("=" * 70)
    print(f"Dataset: {args.dataset}")
    print(f"Total cases: {len(samples)}")
    print(f"Mode: {'very_lenient' if args.very_lenient else 'lenient' if args.lenient else 'strict'}")
    print()
    
    # Test Gemini Flash
    print("Testing Gemini Flash...")
    gemini_result = await test_model(
        "google:gemini-flash",
        samples,
        args.lenient,
        args.very_lenient,
        args.sim_threshold,
        args.task_match_k
    )
    
    # Test GPT-4o-mini
    print("Testing GPT-4o-mini...")
    gpt_result = await test_model(
        "openai:gpt-4o-mini",
        samples,
        args.lenient,
        args.very_lenient,
        args.sim_threshold,
        args.task_match_k
    )
    
    # Print comparison
    print("\n" + "=" * 70)
    print("Results Comparison")
    print("=" * 70)
    print(f"\n{'Metric':<25} {'Gemini Flash':<20} {'GPT-4o-mini':<20}")
    print("-" * 70)
    print(f"{'TP (strict matches)':<25} {gemini_result['strict_tp']:<20} {gpt_result['strict_tp']:<20}")
    print(f"{'TP (partial matches)':<25} {gemini_result['partial_tp']:<20} {gpt_result['partial_tp']:<20}")
    print(f"{'TP (total)':<25} {gemini_result['total_tp']:<20} {gpt_result['total_tp']:<20}")
    print(f"{'Task Precision':<25} {gemini_result['task_precision']:<20.4f} {gpt_result['task_precision']:<20.4f}")
    print(f"{'Task Recall':<25} {gemini_result['task_recall']:<20.4f} {gpt_result['task_recall']:<20.4f}")
    print(f"{'Task F1':<25} {gemini_result['task_f1']:<20.4f} {gpt_result['task_f1']:<20.4f}")
    print(f"{'Owner match rate':<25} {gemini_result['owner_match']:<20.4f} {gpt_result['owner_match']:<20.4f}")
    print(f"{'Due match rate':<25} {gemini_result['due_date_correctness']:<20.4f} {gpt_result['due_date_correctness']:<20.4f}")
    print()


if __name__ == "__main__":
    asyncio.run(main())

