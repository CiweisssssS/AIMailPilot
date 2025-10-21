"""
Task Extractor Service - Extract tasks using GPT-4o-mini
"""

import json
from typing import List, Dict, Any
from app.core.llm import llm_provider
from app.models.schemas import Task
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
        
        # Convert to expected format with source_span
        formatted_tasks = []
        for task in tasks:
            formatted_tasks.append({
                "title": task.get('title', 'Untitled task'),
                "owner": task.get('owner', 'team'),
                "due_iso": task.get('due'),
                "source_span": {"start": 0, "end": len(text)}  # Placeholder span
            })
        
        logger.info(f"GPT-4o-mini extracted {len(formatted_tasks)} tasks")
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
        
        # Convert to Task objects
        tasks = []
        for task_dict in tasks_data:
            try:
                task = Task(
                    title=task_dict.get('title', 'Untitled'),
                    owner=task_dict.get('owner', 'team'),
                    due=task_dict.get('due'),
                    source_message_id=task_dict.get('source_message_id', 
                                                   messages[0].get('id', 'unknown')),
                    type=task_dict.get('type', 'action')
                )
                tasks.append(task)
            except Exception as e:
                logger.error(f"Failed to create Task object: {e}")
                continue
        
        logger.info(f"Extracted {len(tasks)} Task objects")
        return tasks[:10]
        
    except Exception as e:
        logger.error(f"Task extraction failed: {e}")
        return []
