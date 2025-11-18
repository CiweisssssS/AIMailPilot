import json
import os
import time
from dataclasses import asdict
from typing import Dict, List, Tuple

from .common.types import EmailSample, ModelOutput
from .models.registry import get_model_client


def load_dataset(path: str) -> List[EmailSample]:
    samples: List[EmailSample] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            obj = json.loads(line)
            samples.append(
                EmailSample(
                    id=obj["id"],
                    subject=obj.get("subject", ""),
                    from_addr=obj.get("from", ""),
                    to_addrs=obj.get("to", []),
                    cc_addrs=obj.get("cc", []),
                    received_at=obj.get("received_at", ""),
                    body_text=obj.get("body_text", ""),
                    ground_truth=obj.get("ground_truth", {}),
                )
            )
    return samples


def is_relative_time(text: str) -> bool:
    lowered = text.lower()
    triggers = ["next monday", "next tuesday", "tomorrow", "eow", "eod", "by eow", "next week"]
    return any(t in lowered for t in triggers)


def has_multi_actions(text: str) -> bool:
    # cheap heuristic: multiple sentences with verbs like "send", "schedule", "review"
    verbs = ["send", "schedule", "review", "update", "confirm", "share", "draft"]
    hit = 0
    for v in verbs:
        if v in text.lower():
            hit += 1
    return hit >= 2


def is_overlong(text: str, threshold_chars: int) -> bool:
    return len(text) >= threshold_chars


def summary_has_due(summary_json: Dict) -> bool:
    return bool(summary_json.get("deadline"))


def _extract_sender_name(from_addr: str) -> str:
    if not from_addr:
        return ""
    # Try "Name <email@x.com>" format
    if "<" in from_addr and ">" in from_addr:
        name = from_addr.split("<", 1)[0].strip().strip('"')
        if name:
            return name.title()
        from_addr = from_addr.split("<", 1)[1].split(">", 1)[0]
    # Fallback: local part
    local = from_addr.split("@")[0]
    # Replace dots/underscores with space and title-case
    return " ".join(part for part in local.replace(".", " ").replace("_", " ").split()).title()


def _normalize_action(current_action: str, email_text: str) -> str:
    """
    Normalize action to intent labels: "request", "remind", "notify", "inform"
    This maps task verbs to the intent labels used in ground truth.
    """
    if not current_action:
        return ""
    
    action_lower = current_action.lower().strip()
    text = f"{action_lower} {email_text or ''}".lower()
    
    # First, check if it's already an intent label
    if action_lower in ["request", "remind", "notify", "inform"]:
        return action_lower
    
    # Check for composite labels (e.g., "request action", "notify approval")
    if action_lower.startswith("request "):
        return "request"
    if action_lower.startswith("notify "):
        return "notify"
    if action_lower.startswith("remind "):
        return "remind"
    if action_lower.startswith("inform "):
        return "notify"  # "inform" maps to "notify"
    
    # Map task verbs to intent labels
    # Task verbs that map to "request"
    request_verbs = [
        "send", "submit", "share", "forward", "provide", "deliver", "attach", 
        "circulate", "distribute", "transmit", "review", "check", "look over", 
        "double-check", "verify", "audit", "go through", "examine", "inspect", 
        "assess", "evaluate", "approve", "approval", "sign off", "signoff", 
        "sign-off", "ok it", "okay", "endorse", "authorize", "schedule", 
        "arrange", "set up", "book", "invite", "organize", "plan", "coordinate", 
        "setup", "arrange for", "prepare", "draft", "create", "write", "compile", 
        "develop", "generate", "update", "revise", "refresh", "edit", "modify", 
        "amend", "correct", "confirm", "acknowledge", "verify receipt", "respond yes", 
        "rsvp", "validate", "affirm", "request", "ask", "need", "require", 
        "solicit", "petition", "troubleshoot", "fix", "resolve", "debug", 
        "investigate", "escalate", "process", "handle", "manage", "deal with", 
        "address", "complete", "finish", "finalize"
    ]
    
    # Task verbs that map to "remind"
    remind_verbs = ["remind", "prepare"]  # "prepare" can be a reminder in context
    
    # Task verbs that map to "notify"
    notify_verbs = ["notify", "alert", "inform", "announce", "report"]
    
    # Check if action matches any request verb
    for verb in request_verbs:
        if verb in action_lower or action_lower == verb:
            return "request"
    
    # Check if action matches any remind verb
    for verb in remind_verbs:
        if verb in action_lower or action_lower == verb:
            # Check context: if email text suggests it's a reminder, use "remind"
            if "remind" in text or "remember" in text or "don't forget" in text:
                return "remind"
            # Otherwise, "prepare" usually maps to "request"
            if verb == "prepare":
                return "request"
            return "remind"
    
    # Check if action matches any notify verb
    for verb in notify_verbs:
        if verb in action_lower or action_lower == verb:
            return "notify"
    
    # Default: return as-is (might be a phrase we don't recognize)
    return action_lower


def postprocess_summary(summary_json: Dict, email: EmailSample) -> Dict:
    actor = (summary_json or {}).get("actor")
    # Normalize actor: avoid "you/we/our team/null" or email addresses
    if not actor or str(actor).strip().lower() in {"you", "recipient", "assignee", "we", "our team"} or isinstance(actor, list):
        inferred = _extract_sender_name(email.from_addr)
        if inferred:
            summary_json["actor"] = inferred
    else:
        actor_str = str(actor).strip()
        # Check if actor is an email address (contains @)
        if "@" in actor_str:
            # Extract name from email address
            inferred = _extract_sender_name(actor_str)
            if inferred:
                summary_json["actor"] = inferred
            else:
                # Fallback: extract from original from_addr
                inferred = _extract_sender_name(email.from_addr)
                if inferred:
                    summary_json["actor"] = inferred
        else:
            # Normalize actor format: ensure consistent capitalization and remove suffixes
            if actor_str:
                # Remove common suffixes that don't add meaning
                actor_str = actor_str.replace(" Team", "").replace(" Department", "").replace(" Group", "").strip()
                # Normalize to Title Case
                summary_json["actor"] = actor_str.title()
    # Normalize action to canonical verb phrase
    action = (summary_json or {}).get("action")
    summary_json["action"] = _normalize_action(str(action or ""), email.body_text)
    return summary_json


def run_pipeline_for_email(
    email: EmailSample,
    summarizer_fast: str,
    extractor_fast: str,
    extractor_fallback_time: str,
    summarizer_fallback_struct: str,
    overlong_threshold: int,
) -> Tuple[ModelOutput, float]:
    start = time.time()

    # Prepare prompt text with received_at to help resolve relative time
    prompt_text = f"Received at (UTC): {email.received_at}\n\nEmail:\n{email.body_text}"

    # Fast-path summarizer
    sum_fast = get_model_client(summarizer_fast)
    raw_sum, summary_json, conf_sum = sum_fast.summarize(prompt_text)
    summary_json = postprocess_summary(summary_json or {}, email)

    # Fallback conditions on summarizer side (structure / due-date missing)
    fallback_needed = False
    if is_relative_time(email.body_text):
        fallback_needed = True
    if has_multi_actions(email.body_text):
        fallback_needed = True
    if is_overlong(email.body_text, overlong_threshold):
        fallback_needed = True
    if conf_sum is not None and conf_sum < 0.45:
        fallback_needed = True
    if not summary_has_due(summary_json):
        fallback_needed = True

    if fallback_needed:
        sum_fb = get_model_client(summarizer_fallback_struct)
        raw_sum, summary_json, conf_sum = sum_fb.summarize(prompt_text)
        summary_json = postprocess_summary(summary_json or {}, email)

    # Extractor: fast first
    ext_fast = get_model_client(extractor_fast)
    raw_tasks, tasks_json, conf_tasks = ext_fast.extract(prompt_text)

    # If relative time or due-date unresolved → time fallback extractor
    if is_relative_time(email.body_text) or not any(t.get("deadline") for t in tasks_json.get("tasks", [])):
        ext_fb = get_model_client(extractor_fallback_time)
        raw_tasks, tasks_json, conf_tasks = ext_fb.extract(prompt_text)

    end = time.time()
    elapsed_ms = (end - start) * 1000.0

    json_ok = isinstance(summary_json, dict) and isinstance(tasks_json, dict)

    return (
        ModelOutput(
            summary_json=summary_json,
            tasks_json=tasks_json.get("tasks", []),
            raw_summary_text=raw_sum,
            raw_tasks_text=raw_tasks,
            json_compliant=json_ok,
            confidence=min(conf for conf in [conf_sum, conf_tasks] if conf is not None) if any(
                c is not None for c in [conf_sum, conf_tasks]
            ) else None,
        ),
        elapsed_ms,
    )


