"""
Task Extractor Service - Extract tasks using GPT-4o-mini
"""

import json
from typing import List, Dict, Any
from datetime import datetime
from zoneinfo import ZoneInfo
from app.core.llm import llm_provider
from app.models.schemas import Task
from app.utils.deadline_utils import normalize_deadline
import logging

logger = logging.getLogger(__name__)


async def extract_tasks_from_text(text: str, subject: str = "") -> Dict[str, Any]:
    """
    Extract tasks using GPT-4o-mini
    
    Input: { text: string, subject?: string }
    Output: { tasks: [{ title, owner, due_iso, source_span }] }
    """
    if not text:
        return {"tasks": []}
    
    # Prepare content
    combined_text = f"Subject: {subject}\n\n{text}" if subject else text
    
    # Limit text length
    if len(combined_text) > 3000:
        combined_text = combined_text[:3000] + "... [truncated]"
    
    try:
        # Call LLM extractor (returns list of dicts)
        tasks = await llm_provider.extract_tasks([{
            'id': 'msg1',
            'subject': subject,
            'clean_body': text,
            'from_': 'Unknown'
        }])
        
        # Convert to expected format with source_span and normalize deadlines
        formatted_tasks = []
        ref_datetime = datetime.now(ZoneInfo("UTC"))
        
        for task in tasks:
            # Get raw deadline from LLM
            raw_due = task.get('due')
            
            # Normalize deadline using strict rules
            if raw_due:
                # If LLM returns ISO format, use it as deadline text to normalize
                # Otherwise use raw text
                normalized_due = normalize_deadline(str(raw_due), ref_datetime, "UTC")
            else:
                normalized_due = "TBD"
            
            formatted_tasks.append({
                "title": task.get('title', 'Untitled task'),
                "owner": task.get('owner', 'team'),
                "due_iso": normalized_due,  # Now in "Mon DD, YYYY, HH:mm" or "TBD" format
                "source_span": {"start": 0, "end": len(text)}  # Placeholder span
            })
        
        logger.info(f"GPT-4o-mini extracted {len(formatted_tasks)} tasks with normalized deadlines")
        return {"tasks": formatted_tasks[:10]}
        
    except Exception as e:
        logger.error(f"GPT-4o-mini task extraction failed: {e}")
        return {"tasks": []}


async def extract_tasks(messages: List[Dict[str, Any]]) -> List[Task]:
    """
    Legacy function for backward compatibility
    Extracts tasks from message list and returns Task objects
    """
    if not messages:
        return []
    
    try:
        # Use LLM provider's extract_tasks
        tasks_data = await llm_provider.extract_tasks(messages)
        
        # Get reference datetime from email date or use current time as fallback
        ref_datetime = datetime.now(ZoneInfo("UTC"))
        if messages and messages[0].get('date'):
            try:
                from dateutil import parser as date_parser
                email_date = date_parser.parse(messages[0]['date'])
                if email_date.tzinfo is None:
                    email_date = email_date.replace(tzinfo=ZoneInfo("UTC"))
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
                logger.info(f"Processing task: {task_dict.get('title', 'Unknown')}, raw_due: {raw_due}")
                
                # Normalize deadline using strict rules
                if raw_due:
                    normalized_due = normalize_deadline(str(raw_due), ref_datetime, "UTC")
                    logger.info(f"Normalized deadline: '{raw_due}' -> '{normalized_due}'")
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
