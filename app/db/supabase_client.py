"""
Supabase Client Initialization
Handles connection to Supabase PostgreSQL database for data persistence.
"""
import os
from typing import Optional, Any
from supabase import create_client, Client
import logging

logger = logging.getLogger(__name__)

# Global Supabase client instance
_supabase_client: Optional[Client] = None


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
        
        # Upsert: insert if not exists, update if exists
        response = client.table("flag_status").upsert({
            "user_email": user_email,
            "email_id": email_id,
            "is_flagged": is_flagged
        }, on_conflict="user_email,email_id").execute()
        
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
        
        response = client.table("flag_status").select("*").eq("user_email", user_email).eq("is_flagged", True).order("updated_at", desc=True).execute()
        
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
        
        response = client.table("flag_status").delete().eq("user_email", user_email).eq("email_id", email_id).execute()
        
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
        
        response = client.table("deadline_overrides").upsert({
            "user_email": user_email,
            "email_id": email_id,
            "task_index": task_index,
            "original_deadline": original_deadline,
            "override_deadline": override_deadline
        }, on_conflict="user_email,email_id,task_index").execute()
        
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
        
        response = client.table("deadline_overrides").select("*").eq("user_email", user_email).execute()
        
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
        
        response = client.table("deadline_overrides").delete().eq("user_email", user_email).eq("email_id", email_id).eq("task_index", task_index).execute()
        
        logger.info(f"Deadline override deleted for user={user_email}, email_id={email_id}, task_index={task_index}")
        return True
    except Exception as e:
        logger.error(f"Failed to delete deadline override: {e}")
        raise
