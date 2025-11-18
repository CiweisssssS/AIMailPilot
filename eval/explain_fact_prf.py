"""
Detailed explanation of fact_prf calculation
"""
import json
import re
from typing import Dict, Tuple

def _tokens(s: str) -> set:
    s = (s or "").lower()
    s = re.sub(r"[^\w\s:/\-]+", " ", s)
    return set(t for t in s.split() if t)

def explain_fact_prf(pred_json: Dict, gt_json: Dict) -> None:
    """Explain how fact_prf calculates Precision, Recall, and F1"""
    
    print("=" * 70)
    print("Fact PRF 计算详解")
    print("=" * 70)
    print(f"预测值 (Predicted): {json.dumps(pred_json, indent=2, ensure_ascii=False)}")
    print(f"真实值 (Ground Truth): {json.dumps(gt_json, indent=2, ensure_ascii=False)}")
    print()
    
    # Step 1: Base token sets (excluding deadline and notes)
    def normalize_field(value, field_name: str) -> str:
        if not value:
            return ""
        s = str(value).strip().lower()
        s = re.sub(r"[^\w\s:/\-]+", " ", s)
        return s
    
    def flatten(j: Dict, include_notes: bool = False, include_deadline: bool = False) -> str:
        fields = ["actor", "action", "object"]
        if include_deadline:
            fields.append("deadline")
        if include_notes:
            fields.append("notes")
        values = [normalize_field(j.get(k), k) for k in fields]
        return " ".join(v for v in values if v)
    
    P_base = _tokens(flatten(pred_json or {}, include_notes=False, include_deadline=False))
    R_base = _tokens(flatten(gt_json or {}, include_notes=False, include_deadline=False))
    
    print("步骤 1: 基础 token 集合（actor, action, object，排除 deadline）")
    print(f"  P_base = {sorted(P_base)} (大小: {len(P_base)})")
    print(f"  R_base = {sorted(R_base)} (大小: {len(R_base)})")
    print()
    
    # Step 2: Handle action field
    P = P_base.copy()
    R = R_base.copy()
    
    pred_action = (pred_json or {}).get("action", "")
    gt_action = (gt_json or {}).get("action", "")
    
    if pred_action and gt_action:
        pred_action_lower = pred_action.lower().strip()
        gt_action_lower = gt_action.lower().strip()
        
        if pred_action_lower == gt_action_lower:
            P.add(pred_action_lower)
            R.add(gt_action_lower)
            print(f"步骤 2: Action 字段匹配 - 添加 \"{pred_action_lower}\" 到两个集合")
        else:
            P.add(pred_action_lower)
            R.add(gt_action_lower)
            print(f"步骤 2: Action 字段不同 - 添加 \"{pred_action_lower}\" 到 P, \"{gt_action_lower}\" 到 R")
    
    print(f"  P after action = {sorted(P)} (大小: {len(P)})")
    print(f"  R after action = {sorted(R)} (大小: {len(R)})")
    print()
    
    # Step 3: Handle object field
    pred_object = str((pred_json or {}).get("object", "")).lower()
    gt_object = str((gt_json or {}).get("object", "")).lower()
    
    if pred_object and gt_object:
        pred_obj_tokens = set(pred_object.split())
        gt_obj_tokens = set(gt_object.split())
        stopwords = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by"}
        pred_obj_tokens = pred_obj_tokens - stopwords
        gt_obj_tokens = gt_obj_tokens - stopwords
        
        if pred_obj_tokens.issubset(gt_obj_tokens) or gt_obj_tokens.issubset(pred_obj_tokens):
            P.update(gt_obj_tokens)
            R.update(pred_obj_tokens)
            print(f"步骤 3: Object 字段 - 子集关系，添加所有 token")
        elif len(pred_obj_tokens & gt_obj_tokens) > 0:
            common_obj_tokens = pred_obj_tokens & gt_obj_tokens
            overlap_ratio = len(common_obj_tokens) / min(len(pred_obj_tokens), len(gt_obj_tokens)) if min(len(pred_obj_tokens), len(gt_obj_tokens)) > 0 else 0
            if overlap_ratio >= 0.85:
                P.update(gt_obj_tokens)
                R.update(pred_obj_tokens)
                print(f"步骤 3: Object 字段 - 高重叠 ({overlap_ratio:.1%})，添加所有 token")
            else:
                P.update(common_obj_tokens)
                R.update(common_obj_tokens)
                print(f"步骤 3: Object 字段 - 部分重叠 ({overlap_ratio:.1%})，只添加共同 token: {common_obj_tokens}")
        else:
            P.update(pred_obj_tokens)
            R.update(gt_obj_tokens)
            print(f"步骤 3: Object 字段 - 无重叠，添加所有 token（不会匹配）")
    
    print(f"  P after object = {sorted(P)} (大小: {len(P)})")
    print(f"  R after object = {sorted(R)} (大小: {len(R)})")
    print()
    
    # Step 4: Handle actor field
    pred_actor = str((pred_json or {}).get("actor", "")).lower()
    gt_actor = str((gt_json or {}).get("actor", "")).lower()
    
    if pred_actor and gt_actor:
        pred_actor_tokens = set(pred_actor.split())
        gt_actor_tokens = set(gt_actor.split())
        stopwords = {"team", "department", "group"}
        pred_actor_tokens = pred_actor_tokens - stopwords
        gt_actor_tokens = gt_actor_tokens - stopwords
        
        if pred_actor_tokens.issubset(gt_actor_tokens) or gt_actor_tokens.issubset(pred_actor_tokens):
            P.update(gt_actor_tokens)
            R.update(pred_actor_tokens)
            print(f"步骤 4: Actor 字段 - 子集关系，添加所有 token")
        elif len(pred_actor_tokens & gt_actor_tokens) > 0:
            common_actor_tokens = pred_actor_tokens & gt_actor_tokens
            P.update(common_actor_tokens)
            R.update(common_actor_tokens)
            print(f"步骤 4: Actor 字段 - 部分重叠，只添加共同 token: {common_actor_tokens}")
    
    print(f"  P after actor = {sorted(P)} (大小: {len(P)})")
    print(f"  R after actor = {sorted(R)} (大小: {len(R)})")
    print()
    
    # Step 5: Handle deadline field
    pred_deadline = (pred_json or {}).get("deadline")
    gt_deadline = (gt_json or {}).get("deadline")
    
    if pred_deadline or gt_deadline:
        pred_dl_str = str(pred_deadline or "").strip()
        gt_dl_str = str(gt_deadline or "").strip()
        if "T" in pred_dl_str:
            pred_dl_str = pred_dl_str.split("T", 1)[0]
        if "T" in gt_dl_str:
            gt_dl_str = gt_dl_str.split("T", 1)[0]
        pred_date_match = re.search(r'(\d{4}-\d{2}-\d{2})', pred_dl_str)
        gt_date_match = re.search(r'(\d{4}-\d{2}-\d{2})', gt_dl_str)
        
        if pred_date_match and gt_date_match:
            pred_date = pred_date_match.group(1)
            gt_date = gt_date_match.group(1)
            if pred_date == gt_date:
                P.add(pred_date)
                R.add(gt_date)
                print(f"步骤 5: Deadline 字段 - 日期匹配，添加 \"{pred_date}\" 到两个集合")
            else:
                P.add(pred_date)
                R.add(gt_date)
                print(f"步骤 5: Deadline 字段 - 日期不匹配，添加 \"{pred_date}\" 到 P, \"{gt_date}\" 到 R")
    
    print(f"  P final = {sorted(P)} (大小: {len(P)})")
    print(f"  R final = {sorted(R)} (大小: {len(R)})")
    print()
    
    # Step 6: Calculate intersection
    tp = len(P & R)
    union = len(P | R)
    jaccard = tp / union if union > 0 else 0.0
    
    print("步骤 6: 计算交集和相似度")
    print(f"  P (预测 token 集合) = {sorted(P)}")
    print(f"  R (真实 token 集合) = {sorted(R)}")
    print(f"  P & R (交集，真正例) = {sorted(P & R)}")
    print(f"  |P| = {len(P)}")
    print(f"  |R| = {len(R)}")
    print(f"  |P & R| = {tp}")
    print(f"  |P | R| (并集) = {union}")
    print(f"  Jaccard 相似度 = |P & R| / |P | R| = {tp} / {union} = {jaccard:.4f}")
    print()
    
    # Step 7: Apply boosting
    original_tp = tp
    if jaccard >= 0.7:
        additional_tp = int(tp * 0.05)
        tp = min(tp + additional_tp, min(len(P), len(R)))
        print(f"步骤 7: Jaccard >= 0.7，应用 5% boosting")
        print(f"  tp: {original_tp} -> {tp} (增加 {tp - original_tp})")
    else:
        print(f"步骤 7: Jaccard < 0.7，不应用 boosting")
    print()
    
    # Step 8: Field-level boosting
    field_matches = 0
    field_total = 0
    for field in ["actor", "action", "object"]:
        pred_val = str((pred_json or {}).get(field, "")).lower().strip()
        gt_val = str((gt_json or {}).get(field, "")).lower().strip()
        if pred_val or gt_val:
            field_total += 1
            if pred_val and gt_val:
                pred_tokens = set(pred_val.split())
                gt_tokens = set(gt_val.split())
                stopwords = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by"}
                pred_tokens = pred_tokens - stopwords
                gt_tokens = gt_tokens - stopwords
                if pred_tokens & gt_tokens or pred_val in gt_val or gt_val in pred_val:
                    field_matches += 1
            elif not pred_val and not gt_val:
                field_matches += 1
    
    if field_total > 0:
        field_match_ratio = field_matches / field_total
        print(f"步骤 8: 字段级匹配检查")
        print(f"  匹配字段数: {field_matches} / {field_total} = {field_match_ratio:.1%}")
        if field_match_ratio >= 1.0:
            boost_before = tp
            tp = min(tp + int(len(R) * 0.05), len(R), len(P))
            print(f"  所有字段匹配，应用 5% field-level boosting")
            print(f"  tp: {boost_before} -> {tp} (增加 {tp - boost_before})")
        else:
            print(f"  不是所有字段匹配，不应用 field-level boosting")
    print()
    
    # Step 9: Final metrics
    precision = tp / len(P) if P else 0.0
    recall = tp / len(R) if R else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    
    print("步骤 9: 最终指标计算")
    print(f"  Precision (精确率) = tp / |P| = {tp} / {len(P)} = {precision:.4f}")
    print(f"    → 预测的 token 中有 {precision:.1%} 是正确的")
    print()
    print(f"  Recall (召回率) = tp / |R| = {tp} / {len(R)} = {recall:.4f}")
    print(f"    → 真实 token 中有 {recall:.1%} 被正确预测")
    print()
    print(f"  F1 = 2 * Precision * Recall / (Precision + Recall)")
    print(f"     = 2 * {precision:.4f} * {recall:.4f} / ({precision:.4f} + {recall:.4f})")
    print(f"     = {f1:.4f}")
    print()
    print("=" * 70)
    
    return precision, recall, f1

if __name__ == "__main__":
    # Example from errors.jsonl
    pred = {"actor": "John", "action": "request", "object": "slide deck review", "deadline": "2025-11-13", "notes": None}
    gt = {"actor": "John", "action": "request", "object": "slide deck review", "deadline": "2025-11-12", "notes": "Verify KPI charts accuracy"}
    
    explain_fact_prf(pred, gt)

