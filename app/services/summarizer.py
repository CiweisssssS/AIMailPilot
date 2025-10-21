"""
Summarizer Service - Generate summaries using GPT-4o-mini
"""

import json
import re
from typing import List, Dict, Any
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


async def summarize_text(subject: str, text: str, sender: str = "Unknown", max_length: int = 80) -> Dict[str, Any]:
    """
    Summarize text using GPT-4o-mini with strict word-based control
    
    Args:
        subject: Email subject line
        text: Cleaned email text (signatures/quotes removed)
        sender: Email sender (for extracting actor name)
        max_length: Deprecated - using SUMMARY_MAX_WORDS from env
    
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
            max_words=max_words
        )
        
        if summary and len(summary.strip()) > 5:
            word_count = count_words(summary)
            logger.info(f"Summary generated: {word_count} words - '{summary}'")
            
            return {
                "summary": summary,
                "confidence": 0.95
            }
    except Exception as e:
        logger.error(f"GPT-4o-mini summarization failed: {e}")
    
    # Fallback: return subject or truncated text
    fallback_summary = subject if subject else email_body[:200]
    return {
        "summary": fallback_summary,
        "confidence": 0.3
    }


async def _generate_summary_with_retry(subject: str, sender_name: str, body: str, max_words: int, retry_count: int = 0) -> str:
    """
    Generate summary with retry logic for word limit and action verb validation
    
    Args:
        subject: Email subject
        sender_name: Sender's first name
        body: Email body
        max_words: Maximum word count
        retry_count: Current retry attempt (max 1)
    
    Returns:
        Summary string
    """
    system_prompt = get_summary_system_prompt(max_words)
    
    # Build user message
    user_message = f"""Subject: {subject}
From: {sender_name}
Body (trimmed): {body}

Return JSON only."""
    
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
        
        # Ensure period at end
        if summary and not summary.endswith('.'):
            summary += '.'
        
        # Validate word count and action verb
        word_count = count_words(summary)
        has_verb = has_action_verb(summary)
        
        # If validation fails and we haven't retried yet, try again with stricter instruction
        if (word_count > max_words or not has_verb) and retry_count == 0:
            logger.warning(f"Summary validation failed: {word_count} words (max {max_words}), has_verb={has_verb}. Retrying...")
            
            # Retry with stricter prompt
            retry_message = f"""Shorten to <= {max_words} words. Keep actor + action + deadline intact. Return JSON only."""
            
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
                # Create minimal compliant summary using template
                if "deadline" in body.lower() or "eod" in body.lower() or "asap" in body.lower():
                    summary = f"{sender_name} requests action by deadline."
                elif any(word in body.lower() for word in ["review", "feedback", "check", "look"]):
                    summary = f"{sender_name} asks you to review something."
                elif "meeting" in body.lower() or "schedule" in body.lower():
                    summary = f"{sender_name} wants to schedule a meeting."
                else:
                    summary = f"{sender_name} shares information for your review."
        
        # Ensure summary starts with sender name (code-level guard)
        if summary and not summary.lower().startswith(sender_name.lower()):
            logger.warning(f"Summary doesn't start with sender name '{sender_name}'. Prepending...")
            # Check if it starts with "The" or "They" - replace with sender name
            if summary.lower().startswith(('the ', 'they ')):
                summary = sender_name + summary[summary.index(' '):]
            else:
                # Prepend sender name
                summary = f"{sender_name} {summary[0].lower()}{summary[1:]}"
        
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
    Summarize a thread of messages using GPT-4o-mini
    
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
                sender=msg.get('from_', 'Unknown')
            )
            return result['summary']
        
        # For multiple messages, use map-reduce
        summary = await llm_provider.summarize_map_reduce(messages)
        return summary
    except Exception as e:
        logger.error(f"Thread summarization failed: {e}")
        # Fallback: return subject of first message
        return messages[0].get('subject', 'Email thread')
