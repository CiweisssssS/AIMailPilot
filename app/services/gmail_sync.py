"""
Gmail History API sync service
Implements two-phase fetching: cold start backfill + incremental sync
"""
import os
import asyncio
import logging
from typing import Optional, Dict, List, Tuple
from datetime import datetime, timedelta
import httpx
from app.services.gmail_parser import parse_gmail_message

logger = logging.getLogger(__name__)

# Configuration
BACKFILL_DAYS = int(os.getenv("BACKFILL_DAYS", "7"))
INCREMENTAL_PAGE_LIMIT = int(os.getenv("INCREMENTAL_PAGE_LIMIT", "2"))
CONCURRENCY_FETCH_MESSAGES = int(os.getenv("CONCURRENCY_FETCH_MESSAGES", "5"))


async def get_gmail_profile(access_token: str) -> Dict:
    """Get Gmail user profile to read historyId baseline"""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://gmail.googleapis.com/gmail/v1/users/me/profile",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        response.raise_for_status()
        return response.json()


async def fetch_messages_batch(
    access_token: str,
    message_ids: List[str],
    concurrency: int = CONCURRENCY_FETCH_MESSAGES
) -> List[Dict]:
    """Fetch multiple messages with bounded concurrency"""
    async def fetch_one(msg_id: str) -> Optional[Dict]:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg_id}",
                    params={"format": "full"},
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.warning(f"Failed to fetch message {msg_id}: {e}")
            return None
    
    # Process in batches with semaphore
    semaphore = asyncio.Semaphore(concurrency)
    
    async def fetch_with_limit(msg_id: str):
        async with semaphore:
            return await fetch_one(msg_id)
    
    results = await asyncio.gather(*[fetch_with_limit(msg_id) for msg_id in message_ids])
    return [r for r in results if r is not None]


async def cold_start_backfill(
    access_token: str,
    user_email: str,
    days: int = BACKFILL_DAYS
) -> Tuple[List[Dict], str]:
    """
    Cold start: fetch emails from last N days
    Returns: (list of parsed messages, latest_history_id)
    """
    logger.info(f"Starting cold start backfill for {days} days")
    
    # Get profile to get historyId baseline
    profile = await get_gmail_profile(access_token)
    latest_history_id = profile.get("historyId", "")
    
    # Fetch messages
    async with httpx.AsyncClient() as client:
        params = {
            "labelIds": ["INBOX"],
            "maxResults": 200,
            "includeSpamTrash": False,
            "q": f"newer_than:{days}d"
        }
        
        response = await client.get(
            "https://gmail.googleapis.com/gmail/v1/users/me/messages",
            params=params,
            headers={"Authorization": f"Bearer {access_token}"}
        )
        response.raise_for_status()
        data = response.json()
        message_refs = data.get("messages", [])
    
    logger.info(f"Cold start found {len(message_refs)} messages")
    
    # Fetch full message details
    message_ids = [ref["id"] for ref in message_refs]
    messages_data = await fetch_messages_batch(access_token, message_ids)
    
    # Parse messages
    parsed_messages = []
    for msg_data in messages_data:
        try:
            parsed = parse_gmail_message(msg_data, access_token)
            parsed_messages.append(parsed)
        except Exception as e:
            logger.warning(f"Failed to parse message {msg_data.get('id', 'unknown')}: {e}")
    
    logger.info(f"Cold start parsed {len(parsed_messages)} messages")
    return parsed_messages, latest_history_id


async def incremental_sync(
    access_token: str,
    user_email: str,
    start_history_id: str,
    page_limit: int = INCREMENTAL_PAGE_LIMIT
) -> Tuple[List[Dict], Optional[str], bool]:
    """
    Incremental sync: fetch changes since last_history_id
    Returns: (list of parsed messages, latest_history_id, success)
    If historyId too old, returns ([], None, False)
    """
    logger.info(f"Starting incremental sync from historyId: {start_history_id}")
    
    all_messages = []
    latest_history_id = None
    page_count = 0
    
    try:
        async with httpx.AsyncClient() as client:
            next_page_token = None
            
            while page_count < page_limit:
                params = {
                    "startHistoryId": start_history_id,
                    "historyTypes": ["messageAdded", "labelAdded", "messageDeleted", "labelRemoved"],
                    "maxResults": 100
                }
                if next_page_token:
                    params["pageToken"] = next_page_token
                
                response = await client.get(
                    "https://gmail.googleapis.com/gmail/v1/users/me/history",
                    params=params,
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                
                # Handle historyId too old
                if response.status_code == 404:
                    error_data = response.json() if response.content else {}
                    if "invalidArgument" in str(error_data.get("error", {}).get("message", "")):
                        logger.warning(f"HistoryId {start_history_id} too old, need cold start")
                        return ([], None, False)
                    raise
                
                response.raise_for_status()
                data = response.json()
                
                # Extract message IDs from history
                history_records = data.get("history", [])
                message_ids = set()
                
                for record in history_records:
                    # messageAdded
                    messages_added = record.get("messagesAdded", [])
                    for msg_added in messages_added:
                        msg = msg_added.get("message", {})
                        message_ids.add(msg.get("id"))
                    
                    # labelAdded (messages that got new labels)
                    labels_added = record.get("labelsAdded", [])
                    for label_added in labels_added:
                        msg = label_added.get("message", {})
                        message_ids.add(msg.get("id"))
                    
                    # messageDeleted and labelRemoved: we skip these for now
                    # (could mark as deleted in DB if needed)
                
                # Fetch full message details
                if message_ids:
                    messages_data = await fetch_messages_batch(access_token, list(message_ids))
                    for msg_data in messages_data:
                        try:
                            parsed = parse_gmail_message(msg_data, access_token)
                            all_messages.append(parsed)
                        except Exception as e:
                            logger.warning(f"Failed to parse message {msg_data.get('id', 'unknown')}: {e}")
                
                # Check for next page
                next_page_token = data.get("nextPageToken")
                latest_history_id = data.get("historyId")
                
                if not next_page_token:
                    break
                
                page_count += 1
        
        logger.info(f"Incremental sync found {len(all_messages)} new/updated messages")
        return (all_messages, latest_history_id, True)
    
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            logger.warning(f"HistoryId {start_history_id} too old: {e}")
            return ([], None, False)
        raise
    except Exception as e:
        logger.error(f"Incremental sync failed: {e}")
        raise


async def sync_emails(
    access_token: str,
    user_email: str,
    last_history_id: Optional[str] = None
) -> Dict:
    """
    Main sync function: cold start or incremental based on last_history_id
    Returns sync result with mode, counts, and latest_history_id
    """
    from app.db.supabase_client import get_sync_meta, upsert_sync_meta, upsert_email, get_email_by_id
    
    # Verify Gmail profile matches user
    profile = await get_gmail_profile(access_token)
    profile_email = profile.get("emailAddress", "")
    if profile_email != user_email:
        logger.error(f"Gmail profile email {profile_email} doesn't match user {user_email}")
        raise ValueError("Gmail account mismatch - please re-login")
    
    profile_history_id = profile.get("historyId", "")
    
    # Determine sync mode
    if not last_history_id:
        # Cold start
        logger.info("No last_history_id, starting cold start")
        parsed_messages, latest_history_id = await cold_start_backfill(access_token, user_email)
        mode = "coldStart"
        fallback = False
    else:
        # Try incremental
        parsed_messages, latest_history_id, success = await incremental_sync(
            access_token, user_email, last_history_id
        )
        
        if not success:
            # Fallback to cold start
            logger.info("Incremental failed, falling back to cold start")
            parsed_messages, latest_history_id = await cold_start_backfill(access_token, user_email)
            mode = "incrementalFallback"
            fallback = True
        else:
            mode = "incremental"
            fallback = False
    
    # Store emails and update sync_meta
    scanned_count = len(parsed_messages)
    added_count = 0
    
    for parsed in parsed_messages:
        try:
            # Check if email already exists
            existing = await get_email_by_id(user_email, parsed["id"])
            
            if not existing:
                # New email - store it
                await upsert_email(user_email, parsed, latest_history_id or profile_history_id)
                added_count += 1
            else:
                # Update last_seen_at
                await upsert_email(user_email, parsed, latest_history_id or profile_history_id, update_only=True)
        except Exception as e:
            logger.warning(f"Failed to store email {parsed.get('id', 'unknown')}: {e}")
    
    # Update sync_meta
    await upsert_sync_meta(
        user_email,
        latest_history_id or profile_history_id,
        mode == "coldStart" or fallback
    )
    
    return {
        "mode": mode,
        "scanned_messages": scanned_count,
        "added_emails": added_count,
        "latest_history_id": latest_history_id or profile_history_id
    }

