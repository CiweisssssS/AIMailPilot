"""
Task Extractor Service - Extract tasks using GPT-4o-mini (default and fallback for complex time)
"""

import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from zoneinfo import ZoneInfo
from app.core.llm import llm_provider
from app.models.schemas import Task
from app.utils.deadline_utils import normalize_deadline
import logging
import re

logger = logging.getLogger(__name__)

GENERIC_OWNER_TOKENS = {"team", "unknown", "you", "everyone", "all", "folks", "self", "sender", "myself"}

OWNER_PATTERNS = [
    r"\b([A-Z][a-z]+)\s*,\s*(?:please|can you|could you|kindly|need(?:\s+you)?|will you)",
    r"\b([A-Z][a-z]+)\s+needs?\s+to\b",
    r"\b([A-Z][a-z]+)\s+must\b",
    r"\b([A-Z][a-z]+)\s+should\b",
    r"\b([A-Z][a-z]+\s+(?:Department|Team))\s+(?:must|needs|should)\b",
]


def _infer_owner(current_owner: Optional[str], text: str) -> str:
    """
    Attempt to infer a more specific owner from the email text when the LLM returns a generic/default owner.
    """
    owner = (current_owner or "").strip()
    if owner and owner.lower() not in GENERIC_OWNER_TOKENS:
        return owner

    for pattern in OWNER_PATTERNS:
        match = re.search(pattern, text)
        if match:
            candidate = match.group(1).strip()
            if candidate and candidate.lower() not in GENERIC_OWNER_TOKENS:
                return candidate

    return owner or "team"


def _estimate_source_span(text: str, title: str) -> Dict[str, int]:
    """
    Provide a rough span for the extracted task title to help downstream features highlight the origin.
    """
    if not text or not title:
        return {"start": 0, "end": min(len(text), 1)}

    snippet = title[:40]
    idx = text.lower().find(snippet.lower())
    if idx == -1:
        idx = 0
    end = min(len(text), idx + max(len(snippet), 1))
    return {"start": idx, "end": end}


def _prepare_text(subject: str, body: str, limit: int = 3000) -> str:
    combined_text = f"Subject: {subject}\n\n{body}" if subject else body
    if len(combined_text) > limit:
        return combined_text[:limit] + "... [truncated]"
    return combined_text


def _has_complex_time_expression(text: str) -> bool:
    """
    Detect complex time expressions that may require a more powerful model.
    Returns True if the text contains complex time expressions that might need GPT-4o fallback.
    """
    text_lower = text.lower()
    
    # Complex time patterns that may need better model
    complex_patterns = [
        r'\b(?:next|this)\s+(?:week|month|quarter|year)\b',  # "next week", "this month"
        r'\b(?:early|mid|late)\s+(?:next\s+)?(?:week|month|quarter|year)\b',  # "early next week"
        r'\b(?:in\s+)?\d+\s+(?:weeks?|months?|days?)\s+(?:from\s+now|later)\b',  # "in 2 weeks", "3 months later"
        r'\b(?:end\s+of|beginning\s+of|middle\s+of)\s+(?:next\s+)?(?:week|month|quarter)\b',  # "end of next week"
        r'\b(?:first|second|third|fourth|last)\s+(?:week|month)\s+of\s+\w+\b',  # "first week of October"
        r'\b(?:before|after)\s+(?:the\s+)?(?:end|start|beginning)\s+of\b',  # "before the end of"
        r'\b(?:by|until|before)\s+(?:the\s+)?(?:end|start)\s+of\s+(?:next\s+)?(?:week|month|quarter)\b',  # "by the end of next week"
        r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\s+(?:at\s+)?\d{1,2}:\d{2}',  # "10/15/2024 at 3:30pm"
        r'\b(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\s+(?:morning|afternoon|evening|night)\b',  # "Friday morning"
        r'\b(?:next|this|coming)\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\s+(?:morning|afternoon|evening|night)?\b',  # "next Friday evening"
    ]
    
    for pattern in complex_patterns:
        if re.search(pattern, text_lower):
            logger.debug(f"Complex time expression detected: pattern '{pattern}' matched in text")
            return True
    
    return False


async def extract_tasks_from_text(text: str, subject: str = "", sent_date: Optional[str] = None) -> Dict[str, Any]:
    """
    Extract tasks using GPT-4o-mini (default and fallback for complex time expressions)
    
    Input: { text: string, subject?: string, sent_date?: string }
    Output: { tasks: [{ title, owner, due_iso, source_span }] }
    """
    if not text:
        return {"tasks": []}
    
    # Prepare content
    text_for_llm = _prepare_text(subject, text)
    
    # Parse sent_date for year inference
    email_sent_date = None
    if sent_date:
        try:
            from dateutil import parser as date_parser
            email_sent_date = date_parser.parse(sent_date)
            if email_sent_date.tzinfo is None:
                email_sent_date = email_sent_date.replace(tzinfo=ZoneInfo("UTC"))
        except Exception as e:
            logger.warning(f"Failed to parse sent_date '{sent_date}': {e}")
    
    try:
        # Check if text contains complex time expressions
        use_fallback = _has_complex_time_expression(text_for_llm)
        if use_fallback:
            logger.info("Complex time expression detected, using fallback model (GPT-4o-mini)")
        else:
            logger.info("Using default extractor model (GPT-4o-mini)")
        
        # Call LLM extractor (returns list of dicts)
        tasks = await llm_provider.extract_tasks([{
            'id': 'msg1',
            'subject': subject,
            'clean_body': text_for_llm,
            'body': text_for_llm,
            'from_': 'Unknown',
            'date': sent_date
        }], use_fallback=use_fallback)
        
        # Convert to expected format with source_span and normalize deadlines
        formatted_tasks = []
        ref_datetime = datetime.now(ZoneInfo("UTC"))
        
        for task in tasks:
            # Get raw deadline from LLM
            raw_due = task.get('due')
            
            # Normalize deadline using strict rules with email sent date
            if raw_due:
                # If LLM returns ISO format, use it as deadline text to normalize
                # Otherwise use raw text
                normalized_due = normalize_deadline(str(raw_due), ref_datetime, "UTC", sent_date=email_sent_date)
            else:
                normalized_due = "TBD"
            
            inferred_owner = _infer_owner(task.get('owner'), text_for_llm)
            source_span = _estimate_source_span(text_for_llm, task.get('title', ''))

            formatted_tasks.append({
                "title": task.get('title', 'Untitled task'),
                "owner": inferred_owner,
                "due_iso": normalized_due,  # Now in "Mon DD, YYYY, HH:mm" or "TBD" format
                "source_span": source_span
            })
        
        model_used = "GPT-4o-mini"
        logger.info(f"{model_used} extracted {len(formatted_tasks)} tasks with normalized deadlines")
        return {"tasks": formatted_tasks[:10]}
        
    except Exception as e:
        logger.error(f"Task extraction failed: {e}")
        return {"tasks": []}


async def extract_tasks(messages: List[Dict[str, Any]]) -> List[Task]:
    """
    Legacy function for backward compatibility
    Extracts tasks from message list and returns Task objects
    """
    if not messages:
        return []
    
    try:
        primary_subject = messages[0].get('subject', '') if messages else ''
        primary_body = messages[0].get('clean_body', messages[0].get('body', '')) if messages else ''
        primary_text = _prepare_text(primary_subject, primary_body)

        # Check if text contains complex time expressions
        use_fallback = _has_complex_time_expression(primary_text)
        if use_fallback:
            logger.info("Complex time expression detected, using fallback model (GPT-4o-mini)")
        else:
            logger.info("Using default extractor model (GPT-4o-mini)")

        # Use LLM provider's extract_tasks
        tasks_data = await llm_provider.extract_tasks(messages, use_fallback=use_fallback)
        
        # Get reference datetime from email date or use current time as fallback
        ref_datetime = datetime.now(ZoneInfo("UTC"))
        email_sent_date = None
        if messages and messages[0].get('date'):
            try:
                from dateutil import parser as date_parser
                email_date = date_parser.parse(messages[0]['date'])
                if email_date.tzinfo is None:
                    email_date = email_date.replace(tzinfo=ZoneInfo("UTC"))
                email_sent_date = email_date
                ref_datetime = email_date
                logger.info(f"Using email date as reference: {ref_datetime}")
            except Exception as e:
                logger.warning(f"Failed to parse email date, using current time: {e}")
                ref_datetime = datetime.now(ZoneInfo("UTC"))
        
        # Convert to Task objects with normalized deadlines
        tasks = []
        for task_dict in tasks_data:
            try:
                # Get raw deadline from LLM
                raw_due = task_dict.get('due')
                
                # Normalize deadline using strict rules with email sent date
                if raw_due:
                    logger.info(f"Task '{task_dict.get('title', 'Unknown')}': raw_due='{raw_due}'")
                    normalized_due = normalize_deadline(str(raw_due), ref_datetime, "UTC", sent_date=email_sent_date)
                    logger.info(f"  Normalized: '{raw_due}' -> '{normalized_due}'")
                else:
                    normalized_due = "TBD"
                    logger.info(f"No deadline provided, using TBD")
                
                # Ensure all required fields have valid defaults
                task = Task(
                    title=task_dict.get('title') or 'Untitled',
                    owner=_infer_owner(task_dict.get('owner'), primary_text),  # Ensure owner is never None
                    due=normalized_due,  # Use normalized deadline
                    source_message_id=task_dict.get('source_message_id') or (messages[0].get('id', 'unknown') if messages else 'unknown'),
                    type=task_dict.get('type') or 'action'
                )
                logger.info(f"Created task with due: {task.due}")
                tasks.append(task)
            except Exception as e:
                logger.error(f"Failed to create Task object: {e}")
                continue
        
        logger.info(f"Extracted {len(tasks)} Task objects with normalized deadlines")
        return tasks[:10]
        
    except Exception as e:
        logger.error(f"Task extraction failed: {e}")
        return []
