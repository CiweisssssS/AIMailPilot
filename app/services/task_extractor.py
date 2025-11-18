"""
Task extraction and processing service
Extracts tasks from emails and creates task records with state machine
"""
import logging
from typing import List, Dict, Optional
from app.services.extractor import extract_tasks
from app.services.prioritizer import calculate_priority
from app.db.supabase_client import upsert_task, get_email_by_id

logger = logging.getLogger(__name__)


async def process_email_for_tasks(user_email: str, message_id: str) -> int:
    """
    Process an email to extract tasks and create task records
    Returns: number of tasks created
    """
    try:
        # Get email from DB
        email = await get_email_by_id(user_email, message_id)
        if not email:
            logger.warning(f"Email {message_id} not found in DB")
            return 0
        
        # Skip if already processed
        if email.get("processed"):
            logger.debug(f"Email {message_id} already processed")
            return 0
        
        # Build message dict for task extraction
        body_text = email.get("normalized_text") or email.get("snippet", "")
        body_html = email.get("normalized_html")
        
        msg_dict = {
            "id": message_id,
            "subject": email.get("subject", ""),
            "clean_body": body_html or body_text,
            "body": body_html or body_text,
            "from_": email.get("from_email", ""),
            "to": [],
            "date": email.get("date_iso", "")
        }
        
        # Extract tasks
        tasks = await extract_tasks([msg_dict])
        
        # Calculate priority
        priority_result = await calculate_priority([msg_dict], tasks, [])
        priority_label = priority_result.label
        
        # Map priority label to task priority
        if "P1" in priority_label:
            task_priority = "urgent"
        elif "P2" in priority_label:
            task_priority = "todo"
        else:
            task_priority = "fyi"
        
        # Create task records (idempotent)
        created_count = 0
        for task in tasks:
            try:
                # Use task title as normalized_title and rule_key
                task_title = task.title if hasattr(task, "title") else str(task)
                rule_key = f"extracted_{message_id}_{created_count}"
                
                await upsert_task(
                    user_email=user_email,
                    message_id=message_id,
                    priority=task_priority,
                    rule_key=rule_key,
                    normalized_title=task_title
                )
                created_count += 1
            except Exception as e:
                logger.warning(f"Failed to create task for {message_id}: {e}")
        
        # Mark email as processed
        from app.db.supabase_client import get_supabase_client, _run_in_thread
        client = get_supabase_client()
        
        def _mark_processed():
            return client.table("emails")\
                .update({"processed": True})\
                .eq("message_id", message_id)\
                .eq("user_email", user_email)\
                .execute()
        
        await _run_in_thread(_mark_processed)
        
        logger.info(f"Processed email {message_id}, created {created_count} tasks")
        return created_count
    
    except Exception as e:
        logger.error(f"Failed to process email {message_id} for tasks: {e}")
        return 0


async def process_unprocessed_emails(user_email: str, limit: int = 50) -> int:
    """
    Process unprocessed emails in batch
    Returns: total tasks created
    """
    try:
        from app.db.supabase_client import get_supabase_client, _run_in_thread
        client = get_supabase_client()
        
        def _get_unprocessed():
            response = client.table("emails")\
                .select("message_id")\
                .eq("user_email", user_email)\
                .eq("processed", False)\
                .limit(limit)\
                .execute()
            return [row["message_id"] for row in response.data]
        
        unprocessed_ids = await _run_in_thread(_get_unprocessed)
        
        total_tasks = 0
        for message_id in unprocessed_ids:
            tasks_created = await process_email_for_tasks(user_email, message_id)
            total_tasks += tasks_created
        
        logger.info(f"Processed {len(unprocessed_ids)} emails, created {total_tasks} tasks")
        return total_tasks
    
    except Exception as e:
        logger.error(f"Failed to process unprocessed emails: {e}")
        return 0

