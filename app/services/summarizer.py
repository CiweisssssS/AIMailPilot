"""
Summarizer Service - Generate summaries using DistilBART with rule-based fallback
"""

import re
from typing import List, Dict, Any
from app.core.model_manager import model_manager
import logging

logger = logging.getLogger(__name__)

# Imperative verbs for rule-based extraction
IMPERATIVE_VERBS = [
    'finalize', 'submit', 'schedule', 'prepare', 'review', 
    'complete', 'update', 'send', 'create', 'approve', 'confirm'
]


def rule_based_summary(text: str, subject: str = "") -> str:
    """
    Rule-based fallback summarization
    Extracts key sentences containing imperative verbs
    """
    if not text:
        return subject or "Empty content."
    
    sentences = re.split(r'[.!?]\s+', text)
    key_sentences = []
    
    for sentence in sentences:
        for verb in IMPERATIVE_VERBS:
            if verb in sentence.lower():
                key_sentences.append(sentence.strip())
                break
    
    if not key_sentences:
        # No imperative verbs found, use first meaningful sentence
        first_sentence = sentences[0].strip() if sentences else ""
        if first_sentence and len(first_sentence) > 10:
            return first_sentence[:200] + ("..." if len(first_sentence) > 200 else "")
        return subject or "Discussion."
    
    summary = ' '.join(key_sentences[:2])  # Max 2 key sentences
    
    if len(summary) > 200:
        summary = summary[:197] + "..."
    
    return summary


async def summarize_text(subject: str, text: str, max_length: int = 80) -> Dict[str, Any]:
    """
    Summarize text using DistilBART with rule-based fallback
    
    Args:
        subject: Email subject line
        text: Cleaned email text (signatures/quotes removed)
        max_length: Maximum summary length in tokens
    
    Returns:
        { "summary": str, "confidence": float }
    """
    if not text:
        return {
            "summary": subject or "Empty content.",
            "confidence": 0.0
        }
    
    # Try DistilBART first
    try:
        summary = model_manager.summarize_text(text, max_length=max_length)
        
        if summary and len(summary.strip()) > 5:
            logger.info(f"DistilBART summary generated: {len(summary)} chars")
            return {
                "summary": summary,
                "confidence": 0.85  # High confidence for model output
            }
        else:
            logger.warning("DistilBART returned empty/invalid summary, using fallback")
            raise ValueError("Empty summary from model")
            
    except Exception as e:
        logger.error(f"DistilBART summarization failed: {e}, using rule-based fallback")
    
    # Fallback to rule-based
    summary = rule_based_summary(text, subject)
    return {
        "summary": summary,
        "confidence": 0.5  # Lower confidence for rule-based
    }


async def summarize_thread(messages: List[Dict[str, Any]]) -> str:
    """
    Summarize a thread of messages (legacy function for backward compatibility)
    
    Args:
        messages: List of message dicts with 'subject', 'body', 'clean_body'
    
    Returns:
        Summary string
    """
    if not messages:
        return "Empty thread."
    
    # Prefer last 1-2 messages for summarization (most recent context)
    last_msg = messages[-1]
    first_msg = messages[0] if len(messages) > 1 else last_msg
    
    subject = first_msg.get('subject', '')
    
    # Use clean_body if available, otherwise body
    text_parts = []
    for msg in [first_msg, last_msg][-2:]:  # Last 2 messages max
        body = msg.get('clean_body', msg.get('body', ''))
        if body:
            text_parts.append(body)
    
    combined_text = ' '.join(text_parts)
    
    # Call the new summarize_text function
    result = await summarize_text(subject, combined_text, max_length=80)
    
    return result['summary']
