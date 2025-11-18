from fastapi import APIRouter, HTTPException, Request
from typing import Optional
import httpx
from app.models.schemas import (
    ProcessThreadRequest,
    ProcessThreadResponse,
    ChatbotQARequest,
    ChatbotQAResponse,
    UpdateUserSettingsRequest,
    UpdateUserSettingsResponse,
    PersonalizedKeyword,
    BatchAnalyzeRequest,
    BatchAnalyzeResponse,
    ThreadAnalysisResult,
    SummarizeRequest,
    SummarizeResponse,
    ExtractTasksRequest,
    ExtractTasksResponse,
    PrioritizeRequest,
    PrioritizeResponse,
    ToggleFlagRequest,
    ToggleFlagResponse,
    GetFlaggedEmailsResponse,
    DeleteFlagResponse,
    SetDeadlineOverrideRequest,
    SetDeadlineOverrideResponse,
    GetDeadlineOverridesResponse,
    DeleteDeadlineOverrideResponse
)
from app.services.normalizer import normalize_thread
from app.services.summarizer import summarize_thread
from app.services.extractor import extract_tasks
from app.services.prioritizer import calculate_priority
from app.services.qa import answer_question
from app.services.user_settings import update_user_settings, get_user_keywords
import asyncio
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/api/process-thread", response_model=ProcessThreadResponse)
async def process_thread(request: ProcessThreadRequest):
    try:
        thread = normalize_thread(request.messages)
        
        messages_dict = [
            {
                'id': msg.id,
                'from_': next((m.from_ for m in request.messages if m.id == msg.id), 'unknown'),
                'subject': next((m.subject for m in request.messages if m.id == msg.id), ''),
                'clean_body': msg.clean_body,
                'to': next((m.to for m in request.messages if m.id == msg.id), []),
                'cc': next((m.cc for m in request.messages if m.id == msg.id), [])
            }
            for msg in thread.normalized_messages
        ]
        
        summary = await summarize_thread(messages_dict)
        
        tasks = await extract_tasks(messages_dict)
        
        priority = await calculate_priority(messages_dict, tasks, request.personalized_keywords)
        
        return ProcessThreadResponse(
            thread=thread,
            summary=summary,
            tasks=tasks,
            priority=priority
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/chatbot-qa", response_model=ChatbotQAResponse)
async def chatbot_qa(request: ChatbotQARequest):
    try:
        # Convert simple thread array or dict to ThreadData if needed
        thread_data = request.thread
        
        # If thread is a dict, convert to ThreadData
        if isinstance(thread_data, dict):
            from app.models.schemas import ThreadData, NormalizedMessage, TimelineItem
            thread_data = ThreadData(**thread_data)
        
        # If thread is a list (from Apps Script), validate and convert to ThreadData
        elif isinstance(thread_data, list):
            from app.models.schemas import ThreadData, NormalizedMessage, TimelineItem, AppsScriptMessage
            
            # Validate as AppsScriptMessage list
            try:
                validated_msgs = [AppsScriptMessage(**msg) for msg in thread_data]
            except Exception as e:
                raise HTTPException(status_code=422, detail=f"Invalid Apps Script message format: {e}")
            
            # Build ThreadData from Apps Script messages
            participants = set()
            timeline = []
            normalized_messages = []
            thread_id = validated_msgs[0].id if validated_msgs else "chatbot-thread"
            
            for msg in validated_msgs:
                # Extract participants using correct field names
                if msg.from_:
                    participants.add(msg.from_)
                if msg.to:
                    participants.update(msg.to)
                
                # Build timeline item
                timeline.append(TimelineItem(
                    id=msg.id,
                    date=msg.date or '',
                    subject=msg.subject
                ))
                
                # Build normalized message - use last_message as clean_body
                clean_body = msg.last_message or msg.snippet or ''
                normalized_messages.append(NormalizedMessage(
                    id=msg.id,
                    clean_body=clean_body
                ))
            
            thread_data = ThreadData(
                thread_id=thread_id,
                participants=list(participants),
                timeline=timeline,
                normalized_messages=normalized_messages
            )
        
        response = await answer_question(request.question, thread_data)
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/update-user-settings", response_model=UpdateUserSettingsResponse)
async def update_settings(request: UpdateUserSettingsRequest):
    try:
        add_keywords = [kw.dict() for kw in request.add_keywords]
        success = update_user_settings(
            request.user_id,
            add_keywords,
            request.remove_keywords
        )
        
        return UpdateUserSettingsResponse(ok=success)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/batch-analyze", response_model=BatchAnalyzeResponse)
async def batch_analyze(request: BatchAnalyzeRequest):
    """
    Batch analyze threads using local Hugging Face models:
    - DistilBART for summarization
    - MiniLM + NER + Flan-T5 for task extraction
    - MiniLM for semantic keyword matching in prioritization
    
    Also enriches results with Supabase data:
    - Flag status (is_flagged)
    - Deadline overrides
    """
    try:
        results = []
        threads = request.threads
        keywords = request.keywords
        user_email = request.user_email
        
        # Prefetch Supabase data for all emails (batch query)
        email_ids = [thread.id for thread in threads]
        flag_status_dict = {}
        deadline_overrides_dict = {}
        
        if user_email:
            # Run Supabase queries in thread pool to avoid blocking event loop
            flag_status_dict, deadline_overrides_dict = await asyncio.gather(
                asyncio.to_thread(
                    lambda: __import__('app.db.supabase_client', fromlist=['get_flag_status_for_emails']).get_flag_status_for_emails(user_email, email_ids)
                ),
                asyncio.to_thread(
                    lambda: __import__('app.db.supabase_client', fromlist=['get_deadline_overrides_for_emails']).get_deadline_overrides_for_emails(user_email, email_ids)
                )
            )
        
        async def analyze_single_thread(thread):
            try:
                # Build message dict for analysis
                messages_dict = [{
                    'id': thread.id,
                    'subject': thread.subject,
                    'clean_body': thread.last_message or thread.snippet or '',
                    'body': thread.last_message or thread.snippet or '',
                    'to': thread.to or [],
                    'from_': thread.from_ or 'unknown'
                }]
                
                # Summarize with DistilBART
                summary = await summarize_thread(messages_dict)
                
                # Extract tasks with MiniLM + NER + Flan-T5
                tasks = await extract_tasks(messages_dict)
                
                # Apply deadline overrides from Supabase
                for task_index, task in enumerate(tasks):
                    override_key = (thread.id, task_index)
                    if override_key in deadline_overrides_dict:
                        task.due = deadline_overrides_dict[override_key]
                
                # Prioritize with hybrid approach (rule-based + GPT-4o-mini)
                priority = await calculate_priority(
                    messages_dict,
                    tasks,
                    keywords
                )
                
                # Get flag status from Supabase
                is_flagged = flag_status_dict.get(thread.id, False)
                
                return ThreadAnalysisResult(
                    id=thread.id,
                    summary=summary,
                    priority=priority,
                    tasks=tasks,
                    is_flagged=is_flagged
                )
            except Exception as e:
                from app.models.schemas import Priority
                return ThreadAnalysisResult(
                    id=thread.id,
                    summary=f"Error: {str(e)}",
                    priority=Priority(label="P3", score=0.0, reasons=["analysis failed"]),
                    tasks=[],
                    is_flagged=False
                )
        
        # Process in batches of 5 (model_manager batch_size)
        batch_size = 5
        for i in range(0, len(threads), batch_size):
            batch = threads[i:i + batch_size]
            batch_results = await asyncio.gather(*[analyze_single_thread(t) for t in batch])
            results.extend(batch_results)
        
        return BatchAnalyzeResponse(results=results)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/summarize", response_model=SummarizeResponse)
async def summarize_text(request: SummarizeRequest):
    """Summarize text using DistilBART with rule-based fallback"""
    try:
        summary = await summarize_thread([{
            'subject': request.subject,
            'clean_body': request.text,
            'body': request.text
        }])
        
        return SummarizeResponse(summary=summary)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/extract-tasks", response_model=ExtractTasksResponse)
async def extract_tasks_from_text(request: ExtractTasksRequest):
    """Extract tasks using GPT-4o-mini with rule-based fallback"""
    try:
        subject = getattr(request, 'subject', '')
        tasks = await extract_tasks([{
            'id': 'temp',
            'subject': subject,
            'clean_body': request.text,
            'body': request.text,
            'to': [],
            'from_': 'unknown'
        }])
        
        return ExtractTasksResponse(tasks=tasks)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/prioritize", response_model=PrioritizeResponse)
async def prioritize_email(request: PrioritizeRequest):
    try:
        from datetime import datetime, timedelta
        from app.models.schemas import Task
        
        tasks = []
        now = datetime.now()
        
        if request.has_deadline and request.deadline_hours is not None:
            due_time = now + timedelta(hours=request.deadline_hours)
            tasks.append(Task(
                title="Deadline detected",
                owner="you",
                due=due_time.isoformat(),
                source_message_id="temp",
                type="deadline"
            ))
        
        if request.has_meeting and request.meeting_hours is not None:
            meeting_time = now + timedelta(hours=request.meeting_hours)
            tasks.append(Task(
                title="Meeting detected",
                owner="you",
                due=meeting_time.isoformat(),
                source_message_id="temp",
                type="meeting"
            ))
        
        priority = await calculate_priority(
            [{
                'subject': request.subject,
                'clean_body': request.body,
                'body': request.body,
                'from_': request.from_,
                'to': request.to
            }],
            tasks,
            request.keywords
        )
        
        return PrioritizeResponse(priority=priority)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/triage")
async def triage_emails(
    request: Request,
    session_id: Optional[str] = None
):
    """
    Fetch Gmail emails from INBOX and return minimal analyzed_emails structure.
    Frontend expects: { analyzed_emails: [], summary: {}, debug: {} }
    
    HOTFIX: Relaxed Gmail query with fallback to ensure emails are returned.
    """
    try:
        import os
        from app.api.oauth import get_session
        
        # Get session_id from query param or cookie
        session_id_param = request.query_params.get("session_id")
        actual_session_id = session_id or session_id_param
        
        if not actual_session_id:
            raise HTTPException(status_code=401, detail="Not authenticated - no session_id")
        
        # Get session to retrieve access token
        session = get_session(actual_session_id)
        if not session or not session.get("tokens"):
            raise HTTPException(status_code=401, detail="Invalid or expired session")
        
        access_token = session["tokens"].get("access_token")
        if not access_token:
            raise HTTPException(status_code=401, detail="No access token in session")
        
        user_email = session.get("user", {}).get("email")
        
        # Get request body for label and pageToken
        try:
            body = await request.json()
        except:
            body = {}
        label = body.get("label", "IMPORTANT")  # Default to IMPORTANT
        page_token = body.get("pageToken")
        
        # Configurable max results (default 50)
        max_results = int(os.getenv("TRIAGE_MAX_RESULTS", "50"))
        
        # Fetch messages from Gmail API
        async with httpx.AsyncClient() as client:
            # Primary query: INBOX label, use time window for better results
            # Use newer_than:30d to get recent emails (more reliable than no filter)
            primary_params = {
                "labelIds": ["INBOX"],
                "maxResults": max_results,
                "includeSpamTrash": False,
                "q": "newer_than:30d"  # Get emails from last 30 days
            }
            if page_token:
                primary_params["pageToken"] = page_token
            
            primary_url = "https://gmail.googleapis.com/gmail/v1/users/me/messages"
            primary_response = await client.get(
                primary_url,
                params=primary_params,
                headers={"Authorization": f"Bearer {access_token}"}
            )
            primary_response.raise_for_status()
            primary_data = primary_response.json()
            primary_messages = primary_data.get("messages", [])
            primary_query_count = len(primary_messages)
            
            logger.info(f"Primary Gmail query returned {primary_query_count} messages")
            
            # Fallback query if primary returns 0 messages
            fallback_messages = []
            fallback_query_count = 0
            if primary_query_count == 0:
                logger.info("Primary query returned 0 messages, trying fallback (no label filter)")
                fallback_params = {
                    "maxResults": max_results,
                    "includeSpamTrash": False,
                    "q": "newer_than:30d"  # Still use time window for fallback
                    # NO labelIds - get from all labels
                }
                if page_token:
                    fallback_params["pageToken"] = page_token
                
                fallback_response = await client.get(
                    primary_url,
                    params=fallback_params,
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                fallback_response.raise_for_status()
                fallback_data = fallback_response.json()
                fallback_messages = fallback_data.get("messages", [])
                fallback_query_count = len(fallback_messages)
                logger.info(f"Fallback Gmail query returned {fallback_query_count} messages")
            
            # Use fallback if primary was empty, otherwise use primary
            message_list = fallback_messages if primary_query_count == 0 else primary_messages
            
            if not message_list:
                logger.warning("Both primary and fallback queries returned 0 messages")
                return {
                    "analyzed_emails": [],
                    "summary": {"total": 0, "urgent": 0, "todo": 0, "fyi": 0},
                    "debug": {
                        "primaryQueryCount": primary_query_count,
                        "fallbackQueryCount": fallback_query_count
                    }
                }
            
            # Fetch full message details for each message ID and parse with MIME decoder
            from app.services.gmail_parser import parse_gmail_message
            from app.models.schemas import EmailAttachment
            
            analyzed_emails = []
            for msg_ref in message_list[:max_results]:  # Limit to max_results
                msg_id = msg_ref.get("id")
                if not msg_id:
                    continue
                
                # Get full message details (format=full to get body and attachments)
                msg_url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg_id}"
                msg_response = await client.get(
                    msg_url,
                    params={"format": "full"},
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                msg_response.raise_for_status()
                msg_data = msg_response.json()
                
                # Parse message with MIME decoder
                parsed = parse_gmail_message(msg_data, access_token)
                
                # Convert attachments to EmailAttachment models
                attachments = [
                    EmailAttachment(**att) for att in parsed["attachments"]
                ]
                
                # Build analyzed email entry
                analyzed_emails.append({
                    "id": parsed["id"],
                    "threadId": parsed["thread_id"],
                    "from_name": parsed["from_name"],
                    "from_email": parsed["from_email"],
                    "from": parsed["from_email"],  # Keep for backward compatibility
                    "subject": parsed["subject"],
                    "date": parsed["date"],
                    "snippet": parsed["snippet"],
                    "body_html": parsed["body_html"],
                    "body_text": parsed["body_text"],
                    "inline_images": parsed["inline_images"],
                    "attachments": [att.dict() for att in attachments],
                    "summary": parsed["snippet"][:100] if parsed["snippet"] else "",  # Use snippet as summary for now
                    "priority": {"label": "P3 - FYI", "score": 0.0, "reasons": []},  # Default priority
                    "tasks": [],
                    "task_extracted": None,
                    "is_flagged": False
                })
        
        return {
            "analyzed_emails": analyzed_emails,
            "summary": {
                "total": len(analyzed_emails),
                "urgent": 0,  # Set to 0 for hotfix
                "todo": 0,    # Set to 0 for hotfix
                "fyi": 0      # Set to 0 for hotfix
            },
            "debug": {
                "primaryQueryCount": primary_query_count,
                "fallbackQueryCount": fallback_query_count
            }
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# Flag Status Routes
# ==========================================

@router.post("/api/flags/toggle", response_model=ToggleFlagResponse)
async def toggle_flag(body: ToggleFlagRequest):
    """
    Toggle flag status for an email.
    Requires user authentication (user_email passed from Node.js server).
    """
    try:
        from app.db.supabase_client import toggle_flag_status
        
        # Get user email from request body (passed from Node.js server)
        user_email = body.user_email
        if not user_email:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        # Toggle flag in database
        await toggle_flag_status(user_email, body.email_id, body.is_flagged)
        
        logger.info(f"Toggled flag for email {body.email_id} (user: {user_email}, flagged: {body.is_flagged})")
        
        return ToggleFlagResponse(
            success=True,
            email_id=body.email_id,
            is_flagged=body.is_flagged
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error toggling flag: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/flags", response_model=GetFlaggedEmailsResponse)
async def get_flagged_emails_route(user_email: str):
    """
    Get all flagged emails for the current user.
    Requires user authentication (user_email passed from Node.js server as query param).
    """
    try:
        from app.db.supabase_client import get_flagged_emails
        
        if not user_email:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        # Get flagged emails from database
        flagged = await get_flagged_emails(user_email)
        
        logger.info(f"Retrieved {len(flagged)} flagged emails for user: {user_email}")
        
        return GetFlaggedEmailsResponse(flagged_emails=flagged)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting flagged emails: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/flags/{email_id}", response_model=DeleteFlagResponse)
async def delete_flag(email_id: str, user_email: str):
    """
    Delete flag status for an email.
    Requires user authentication (user_email passed from Node.js server as query param).
    """
    try:
        from app.db.supabase_client import delete_flag_status
        
        if not user_email:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        # Delete flag from database
        await delete_flag_status(user_email, email_id)
        
        logger.info(f"Deleted flag for email {email_id} (user: {user_email})")
        
        return DeleteFlagResponse(
            success=True,
            email_id=email_id
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting flag: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# Deadline Override Routes
# ==========================================

@router.post("/api/deadline-overrides", response_model=SetDeadlineOverrideResponse)
async def set_deadline_override_route(body: SetDeadlineOverrideRequest):
    """
    Set or update deadline override for a task.
    Requires user authentication (user_email passed from Node.js server in request body).
    """
    try:
        from app.db.supabase_client import set_deadline_override as db_set_deadline
        
        # Get user email from request body (passed from Node.js server)
        user_email = body.user_email
        if not user_email:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        # Set deadline override in database
        await db_set_deadline(
            user_email,
            body.email_id,
            body.task_index,
            body.original_deadline,
            body.override_deadline
        )
        
        logger.info(f"Set deadline override for email {body.email_id}, task {body.task_index} (user: {user_email}): {body.override_deadline}")
        
        return SetDeadlineOverrideResponse(
            success=True,
            email_id=body.email_id,
            task_index=body.task_index,
            override_deadline=body.override_deadline
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting deadline override: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/deadline-overrides", response_model=GetDeadlineOverridesResponse)
async def get_deadline_overrides_route(user_email: str):
    """
    Get all deadline overrides for the current user.
    Requires user authentication (user_email passed from Node.js server as query param).
    """
    try:
        from app.db.supabase_client import get_deadline_overrides as db_get_deadline_overrides
        
        if not user_email:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        # Get deadline overrides from database
        overrides = await db_get_deadline_overrides(user_email)
        
        logger.info(f"Retrieved {len(overrides)} deadline overrides for user: {user_email}")
        
        return GetDeadlineOverridesResponse(deadline_overrides=overrides)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting deadline overrides: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/deadline-overrides/{email_id}/{task_index}", response_model=DeleteDeadlineOverrideResponse)
async def delete_deadline_override_route(email_id: str, task_index: int, user_email: str):
    """
    Delete deadline override for a task.
    Requires user authentication (user_email passed from Node.js server as query param).
    """
    try:
        from app.db.supabase_client import delete_deadline_override as db_delete_deadline
        
        if not user_email:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        # Delete deadline override from database
        await db_delete_deadline(user_email, email_id, task_index)
        
        logger.info(f"Deleted deadline override for email {email_id}, task {task_index} (user: {user_email})")
        
        return DeleteDeadlineOverrideResponse(
            success=True,
            email_id=email_id,
            task_index=task_index
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting deadline override: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# Attachment & Image Proxy Routes
# ==========================================

@router.get("/api/message/{message_id}/attachment/{attachment_id}")
async def get_attachment(
    message_id: str,
    attachment_id: str,
    request: Request,
    session_id: Optional[str] = None
):
    """
    Download attachment from Gmail and proxy it to frontend.
    Sets proper Content-Type and Content-Disposition headers.
    """
    try:
        from app.api.oauth import get_session
        
        # Get session_id from query param or cookie
        session_id_param = request.query_params.get("session_id")
        actual_session_id = session_id or session_id_param
        
        if not actual_session_id:
            raise HTTPException(status_code=401, detail="Not authenticated - no session_id")
        
        # Get session to retrieve access token
        session = get_session(actual_session_id)
        if not session or not session.get("tokens"):
            raise HTTPException(status_code=401, detail="Invalid or expired session")
        
        access_token = session["tokens"].get("access_token")
        if not access_token:
            raise HTTPException(status_code=401, detail="No access token in session")
        
        # Fetch attachment from Gmail API
        async with httpx.AsyncClient() as client:
            attachment_url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}/attachments/{attachment_id}"
            attachment_response = await client.get(
                attachment_url,
                headers={"Authorization": f"Bearer {access_token}"}
            )
            attachment_response.raise_for_status()
            attachment_data = attachment_response.json()
            
            # Decode base64 data
            data = attachment_data.get("data", "")
            if not data:
                raise HTTPException(status_code=404, detail="Attachment data not found")
            
            import base64
            attachment_bytes = base64.urlsafe_b64decode(data + '==')
            
            # Get message to find attachment metadata (filename, mime type)
            msg_url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}"
            msg_response = await client.get(
                msg_url,
                params={"format": "full"},
                headers={"Authorization": f"Bearer {access_token}"}
            )
            msg_response.raise_for_status()
            msg_data = msg_response.json()
            
            # Find attachment metadata
            filename = f"attachment_{attachment_id}"
            mime_type = "application/octet-stream"
            
            def find_attachment_in_parts(parts, att_id):
                for part in parts:
                    body = part.get("body", {})
                    if body.get("attachmentId") == att_id:
                        headers = part.get("headers", [])
                        for header in headers:
                            name = header.get("name", "").lower()
                            value = header.get("value", "")
                            if name == "content-disposition":
                                # Extract filename
                                import re
                                filename_match = re.search(r'filename[^;=\n]*=(([\'"]).*?\2|[^;\n]*)', value, re.IGNORECASE)
                                if filename_match:
                                    from app.services.gmail_parser import decode_mime_header
                                    filename = decode_mime_header(filename_match.group(1).strip('"\''))
                            elif name == "content-type":
                                # Extract mime type
                                mime_match = re.search(r'^([^;]+)', value)
                                if mime_match:
                                    mime_type = mime_match.group(1).strip()
                        return part.get("mimeType", mime_type), filename
                    if "parts" in part:
                        result = find_attachment_in_parts(part["parts"], att_id)
                        if result:
                            return result
                return None
            
            payload = msg_data.get("payload", {})
            parts = payload.get("parts", [])
            if parts:
                result = find_attachment_in_parts(parts, attachment_id)
                if result:
                    mime_type, filename = result
            
            # Return attachment with proper headers
            from fastapi.responses import Response
            return Response(
                content=attachment_bytes,
                media_type=mime_type,
                headers={
                    "Content-Disposition": f'inline; filename="{filename}"',
                    "Access-Control-Allow-Origin": "https://ai-mail-pilot.vercel.app",
                    "Access-Control-Allow-Credentials": "true",
                    "Cache-Control": "public, max-age=3600"
                }
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching attachment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/proxy-image")
async def proxy_image(
    url: str,
    request: Request
):
    """
    Proxy external images to avoid CORS and mixed content issues.
    """
    try:
        import urllib.parse
        
        # Decode URL
        image_url = urllib.parse.unquote(url)
        
        # Validate URL
        if not image_url.startswith(("http://", "https://")):
            raise HTTPException(status_code=400, detail="Invalid image URL")
        
        # Fetch image
        async with httpx.AsyncClient(timeout=10.0) as client:
            image_response = await client.get(image_url, follow_redirects=True)
            image_response.raise_for_status()
            
            # Get content type
            content_type = image_response.headers.get("Content-Type", "image/jpeg")
            
            # Return proxied image
            from fastapi.responses import Response
            return Response(
                content=image_response.content,
                media_type=content_type,
                headers={
                    "Access-Control-Allow-Origin": "https://ai-mail-pilot.vercel.app",
                    "Access-Control-Allow-Credentials": "true",
                    "Cache-Control": "public, max-age=86400"  # 24 hours
                }
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error proxying image: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# Sync & Task Management Routes
# ==========================================

@router.post("/api/refresh")
async def refresh_emails(
    request: Request,
    session_id: Optional[str] = None
):
    """
    Refresh emails: run incremental sync or cold start backfill
    Returns sync result with mode, counts, and latest_history_id
    """
    try:
        from app.api.oauth import get_session
        from app.services.gmail_sync import sync_emails
        from app.services.task_extractor import process_unprocessed_emails
        from app.db.supabase_client import get_sync_meta
        
        # Get session
        session_id_param = request.query_params.get("session_id")
        actual_session_id = session_id or session_id_param
        
        if not actual_session_id:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        session = get_session(actual_session_id)
        if not session or not session.get("tokens"):
            raise HTTPException(status_code=401, detail="Invalid session")
        
        access_token = session["tokens"].get("access_token")
        user_email = session.get("user", {}).get("email")
        
        if not access_token or not user_email:
            raise HTTPException(status_code=401, detail="Missing credentials")
        
        # Get last_history_id
        sync_meta = await get_sync_meta(user_email)
        last_history_id = sync_meta.get("last_history_id") if sync_meta else None
        
        # Run sync
        sync_result = await sync_emails(access_token, user_email, last_history_id)
        
        # Process unprocessed emails for tasks
        added_tasks = await process_unprocessed_emails(user_email, limit=50)
        
        return {
            "mode": sync_result["mode"],
            "scanned_messages": sync_result["scanned_messages"],
            "added_emails": sync_result["added_emails"],
            "added_tasks": added_tasks,
            "latest_history_id": sync_result["latest_history_id"]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Refresh failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/triage")
async def get_triage_tasks(
    request: Request,
    limit: int = 50,
    session_id: Optional[str] = None
):
    """
    Get Inbox Reminder: tasks with state="new" only
    Returns summary counts and new tasks
    """
    try:
        from app.api.oauth import get_session
        from app.db.supabase_client import get_tasks, get_email_by_id
        
        # Get session
        session_id_param = request.query_params.get("session_id")
        actual_session_id = session_id or session_id_param
        
        if not actual_session_id:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        session = get_session(actual_session_id)
        if not session or not session.get("user"):
            raise HTTPException(status_code=401, detail="Invalid session")
        
        user_email = session.get("user", {}).get("email")
        if not user_email:
            raise HTTPException(status_code=401, detail="Missing user email")
        
        # Get new tasks only
        new_tasks = await get_tasks(user_email, state="new", limit=limit)
        
        # Get all tasks for summary counts
        all_tasks = await get_tasks(user_email, state="all", limit=1000)
        urgent_count = sum(1 for t in all_tasks if t.get("priority") == "urgent" and t.get("state") != "done")
        todo_count = sum(1 for t in all_tasks if t.get("priority") == "todo" and t.get("state") != "done")
        fyi_count = sum(1 for t in all_tasks if t.get("priority") == "fyi" and t.get("state") != "done")
        
        # Build analyzed_emails from tasks (for frontend compatibility)
        analyzed_emails = []
        for task in new_tasks:
            message_id = task.get("message_id")
            email = await get_email_by_id(user_email, message_id)
            
            if email:
                analyzed_emails.append({
                    "id": message_id,
                    "threadId": email.get("thread_id", ""),
                    "from_name": email.get("from_name", ""),
                    "from_email": email.get("from_email", ""),
                    "from": email.get("from_email", ""),
                    "subject": email.get("subject", ""),
                    "date": email.get("date_iso", ""),
                    "snippet": email.get("snippet", ""),
                    "body_html": email.get("normalized_html"),
                    "body_text": email.get("normalized_text"),
                    "summary": email.get("snippet", "")[:100],
                    "priority": {"label": f"P{1 if task.get('priority') == 'urgent' else 2 if task.get('priority') == 'todo' else 3}", "score": 0.0, "reasons": []},
                    "tasks": [{"title": task.get("normalized_title", ""), "type": "action"}],
                    "task_extracted": task.get("normalized_title", ""),
                    "is_flagged": False,
                    "task_id": task.get("task_id")  # Include task_id for state transitions
                })
        
        return {
            "analyzed_emails": analyzed_emails,
            "summary": {
                "total": len(analyzed_emails),
                "urgent": urgent_count,
                "todo": todo_count,
                "fyi": fyi_count
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get triage failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/tasks")
async def get_tasks_route(
    request: Request,
    state: str = "open",
    limit: int = 50,
    offset: int = 0,
    session_id: Optional[str] = None
):
    """
    Get tasks with state filter
    state: "all" | "open" | "new" | "viewed" | "saved" | "done"
    """
    try:
        from app.api.oauth import get_session
        from app.db.supabase_client import get_tasks, get_email_by_id
        
        # Get session
        session_id_param = request.query_params.get("session_id")
        actual_session_id = session_id or session_id_param
        
        if not actual_session_id:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        session = get_session(actual_session_id)
        if not session or not session.get("user"):
            raise HTTPException(status_code=401, detail="Invalid session")
        
        user_email = session.get("user", {}).get("email")
        if not user_email:
            raise HTTPException(status_code=401, detail="Missing user email")
        
        # Get tasks
        tasks = await get_tasks(user_email, state=state, limit=limit, offset=offset)
        
        # Enrich with email data
        enriched_tasks = []
        for task in tasks:
            message_id = task.get("message_id")
            email = await get_email_by_id(user_email, message_id)
            
            enriched_tasks.append({
                **task,
                "email": {
                    "id": message_id,
                    "thread_id": email.get("thread_id", "") if email else "",
                    "from_name": email.get("from_name", "") if email else "",
                    "from_email": email.get("from_email", "") if email else "",
                    "subject": email.get("subject", "") if email else "",
                    "date": email.get("date_iso", "") if email else "",
                    "snippet": email.get("snippet", "") if email else ""
                } if email else None
            })
        
        return {"tasks": enriched_tasks}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get tasks failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/tasks/{task_id}/viewed")
async def mark_task_viewed(
    task_id: int,
    request: Request,
    session_id: Optional[str] = None
):
    """Mark task as viewed (new → viewed)"""
    try:
        from app.api.oauth import get_session
        from app.db.supabase_client import update_task_state
        
        session_id_param = request.query_params.get("session_id")
        actual_session_id = session_id or session_id_param
        
        if not actual_session_id:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        session = get_session(actual_session_id)
        user_email = session.get("user", {}).get("email") if session else None
        
        if not user_email:
            raise HTTPException(status_code=401, detail="Invalid session")
        
        task = await update_task_state(user_email, task_id, "viewed")
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        return {"success": True, "task_id": task_id, "state": "viewed"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Mark task viewed failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/tasks/{task_id}/save")
async def mark_task_saved(
    task_id: int,
    request: Request,
    session_id: Optional[str] = None
):
    """Mark task as saved (→ saved)"""
    try:
        from app.api.oauth import get_session
        from app.db.supabase_client import update_task_state
        
        session_id_param = request.query_params.get("session_id")
        actual_session_id = session_id or session_id_param
        
        if not actual_session_id:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        session = get_session(actual_session_id)
        user_email = session.get("user", {}).get("email") if session else None
        
        if not user_email:
            raise HTTPException(status_code=401, detail="Invalid session")
        
        task = await update_task_state(user_email, task_id, "saved")
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        return {"success": True, "task_id": task_id, "state": "saved"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Mark task saved failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/tasks/{task_id}/done")
async def mark_task_done(
    task_id: int,
    request: Request,
    session_id: Optional[str] = None
):
    """Mark task as done (→ done)"""
    try:
        from app.api.oauth import get_session
        from app.db.supabase_client import update_task_state
        
        session_id_param = request.query_params.get("session_id")
        actual_session_id = session_id or session_id_param
        
        if not actual_session_id:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        session = get_session(actual_session_id)
        user_email = session.get("user", {}).get("email") if session else None
        
        if not user_email:
            raise HTTPException(status_code=401, detail="Invalid session")
        
        task = await update_task_state(user_email, task_id, "done")
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        return {"success": True, "task_id": task_id, "state": "done"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Mark task done failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
