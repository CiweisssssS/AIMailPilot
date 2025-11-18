"""
Task Extractor Service - Extract tasks using Gemini Flash (default and fallback to GPT-4o base for complex time)
"""

import json
import re
from typing import List, Dict, Any, Optional
from datetime import datetime
from zoneinfo import ZoneInfo
from app.core.llm import llm_provider
from app.models.schemas import Task
from app.utils.deadline_utils import normalize_deadline
import logging

logger = logging.getLogger(__name__)


def _has_complex_time_expression(text: str) -> bool:
    """
    Detect complex time expressions that may require a more powerful model.
    Returns True if the text contains complex time expressions that might need GPT-4o base fallback.
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
    Extract tasks using Gemini Flash (default and fallback to GPT-4o base for complex time expressions)
    
    Input: { text: string, subject?: string, sent_date?: string }
    Output: { tasks: [{ title, owner, due_iso, source_span }] }
    """
    if not text:
        return {"tasks": []}
    
    # Prepare content
    combined_text = f"Subject: {subject}\n\n{text}" if subject else text
    
    # Limit text length
    if len(combined_text) > 3000:
        combined_text = combined_text[:3000] + "... [truncated]"
    
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
        use_fallback = _has_complex_time_expression(combined_text)
        if use_fallback:
            logger.info("Complex time expression detected, using fallback model (GPT-4o base)")
        else:
            logger.info("Using default extractor model (Gemini Flash)")
        
        # Call LLM extractor with fallback flag (returns list of dicts)
        tasks = await llm_provider.extract_tasks([{
            'id': 'msg1',
            'subject': subject,
            'clean_body': combined_text,
            'body': combined_text,
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
            
            formatted_tasks.append({
                "title": task.get('title', 'Untitled task'),
                "owner": task.get('owner', 'team'),
                "due_iso": normalized_due,  # Now in "Mon DD, YYYY, HH:mm" or "TBD" format
                "source_span": {"start": 0, "end": len(text)}  # Placeholder span
            })
        
        model_used = "GPT-4o base" if use_fallback else "Gemini Flash"
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
        # Check if text contains complex time expressions
        primary_subject = messages[0].get('subject', '') if messages else ''
        primary_body = messages[0].get('clean_body', messages[0].get('body', '')) if messages else ''
        primary_text = f"Subject: {primary_subject}\n\n{primary_body}" if primary_subject else primary_body
        
        use_fallback = _has_complex_time_expression(primary_text)
        if use_fallback:
            logger.info("Complex time expression detected, using fallback model (GPT-4o base)")
        else:
            logger.info("Using default extractor model (Gemini Flash)")
        
        # Use LLM provider's extract_tasks with fallback flag
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
                    owner=task_dict.get('owner') or 'team',  # Ensure owner is never None
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
