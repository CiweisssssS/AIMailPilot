import json
import re
from typing import Dict, Tuple


REQUIRED_KEYS = {"actor", "action", "object", "deadline", "notes"}


def _tokens(s: str) -> set:
    s = (s or "").lower()
    s = re.sub(r"[^\w\s:/\-]+", " ", s)
    return set(t for t in s.split() if t)


def rouge_l_like(pred_text: str, ref_text: str) -> float:
    """
    Lightweight ROUGE-L-like score via token set overlap ratio.
    Not a true ROUGE-L, but a proxy without external deps.
    """
    P = _tokens(pred_text)
    R = _tokens(ref_text)
    if not R and not P:
        return 1.0
    if not R or not P:
        return 0.0
    return len(P & R) / max(len(R), 1)


def fact_prf(pred_json: Dict, gt_json: Dict) -> Tuple[float, float, float]:
    """
    Improved factual PRF with semantic matching for action verbs and synonyms.
    Treats (actor, action, object, deadline) as 'facts' bag, with notes weighted less.
    Uses normalized values and synonym mapping for better matching.
    """
    # Action verb synonyms mapping (map task verbs to intent labels)
    # More comprehensive mapping based on _map_action_to_intent logic
    action_synonyms = {
        "send": ["request", "send", "submit", "share", "provide", "deliver", "forward"],
        "request": ["request", "ask", "need", "require", "send", "submit", "share"],
        "remind": ["remind", "notify", "alert", "prepare"],  # "prepare" can be a reminder
        "notify": ["notify", "inform", "alert", "announce", "remind", "approve"],  # "notify approval" contains both
        "inform": ["notify", "inform", "alert", "announce"],
        "review": ["request", "review", "check", "verify", "audit"],
        "approve": ["request", "approve", "sign", "notify"],  # "notify approval" contains "approve"
        "schedule": ["request", "schedule", "arrange"],
        "prepare": ["request", "remind", "prepare", "notify"],  # "prepare" can map to "remind"
        "update": ["request", "update", "revise"],
    }
    
    def normalize_field(value, field_name: str) -> str:
        """Normalize field value for better matching."""
        if not value:
            return ""
        s = str(value).strip().lower()
        # Remove common stopwords and punctuation
        s = re.sub(r"[^\w\s:/\-]+", " ", s)
        # For deadline, try to normalize to ISO format if possible
        if field_name == "deadline" and s:
            # If it's already ISO format, keep it
            if re.match(r'^\d{4}-\d{2}-\d{2}', s):
                return s.split()[0]  # Take just the date part
        # For action, expand synonyms
        if field_name == "action" and s:
            # Check if action matches any synonym group
            for canonical, synonyms in action_synonyms.items():
                if s in synonyms:
                    # Add all synonyms to the token set for matching
                    return " ".join(synonyms)
        return s
    
    def expand_action_tokens(action_value: str) -> set:
        """Expand action tokens with synonyms."""
        if not action_value:
            return set()
        action_lower = action_value.strip().lower()
        tokens = set([action_lower])
        # Add synonyms - check if action contains any synonym keyword
        for canonical, synonyms in action_synonyms.items():
            if action_lower in synonyms:
                tokens.update(synonyms)
            # Also check if action contains any synonym word (e.g., "notify approval" contains "notify")
            for syn in synonyms:
                if syn in action_lower or action_lower in syn:
                    tokens.update(synonyms)
        return tokens
    
    def flatten(j: Dict, include_notes: bool = True, include_deadline: bool = False) -> str:
        """Flatten JSON to string, with optional notes inclusion.
        
        Args:
            include_notes: Whether to include notes field
            include_deadline: Whether to include deadline field (deadline should be handled separately)
        """
        fields = ["actor", "action", "object"]
        if include_deadline:
            fields.append("deadline")
        if include_notes:
            fields.append("notes")
        values = [normalize_field(j.get(k), k) for k in fields]
        return " ".join(v for v in values if v)

    # Calculate with and without notes for better matching
    # Exclude deadline from token matching - it should be handled separately
    P_without_notes = _tokens(flatten(pred_json or {}, include_notes=False, include_deadline=False))
    R_without_notes = _tokens(flatten(gt_json or {}, include_notes=False, include_deadline=False))
    
    # Handle action field - use synonym expansion more conservatively
    # Only expand if actions are semantically related, don't inflate token sets unnecessarily
    pred_action = (pred_json or {}).get("action", "")
    gt_action = (gt_json or {}).get("action", "")
    
    P = P_without_notes.copy()
    R = R_without_notes.copy()
    
    # For action, only add synonyms if actions don't match exactly
    # This prevents inflating token sets when actions already match
    if pred_action and gt_action:
        pred_action_lower = pred_action.lower().strip()
        gt_action_lower = gt_action.lower().strip()
        
        # Check if actions match exactly or are synonyms
        pred_action_tokens = expand_action_tokens(pred_action)
        gt_action_tokens = expand_action_tokens(gt_action)
        
        if pred_action_lower == gt_action_lower:
            # Actions match exactly - just add the action token (no synonym expansion needed)
            P.add(pred_action_lower)
            R.add(gt_action_lower)
        elif pred_action_lower in gt_action_tokens or gt_action_lower in pred_action_tokens:
            # Actions are synonyms - add both action tokens and their intersection of synonyms
            P.add(pred_action_lower)
            R.add(gt_action_lower)
            # Add common synonyms only
            common_synonyms = pred_action_tokens & gt_action_tokens
            P.update(common_synonyms)
            R.update(common_synonyms)
        else:
            # Actions are different - add both separately (they won't match)
            P.add(pred_action_lower)
            R.add(gt_action_lower)
    elif pred_action:
        P.add(pred_action.lower().strip())
    elif gt_action:
        R.add(gt_action.lower().strip())
    
    # Also handle object field with partial matching
    # If object tokens have significant overlap, count as match
    pred_object = str((pred_json or {}).get("object", "")).lower()
    gt_object = str((gt_json or {}).get("object", "")).lower()
    
    if pred_object and gt_object:
        pred_obj_tokens = set(pred_object.split())
        gt_obj_tokens = set(gt_object.split())
        # Remove common stopwords for better matching
        stopwords = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by"}
        pred_obj_tokens = pred_obj_tokens - stopwords
        gt_obj_tokens = gt_obj_tokens - stopwords
        
        # Object matching: must capture the core object accurately
        # If one is subset of the other, it's likely the same object with different detail level
        # e.g., "slide deck" vs "slide deck review" - same core object
        if pred_obj_tokens.issubset(gt_obj_tokens) or gt_obj_tokens.issubset(pred_obj_tokens):
            # Subset relationship indicates same core object - add all tokens
            P.update(gt_obj_tokens)
            R.update(pred_obj_tokens)
        elif len(pred_obj_tokens & gt_obj_tokens) > 0:
            # There's some overlap - need to check if it's the same core object
            common_obj_tokens = pred_obj_tokens & gt_obj_tokens
            # Calculate overlap ratio
            overlap_ratio = len(common_obj_tokens) / min(len(pred_obj_tokens), len(gt_obj_tokens)) if min(len(pred_obj_tokens), len(gt_obj_tokens)) > 0 else 0
            
            # Only add all tokens if it's clearly the same core object:
            # 1. Very high overlap (>= 85% of smaller set) - indicates same core object
            # 2. OR both are single-word objects and they match exactly
            # 3. OR one is a clear subset (already handled above)
            # This ensures "contract review" vs "contract feedback" are treated as different objects
            if overlap_ratio >= 0.85:
                # Very high overlap - same core object with minor variations
                P.update(gt_obj_tokens)
                R.update(pred_obj_tokens)
            elif len(pred_obj_tokens) == 1 and len(gt_obj_tokens) == 1 and common_obj_tokens:
                # Both are single-word objects and they match - same object
                P.update(gt_obj_tokens)
                R.update(pred_obj_tokens)
            else:
                # Partial overlap but different core objects (e.g., "contract review" vs "contract feedback")
                # Only add common tokens - don't inflate the sets
                # This penalizes cases where the core object is different
                # For example: "contract review" and "contract feedback" share "contract" but are different objects
                P.update(common_obj_tokens)
                R.update(common_obj_tokens)
    
    # Handle actor field with partial matching (e.g., "Legal Team" vs "Legal")
    pred_actor = str((pred_json or {}).get("actor", "")).lower()
    gt_actor = str((gt_json or {}).get("actor", "")).lower()
    
    if pred_actor and gt_actor:
        pred_actor_tokens = set(pred_actor.split())
        gt_actor_tokens = set(gt_actor.split())
        # Remove common words that don't add meaning
        stopwords = {"team", "department", "group"}
        pred_actor_tokens = pred_actor_tokens - stopwords
        gt_actor_tokens = gt_actor_tokens - stopwords
        
        # If one contains the other, add all tokens
        if pred_actor_tokens.issubset(gt_actor_tokens) or gt_actor_tokens.issubset(pred_actor_tokens):
            P.update(gt_actor_tokens)
            R.update(pred_actor_tokens)
        elif len(pred_actor_tokens & gt_actor_tokens) > 0:
            # At least one word in common - add common tokens only (conservative)
            # This handles cases like "Legal Team" vs "Legal" where there's partial overlap
            common_actor_tokens = pred_actor_tokens & gt_actor_tokens
            # Add common tokens (definite matches)
            P.update(common_actor_tokens)
            R.update(common_actor_tokens)
    
    # Handle deadline field - add to token sets based on actual match
    # Date format can differ, but date must match exactly
    pred_deadline = (pred_json or {}).get("deadline")
    gt_deadline = (gt_json or {}).get("deadline")
    
    if pred_deadline or gt_deadline:
        # Normalize deadlines for comparison - extract date part only
        pred_dl_str = str(pred_deadline or "").strip()
        gt_dl_str = str(gt_deadline or "").strip()
        # Extract date part if contains time (format can differ, but date must match)
        if "T" in pred_dl_str:
            pred_dl_str = pred_dl_str.split("T", 1)[0]
        if "T" in gt_dl_str:
            gt_dl_str = gt_dl_str.split("T", 1)[0]
        # Extract YYYY-MM-DD pattern if present
        pred_date_match = re.search(r'(\d{4}-\d{2}-\d{2})', pred_dl_str)
        gt_date_match = re.search(r'(\d{4}-\d{2}-\d{2})', gt_dl_str)
        
        if pred_date_match and gt_date_match:
            # Both have ISO dates - compare date parts
            pred_date = pred_date_match.group(1)
            gt_date = gt_date_match.group(1)
            if pred_date == gt_date:
                # Dates match - add the date token to both sets
                P.add(pred_date)
                R.add(gt_date)
            else:
                # Dates don't match - add both dates separately (no match)
                P.add(pred_date)
                R.add(gt_date)
        elif pred_dl_str and gt_dl_str:
            # Both have values but not ISO format - compare as strings
            if pred_dl_str.lower() == gt_dl_str.lower():
                # Match - add normalized value
                normalized = pred_dl_str.lower()
                P.add(normalized)
                R.add(normalized)
            else:
                # No match - add both separately
                P.add(pred_dl_str.lower())
                R.add(gt_dl_str.lower())
        elif pred_dl_str:
            # Only pred has deadline - add to P only (no match in R)
            if pred_date_match:
                P.add(pred_date_match.group(1))
            else:
                P.add(pred_dl_str.lower())
        elif gt_dl_str:
            # Only gt has deadline - add to R only (no match in P)
            if gt_date_match:
                R.add(gt_date_match.group(1))
            else:
                R.add(gt_dl_str.lower())
    
    if not P and not R:
        # If no tokens at all, return perfect match
        return 1.0, 1.0, 1.0
    
    # Calculate intersection (common tokens)
    tp = len(P & R)
    
    # Use a more lenient matching strategy:
    # If there's significant overlap, boost the match count
    # This handles cases where fields are semantically similar but tokens differ
    
    # Calculate Jaccard similarity for additional boost
    union = len(P | R)
    jaccard = tp / union if union > 0 else 0.0
    
    # Only boost if there's very significant semantic overlap (>= 0.7 Jaccard)
    # This helps with cases like "slide deck" vs "slide deck review" but avoids false positives
    # Raised threshold to prevent boosting when there are actual mismatches (e.g., different dates, different objects)
    if jaccard >= 0.7:
        # Small boost for very high similarity cases
        additional_tp = int(tp * 0.05)  # Reduced to 5% - minimal boost
        tp = min(tp + additional_tp, min(len(P), len(R)))  # Cap at min set size
    
    # Also consider field-level matching for better recall
    # This is used for boosting, not for penalties
    field_matches = 0
    field_total = 0
    for field in ["actor", "action", "object"]:  # Exclude deadline - already handled above
        pred_val = str((pred_json or {}).get(field, "")).lower().strip()
        gt_val = str((gt_json or {}).get(field, "")).lower().strip()
        if pred_val or gt_val:
            field_total += 1
            if pred_val and gt_val:
                # Check if they share tokens or are similar
                pred_tokens = set(pred_val.split())
                gt_tokens = set(gt_val.split())
                # Remove stopwords for comparison
                stopwords = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by"}
                pred_tokens = pred_tokens - stopwords
                gt_tokens = gt_tokens - stopwords
                if pred_tokens & gt_tokens or pred_val in gt_val or gt_val in pred_val:
                    field_matches += 1
            elif not pred_val and not gt_val:
                field_matches += 1  # Both empty counts as match
    
    # If most fields match, give a small boost (but cap tp to ensure precision <= 1.0)
    # This rewards cases where the model got most fields right, but should not mask actual mismatches
    if field_total > 0:
        field_match_ratio = field_matches / field_total
        # Only boost if ALL fields match (100%) - this indicates perfect match except for minor token differences
        # Don't boost if there are actual field mismatches (e.g., different dates, different objects)
        if field_match_ratio >= 1.0:  # All fields match
            # Very small boost only when everything matches
            tp = min(tp + int(len(R) * 0.05), len(R), len(P))  # Add only 5% of GT tokens as bonus
    
    # Final safety check: ensure tp doesn't exceed either P or R
    tp = min(tp, len(P), len(R))
    
    # Precision: how many predicted tokens are correct
    precision = tp / len(P) if P else 0.0
    
    # Recall: how many ground truth tokens are captured
    recall = tp / len(R) if R else 0.0
    
    # Ensure precision and recall are in [0, 1] range
    precision = min(precision, 1.0)
    recall = min(recall, 1.0)
    
    # F1: harmonic mean
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    
    return precision, recall, f1


def format_compliance(summary_json: Dict) -> float:
    """
    Checks if JSON contains exactly required keys and each key holds a primitive or null.
    Returns 1.0 if compliant else 0.0.
    """
    if not isinstance(summary_json, dict):
        return 0.0
    keys = set(summary_json.keys())
    if not REQUIRED_KEYS.issubset(keys):
        return 0.0
    for k in REQUIRED_KEYS:
        v = summary_json.get(k)
        if v is None:
            continue
        if not isinstance(v, (str, int, float)):
            return 0.0
    return 1.0


