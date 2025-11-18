"""
Supabase Client Initialization
Handles connection to Supabase PostgreSQL database for data persistence.

IMPORTANT: All database operations use asyncio.to_thread to wrap synchronous
supabase-py calls, preventing FastAPI event loop blocking.
"""
import os
import asyncio
from typing import Optional, Any, Callable, TypeVar, Dict, List
from supabase import create_client, Client
import logging

logger = logging.getLogger(__name__)

# Global Supabase client instance
_supabase_client: Optional[Client] = None

T = TypeVar('T')


async def _run_in_thread(func: Callable[[], T]) -> T:
    """
    Execute a synchronous Supabase operation in a thread pool to avoid blocking
    the FastAPI event loop.
    
    Args:
        func: Synchronous function to execute
    
    Returns:
        Result of the function execution
    """
    return await asyncio.to_thread(func)


def get_supabase_client() -> Client:
    """
    Get or create Supabase client singleton.
    
    Environment variables required:
    - SUPABASE_URL: Your Supabase project URL (e.g., https://xxxxx.supabase.co)
    - SUPABASE_KEY: Your Supabase anon/public API key
    
    Returns:
        Supabase Client instance
    
    Raises:
        ValueError: If required environment variables are not set
        Exception: If client initialization fails
    """
    global _supabase_client
    
    if _supabase_client is not None:
        return _supabase_client
    
    # Get environment variables
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    
    if not supabase_url or not supabase_key:
        raise ValueError(
            "Supabase credentials not configured. "
            "Please set SUPABASE_URL and SUPABASE_KEY environment variables."
        )
    
    try:
        _supabase_client = create_client(supabase_url, supabase_key)
        logger.info(f"Supabase client initialized successfully for URL: {supabase_url}")
        return _supabase_client
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {e}")
        raise


def check_supabase_connection() -> bool:
    """
    Test Supabase connection by attempting to query a table.
    
    Returns:
        True if connection is successful, False otherwise
    """
    try:
        client = get_supabase_client()
        # Try to query flag_status table (will fail gracefully if not exists)
        response = client.table("flag_status").select("id").limit(1).execute()
        logger.info("Supabase connection test successful")
        return True
    except Exception as e:
        logger.error(f"Supabase connection test failed: {e}")
        return False


# ==========================================
# Flag Status Operations
# ==========================================

async def toggle_flag_status(user_email: str, email_id: str, is_flagged: bool) -> Any:
    """
    Toggle flag status for an email.
    Uses upsert to insert or update the flag status.
    
    Args:
        user_email: User's email address
        email_id: Gmail message ID
        is_flagged: New flag status
    
    Returns:
        dict with the upserted record
    """
    try:
        client = get_supabase_client()
        
        def _upsert():
            return client.table("flag_status").upsert({
                "user_email": user_email,
                "email_id": email_id,
                "is_flagged": is_flagged
            }, on_conflict="user_email,email_id").execute()
        
        response = await _run_in_thread(_upsert)
        
        logger.info(f"Flag status toggled for user={user_email}, email_id={email_id}, is_flagged={is_flagged}")
        return response.data[0] if response.data else {}
    except Exception as e:
        logger.error(f"Failed to toggle flag status: {e}")
        raise


async def get_flagged_emails(user_email: str) -> list[Any]:
    """
    Get all flagged emails for a user.
    
    Args:
        user_email: User's email address
    
    Returns:
        List of flagged email records
    """
    try:
        client = get_supabase_client()
        
        def _select():
            return client.table("flag_status").select("*").eq("user_email", user_email).eq("is_flagged", True).order("updated_at", desc=True).execute()
        
        response = await _run_in_thread(_select)
        
        logger.info(f"Retrieved {len(response.data)} flagged emails for user={user_email}")
        return response.data
    except Exception as e:
        logger.error(f"Failed to get flagged emails: {e}")
        raise


async def delete_flag_status(user_email: str, email_id: str) -> bool:
    """
    Delete flag status for an email.
    
    Args:
        user_email: User's email address
        email_id: Gmail message ID
    
    Returns:
        True if deleted successfully
    """
    try:
        client = get_supabase_client()
        
        def _delete():
            return client.table("flag_status").delete().eq("user_email", user_email).eq("email_id", email_id).execute()
        
        await _run_in_thread(_delete)
        
        logger.info(f"Flag status deleted for user={user_email}, email_id={email_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to delete flag status: {e}")
        raise


# ==========================================
# Deadline Override Operations
# ==========================================

async def set_deadline_override(
    user_email: str,
    email_id: str,
    task_index: int,
    original_deadline: str,
    override_deadline: str
) -> Any:
    """
    Set or update deadline override for a task.
    
    Args:
        user_email: User's email address
        email_id: Gmail message ID
        task_index: Index of the task in the email's task list
        original_deadline: Original deadline from AI analysis
        override_deadline: User's override deadline
    
    Returns:
        dict with the upserted record
    """
    try:
        client = get_supabase_client()
        
        def _upsert():
            return client.table("deadline_overrides").upsert({
                "user_email": user_email,
                "email_id": email_id,
                "task_index": task_index,
                "original_deadline": original_deadline,
                "override_deadline": override_deadline
            }, on_conflict="user_email,email_id,task_index").execute()
        
        response = await _run_in_thread(_upsert)
        
        logger.info(f"Deadline override set for user={user_email}, email_id={email_id}, task_index={task_index}")
        return response.data[0] if response.data else {}
    except Exception as e:
        logger.error(f"Failed to set deadline override: {e}")
        raise


async def get_deadline_overrides(user_email: str) -> list[Any]:
    """
    Get all deadline overrides for a user.
    
    Args:
        user_email: User's email address
    
    Returns:
        List of deadline override records
    """
    try:
        client = get_supabase_client()
        
        def _select():
            return client.table("deadline_overrides").select("*").eq("user_email", user_email).execute()
        
        response = await _run_in_thread(_select)
        
        logger.info(f"Retrieved {len(response.data)} deadline overrides for user={user_email}")
        return response.data
    except Exception as e:
        logger.error(f"Failed to get deadline overrides: {e}")
        raise


async def delete_deadline_override(user_email: str, email_id: str, task_index: int) -> bool:
    """
    Delete deadline override for a task.
    
    Args:
        user_email: User's email address
        email_id: Gmail message ID
        task_index: Index of the task in the email's task list
    
    Returns:
        True if deleted successfully
    """
    try:
        client = get_supabase_client()
        
        def _delete():
            return client.table("deadline_overrides").delete().eq("user_email", user_email).eq("email_id", email_id).eq("task_index", task_index).execute()
        
        await _run_in_thread(_delete)
        
        logger.info(f"Deadline override deleted for user={user_email}, email_id={email_id}, task_index={task_index}")
        return True
    except Exception as e:
        logger.error(f"Failed to delete deadline override: {e}")
        raise


# ==========================================
# Batch Query Operations (for batch-analyze)
# ==========================================

def get_flag_status_for_emails(user_email: str, email_ids: list[str]) -> dict[str, bool]:
    """
    Batch fetch flag status for multiple emails.
    Returns a dict mapping email_id -> is_flagged.
    
    Args:
        user_email: User's email address
        email_ids: List of Gmail message IDs
    
    Returns:
        Dict mapping email_id to is_flagged status
    """
    try:
        if not email_ids:
            return {}
        
        client = get_supabase_client()
        
        response = client.table("flag_status")\
            .select("email_id, is_flagged")\
            .eq("user_email", user_email)\
            .in_("email_id", email_ids)\
            .execute()
        
        result = {row["email_id"]: row["is_flagged"] for row in response.data}
        logger.info(f"Batch fetched flag status for {len(email_ids)} emails, found {len(result)} flags")
        return result
    except Exception as e:
        logger.error(f"Failed to batch fetch flag status: {e}")
        return {}


def get_deadline_overrides_for_emails(user_email: str, email_ids: list[str]) -> dict[tuple[str, int], str]:
    """
    Batch fetch deadline overrides for multiple emails.
    Returns a dict mapping (email_id, task_index) -> override_deadline.
    
    Args:
        user_email: User's email address
        email_ids: List of Gmail message IDs
    
    Returns:
        Dict mapping (email_id, task_index) to override_deadline
    """
    try:
        if not email_ids:
            return {}
        
        client = get_supabase_client()
        
        response = client.table("deadline_overrides")\
            .select("email_id, task_index, override_deadline")\
            .eq("user_email", user_email)\
            .in_("email_id", email_ids)\
            .execute()
        
        result = {
            (row["email_id"], row["task_index"]): row["override_deadline"]
            for row in response.data
        }
        logger.info(f"Batch fetched deadline overrides for {len(email_ids)} emails, found {len(result)} overrides")
        return result
    except Exception as e:
        logger.error(f"Failed to batch fetch deadline overrides: {e}")
        return {}


# ==========================================
# Email Operations
# ==========================================

async def upsert_email(
    user_email: str,
    parsed_message: Dict,
    history_id: Optional[str] = None,
    update_only: bool = False
) -> Any:
    """
    Upsert email record (idempotent by message_id)
    """
    try:
        client = get_supabase_client()
        
        # Parse date_iso
        date_iso = None
        if parsed_message.get("date"):
            try:
                from email.utils import parsedate_to_datetime
                dt = parsedate_to_datetime(parsed_message["date"])
                if dt:
                    date_iso = dt.isoformat()
            except Exception as e:
                logger.warning(f"Failed to parse date {parsed_message.get('date')}: {e}")
                pass
        
        email_data = {
            "message_id": parsed_message["id"],
            "thread_id": parsed_message["thread_id"],
            "user_email": user_email,
            "from_name": parsed_message.get("from_name", ""),
            "from_email": parsed_message.get("from_email", ""),
            "subject": parsed_message.get("subject", ""),
            "date_iso": date_iso,
            "snippet": parsed_message.get("snippet", ""),
            "normalized_html": parsed_message.get("body_html"),
            "normalized_text": parsed_message.get("body_text"),
            "last_history_id_at_create": history_id
        }
        
        # Note: Supabase handles "now()" automatically via DEFAULT, but we can also use None
        # For explicit timestamps, we'll let Supabase handle it via triggers
        
        def _upsert():
            return client.table("emails").upsert(
                email_data,
                on_conflict="message_id"
            ).execute()
        
        response = await _run_in_thread(_upsert)
        return response.data[0] if response.data else {}
    except Exception as e:
        logger.error(f"Failed to upsert email: {e}")
        raise


async def get_email_by_id(user_email: str, message_id: str) -> Optional[Dict]:
    """Get email by message_id"""
    try:
        client = get_supabase_client()
        
        def _get():
            response = client.table("emails")\
                .select("*")\
                .eq("message_id", message_id)\
                .eq("user_email", user_email)\
                .limit(1)\
                .execute()
            return response.data[0] if response.data else None
        
        return await _run_in_thread(_get)
    except Exception as e:
        logger.error(f"Failed to get email: {e}")
        return None


# ==========================================
# Task Operations
# ==========================================

async def upsert_task(
    user_email: str,
    message_id: str,
    priority: str,
    rule_key: str,
    normalized_title: str
) -> Any:
    """
    Upsert task (idempotent by composite key)
    """
    try:
        client = get_supabase_client()
        
        task_data = {
            "message_id": message_id,
            "user_email": user_email,
            "priority": priority,
            "rule_key": rule_key or "",
            "normalized_title": normalized_title,
            "state": "new"  # New tasks start as 'new'
        }
        
        def _upsert():
            return client.table("tasks").upsert(
                task_data,
                on_conflict="message_id,rule_key,normalized_title,user_email"
            ).execute()
        
        response = await _run_in_thread(_upsert)
        return response.data[0] if response.data else {}
    except Exception as e:
        logger.error(f"Failed to upsert task: {e}")
        raise


async def update_task_state(
    user_email: str,
    task_id: int,
    new_state: str
) -> Optional[Dict]:
    """
    Update task state (with validation)
    """
    try:
        client = get_supabase_client()
        
        # Validate state transition
        valid_states = ["new", "viewed", "saved", "done"]
        if new_state not in valid_states:
            raise ValueError(f"Invalid state: {new_state}")
        
        def _update():
            # Get current task
            response = client.table("tasks")\
                .select("*")\
                .eq("task_id", task_id)\
                .eq("user_email", user_email)\
                .limit(1)\
                .execute()
            
            if not response.data:
                return None
            
            task = response.data[0]
            current_state = task.get("state")
            
            # Validate transition (no-op if already viewed/saved/done when trying to set viewed)
            if new_state == "viewed" and current_state in ["viewed", "saved", "done"]:
                return task  # No-op
            
            # Update state
            update_response = client.table("tasks")\
                .update({"state": new_state})\
                .eq("task_id", task_id)\
                .eq("user_email", user_email)\
                .execute()
            
            return update_response.data[0] if update_response.data else None
        
        return await _run_in_thread(_update)
    except Exception as e:
        logger.error(f"Failed to update task state: {e}")
        raise


async def get_tasks(
    user_email: str,
    state: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
) -> List[Dict]:
    """
    Get tasks with optional state filter
    state: "all" | "open" | "new" | "viewed" | "saved" | "done"
    """
    try:
        client = get_supabase_client()
        
        def _get():
            query = client.table("tasks")\
                .select("*")\
                .eq("user_email", user_email)
            
            if state and state != "all":
                if state == "open":
                    # Open = new, viewed, saved (not done)
                    query = query.in_("state", ["new", "viewed", "saved"])
                else:
                    query = query.eq("state", state)
            
            query = query.order("created_at", desc=True)\
                .limit(limit)\
                .offset(offset)
            
            response = query.execute()
            return response.data
        
        return await _run_in_thread(_get)
    except Exception as e:
        logger.error(f"Failed to get tasks: {e}")
        return []


# ==========================================
# Sync Meta Operations
# ==========================================

async def get_sync_meta(user_email: str) -> Optional[Dict]:
    """Get sync metadata for user"""
    try:
        client = get_supabase_client()
        
        def _get():
            response = client.table("sync_meta")\
                .select("*")\
                .eq("user_email", user_email)\
                .limit(1)\
                .execute()
            return response.data[0] if response.data else None
        
        return await _run_in_thread(_get)
    except Exception as e:
        logger.error(f"Failed to get sync meta: {e}")
        return None


async def upsert_sync_meta(
    user_email: str,
    last_history_id: str,
    is_backfill: bool = False
) -> Any:
    """Update sync metadata"""
    try:
        client = get_supabase_client()
        
        from datetime import datetime, timezone
        sync_data = {
            "user_id": user_email,  # Use email as user_id
            "user_email": user_email,
            "last_history_id": last_history_id,
            "last_sync_at": datetime.now(timezone.utc).isoformat()
        }
        
        if is_backfill:
            sync_data["last_backfill_from"] = datetime.now(timezone.utc).isoformat()
        
        def _upsert():
            return client.table("sync_meta").upsert(
                sync_data,
                on_conflict="user_id"
            ).execute()
        
        response = await _run_in_thread(_upsert)
        return response.data[0] if response.data else {}
    except Exception as e:
        logger.error(f"Failed to upsert sync meta: {e}")
        raise
