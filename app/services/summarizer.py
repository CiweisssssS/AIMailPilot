"""
Summarizer Service - Generate summaries using Claude 3.5 Haiku (default)
"""

import json
import re
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dateutil import parser as date_parser
from app.core.llm import llm_provider
from app.core.config import settings
from app.core.prompts import get_summary_system_prompt, SUMMARY_FEW_SHOT_EXAMPLES
import logging

logger = logging.getLogger(__name__)


def count_words(text: str) -> int:
    """Count words in text (handles punctuation correctly)"""
    return len(text.split())


def has_action_verb(text: str) -> bool:
    """Check if summary contains an action verb"""
    action_verbs = [
        'needs', 'asks', 'requests', 'shares', 'sends', 'invites', 'reminds',
        'wants', 'requires', 'suggests', 'proposes', 'recommends', 'offers',
        'seeks', 'provides', 'announces', 'reports', 'updates', 'notifies',
        'review', 'submit', 'complete', 'send', 'schedule', 'approve'
    ]
    text_lower = text.lower()
    return any(verb in text_lower for verb in action_verbs)


def extract_sender_name(sender_email: str) -> str:
    """Extract first name from email sender"""
    if not sender_email:
        return "They"
    
    # Try to extract name from "Name <email>" format
    match = re.match(r'^([^<]+)', sender_email)
    if match:
        name = match.group(1).strip()
        # Get first name
        first_name = name.split()[0] if name else "They"
        return first_name
    
    # Fallback to email username
    email_match = re.match(r'^([^@]+)', sender_email)
    if email_match:
        username = email_match.group(1)
        # Capitalize first letter
        return username.capitalize()
    
    return "They"


def build_summary(sender_name: str, actor: str, action: str, obj: str, deadline: Optional[str]) -> str:
    """Compose a deterministic summary sentence from structured pieces."""
    actor = actor.strip() if actor else sender_name
    action = action.strip() if action else "shares"
    obj = obj.strip() if obj else "an update"
    sentence = f"{sender_name} {action}"
    if obj:
        sentence += f" {obj}"
    if deadline:
        clean_deadline = deadline.strip().strip(".")
        if clean_deadline:
            sentence += f" by {clean_deadline}"
    if not sentence.endswith("."):
        sentence += "."
    return sentence


def enforce_sender_prefix(summary: str, sender_name: str) -> str:
    """Ensure generated summary starts with the sender's name."""
    summary = summary.strip()
    if not summary:
        return f"{sender_name} shares an update."
    if summary.lower().startswith(sender_name.lower()):
        return summary
    return f"{sender_name} {summary[0].lower()}{summary[1:]}"


def _normalize_deadline(deadline: Any, received_at: str = None) -> Optional[str]:
    """
    Normalize deadline to ISO format (YYYY-MM-DD) or null.
    
    Args:
        deadline: Raw deadline value from LLM (could be string, null, or relative time)
        received_at: Email received timestamp (ISO format) for relative time calculation
    
    Returns:
        Normalized deadline in ISO format (YYYY-MM-DD) or None
    """
    if deadline is None or deadline == "" or str(deadline).lower().strip() in ("null", "none", ""):
        return None
    
    deadline_str = str(deadline).strip()
    
    # If already in ISO format (YYYY-MM-DD), return as-is
    if re.match(r'^\d{4}-\d{2}-\d{2}$', deadline_str):
        return deadline_str
    
    # If contains time (YYYY-MM-DDTHH:MM:SS), extract date part
    if "T" in deadline_str:
        deadline_str = deadline_str.split("T", 1)[0]
        if re.match(r'^\d{4}-\d{2}-\d{2}$', deadline_str):
            return deadline_str
    
    # Try to parse relative time expressions if received_at is provided
    if received_at:
        try:
            # Parse received_at as reference
            ref_date = date_parser.parse(received_at)
            if ref_date.tzinfo:
                ref_date = ref_date.replace(tzinfo=None)
            
            deadline_lower = deadline_str.lower()
            
            # Handle common relative time expressions
            if deadline_lower in ["eod", "end of day", "cob", "end of today"]:
                return ref_date.strftime("%Y-%m-%d")
            elif deadline_lower in ["tomorrow", "tomorrow morning", "tomorrow afternoon", "tomorrow evening"] or "tomorrow" in deadline_lower:
                next_day = ref_date + timedelta(days=1)
                return next_day.strftime("%Y-%m-%d")
            elif deadline_lower in ["eow", "end of week", "by eow", "end of this week"] or ("eow" in deadline_lower and "next" not in deadline_lower):
                # This week's Friday
                days_until_friday = (4 - ref_date.weekday()) % 7
                if days_until_friday == 0:
                    return ref_date.strftime("%Y-%m-%d")
                else:
                    friday = ref_date + timedelta(days=days_until_friday)
                    return friday.strftime("%Y-%m-%d")
            elif deadline_lower.startswith("next week"):
                days_until_next_monday = (7 - ref_date.weekday()) % 7
                if days_until_next_monday == 0:
                    days_until_next_monday = 7
                next_monday = ref_date + timedelta(days=days_until_next_monday)
                return next_monday.strftime("%Y-%m-%d")
            elif deadline_lower.startswith("next "):
                weekday_map = {
                    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
                    "friday": 4, "saturday": 5, "sunday": 6
                }
                for day_name, day_num in weekday_map.items():
                    if day_name in deadline_lower:
                        days_until = (day_num - ref_date.weekday()) % 7
                        if days_until == 0:
                            days_until = 7
                        target_date = ref_date + timedelta(days=days_until)
                        return target_date.strftime("%Y-%m-%d")
        except Exception as e:
            logger.warning(f"Failed to parse relative deadline '{deadline_str}' with received_at '{received_at}': {e}")
    
    # If we can't parse it, try to extract date from the string
    # Look for YYYY-MM-DD pattern
    date_match = re.search(r'\d{4}-\d{2}-\d{2}', deadline_str)
    if date_match:
        return date_match.group(0)
    
    # If still can't parse, return None (invalid deadline)
    logger.warning(f"Could not normalize deadline: '{deadline_str}'")
    return None


async def summarize_text(subject: str, text: str, sender: str = "Unknown", max_length: int = 80, received_at: str = None) -> Dict[str, Any]:
    """
    Summarize text using Claude 3.5 Haiku with strict word-based control
    
    Args:
        subject: Email subject line
        text: Cleaned email text (signatures/quotes removed)
        sender: Email sender (for extracting actor name)
        max_length: Deprecated - using SUMMARY_MAX_WORDS from env
        received_at: Email received timestamp (ISO format) for deadline calculation
    
    Returns:
        { "summary": str, "confidence": float }
    """
    if not text and not subject:
        return {
            "summary": "Empty content.",
            "confidence": 0.0
        }
    
    max_words = settings.summary_max_words
    sender_name = extract_sender_name(sender)
    
    # Prepare content for summarization
    email_body = text if text else subject
    
    # Limit text length to avoid token limits
    if len(email_body) > 2500:
        email_body = email_body[:2500] + "..."
    
    try:
        summary = await _generate_summary_with_retry(
            subject=subject,
            sender_name=sender_name,
            body=email_body,
            max_words=max_words,
            received_at=received_at
        )
        
        if summary and len(summary.strip()) > 5:
            word_count = count_words(summary)
            logger.info(f"Summary generated: {word_count} words - '{summary}'")
            
            return {
                "summary": summary,
                "confidence": 0.95
            }
    except Exception as e:
        logger.error(f"Summarization failed: {e}")
    
    # Fallback: return subject or truncated text
    fallback_summary = subject if subject else email_body[:200]
    return {
        "summary": fallback_summary,
        "confidence": 0.3
    }


async def _generate_summary_with_retry(subject: str, sender_name: str, body: str, max_words: int, retry_count: int = 0, received_at: str = None) -> str:
    """
    Generate summary with retry logic for word limit and action verb validation
    
    Args:
        subject: Email subject
        sender_name: Sender's first name
        body: Email body
        max_words: Maximum word count
        retry_count: Current retry attempt (max 1)
        received_at: Email received timestamp (ISO format) for deadline calculation
    
    Returns:
        Summary string
    """
    system_prompt = get_summary_system_prompt(max_words)
    
    # Build user message with received_at for deadline calculation
    received_at_str = f"\nReceived at (UTC): {received_at}" if received_at else ""
    user_message = f"""Subject: {subject}
From: {sender_name}{received_at_str}
Body (trimmed): {body}

Return JSON only with keys: summary, actor, action, object, deadline."""
    
    # Prepare messages with few-shot examples
    messages = [
        {"role": "system", "content": system_prompt}
    ]
    
    # Add few-shot examples
    messages.extend(SUMMARY_FEW_SHOT_EXAMPLES)
    
    # Add user message
    messages.append({"role": "user", "content": user_message})
    
    # Call LLM with JSON mode and temperature 0.2
    response = await llm_provider.call_with_json_mode(
        messages=messages,
        temperature=0.2
    )
    
    # Parse JSON response
    try:
        if isinstance(response, str):
            response_data = json.loads(response)
        else:
            response_data = response
            
        summary = response_data.get("summary", "").strip()
        actor = (response_data.get("actor") or sender_name).strip()
        action = (response_data.get("action") or "").strip()
        obj = (response_data.get("object") or "").strip()
        deadline_raw = response_data.get("deadline")
        
        # Normalize deadline: convert to ISO format (YYYY-MM-DD) or null
        deadline = _normalize_deadline(deadline_raw, received_at)

        if not summary:
            summary = build_summary(sender_name, actor, action, obj, deadline)

        summary = enforce_sender_prefix(summary, sender_name)
        if obj and obj.lower() not in summary.lower():
            summary = build_summary(sender_name, actor, action, obj, deadline)

        if deadline and deadline.lower() not in summary.lower():
            summary = build_summary(sender_name, actor, action, obj, deadline)

        if summary and not summary.endswith('.'):
            summary += '.'

        word_count = count_words(summary)
        has_verb = has_action_verb(summary)
        
        # If validation fails and we haven't retried yet, try again with stricter instruction
        if (word_count > max_words or not has_verb) and retry_count == 0:
            logger.warning(f"Summary validation failed: {word_count} words (max {max_words}), has_verb={has_verb}. Retrying...")
            
            # Retry with stricter prompt
            retry_message = f"""Shorten to <= {max_words} words. Keep actor + action + object + deadline intact. Return JSON only."""
            
            retry_messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": json.dumps({"summary": summary})},
                {"role": "user", "content": retry_message}
            ]
            
            retry_response = await llm_provider.call_with_json_mode(
                messages=retry_messages,
                temperature=0.2
            )
            
            if isinstance(retry_response, str):
                retry_data = json.loads(retry_response)
            else:
                retry_data = retry_response
                
            summary = retry_data.get("summary", "").strip()
            actor = (retry_data.get("actor") or actor).strip()
            action = (retry_data.get("action") or action).strip()
            obj = (retry_data.get("object") or obj).strip()
            # Use retry deadline if available, otherwise keep original
            deadline_raw = retry_data.get("deadline") if retry_data.get("deadline") is not None else deadline_raw
            deadline = _normalize_deadline(deadline_raw, received_at)

            if not summary:
                summary = build_summary(sender_name, actor, action, obj, deadline)

            summary = enforce_sender_prefix(summary, sender_name)
            if summary and not summary.endswith('.'):
                summary += '.'
            
            # Re-validate after retry
            word_count = count_words(summary)
            has_verb = has_action_verb(summary)
            
            if word_count > max_words:
                logger.warning(f"Retry still exceeded word limit ({word_count} > {max_words}). Truncating...")
                # Hard truncate to max_words as last resort
                words = summary.split()
                if len(words) > max_words:
                    summary = ' '.join(words[:max_words])
                    if not summary.endswith('.'):
                        summary += '.'
                    
                    # Re-check action verb after truncation
                    has_verb = has_action_verb(summary)
            
            # If still missing action verb after retry, use template fallback
            if not has_verb:
                logger.warning("Summary still missing action verb after retry. Using template fallback.")
                template_action = action or "shares"
                template_object = obj or "an update"
                template_deadline = deadline
                if "deadline" in body.lower() or "eod" in body.lower() or "asap" in body.lower():
                    template_action = "requests action"
                    template_deadline = template_deadline or "the stated deadline"
                elif any(word in body.lower() for word in ["review", "feedback", "check", "look"]):
                    template_action = "asks you to review"
                    template_object = template_object or "the materials"
                elif "meeting" in body.lower() or "schedule" in body.lower():
                    template_action = "wants to schedule"
                    template_object = template_object or "a meeting"
                summary = build_summary(sender_name, actor, template_action, template_object, template_deadline)
        
        summary = enforce_sender_prefix(summary, sender_name)

        return summary
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON response: {e}, response: {response}")
        # Fallback: try to extract summary from text
        if "summary" in response.lower():
            match = re.search(r'"summary"\s*:\s*"([^"]+)"', response)
            if match:
                return match.group(1).strip()
        raise


async def summarize_thread(messages: List[Dict[str, Any]]) -> str:
    """
    Summarize a thread of messages using Claude 3.5 Haiku
    
    Args:
        messages: List of message dicts with 'subject', 'body', 'clean_body'
    
    Returns:
        Summary string
    """
    if not messages:
        return "Empty thread."
    
    try:
        # For single message, use the optimized summarize_text
        if len(messages) == 1:
            msg = messages[0]
            result = await summarize_text(
                subject=msg.get('subject', ''),
                text=msg.get('clean_body', msg.get('body', '')),
                sender=msg.get('from_', 'Unknown'),
                received_at=msg.get('date', None)  # Pass email date for deadline calculation
            )
            return result['summary']
        
        # For multiple messages, use map-reduce
        summary = await llm_provider.summarize_map_reduce(messages)
        return summary
    except Exception as e:
        logger.error(f"Thread summarization failed: {e}")
        # Fallback: return subject of first message
        return messages[0].get('subject', 'Email thread')
