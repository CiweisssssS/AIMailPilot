"""
Summarizer Service - Generate summaries using GPT-4o-mini
"""

from typing import List, Dict, Any
from app.core.llm import llm_provider
import logging

logger = logging.getLogger(__name__)


async def summarize_text(subject: str, text: str, max_length: int = 80) -> Dict[str, Any]:
    """
    Summarize text using GPT-4o-mini
    
    Args:
        subject: Email subject line
        text: Cleaned email text (signatures/quotes removed)
        max_length: Maximum summary length (not used with LLM, kept for API compatibility)
    
    Returns:
        { "summary": str, "confidence": float }
    """
    if not text:
        return {
            "summary": subject or "Empty content.",
            "confidence": 0.0
        }
    
    # Prepare content for summarization
    combined_text = f"Subject: {subject}\n\n{text}"
    
    # Limit text length to avoid token limits
    if len(combined_text) > 3000:
        combined_text = combined_text[:3000] + "... [truncated]"
    
    try:
        summary = await llm_provider.summarize_map_reduce([{
            'subject': subject,
            'clean_body': text,
            'from_': 'Unknown'
        }])
        
        if summary and len(summary.strip()) > 5:
            # Ensure summary is max 15 words
            words = summary.strip().split()
            if len(words) > 15:
                summary = ' '.join(words[:15]) + '...'
                logger.info(f"Summary truncated to 15 words")
            
            logger.info(f"GPT-4o-mini summary generated: {len(summary)} chars, {len(words)} words")
            return {
                "summary": summary,
                "confidence": 0.95  # High confidence for LLM output
            }
    except Exception as e:
        logger.error(f"GPT-4o-mini summarization failed: {e}")
    
    # Fallback: return subject or truncated text
    fallback_summary = subject if subject else text[:200]
    return {
        "summary": fallback_summary,
        "confidence": 0.3
    }


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
        summary = await llm_provider.summarize_map_reduce(messages)
        return summary
    except Exception as e:
        logger.error(f"Thread summarization failed: {e}")
        # Fallback: return subject of first message
        return messages[0].get('subject', 'Email thread')
