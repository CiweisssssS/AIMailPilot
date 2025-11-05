from fastapi import APIRouter, HTTPException, Request
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
async def triage_emails(request: dict):
    """
    Analyze multiple Gmail emails in parallel and return priorities, summaries, and tasks.
    Also enriches results with Supabase data (flag status, deadline overrides).
    Frontend expects: { analyzed_emails: [], summary: {} }
    
    Note: user_email is optional for unauthenticated analysis. When provided, 
    persistent data (flags, deadline overrides) will be loaded and merged.
    """
    try:
        from app.models.schemas import Priority
        
        messages = request.get('messages', [])
        user_email = request.get('user_email')
        
        if not messages:
            return {"analyzed_emails": [], "summary": {"total": 0, "urgent": 0, "todo": 0, "fyi": 0}}
        
        # Prefetch Supabase data for all emails (batch query)
        # Only query database if user is authenticated
        email_ids = [msg.get('id', 'unknown') for msg in messages]
        flag_status_dict = {}
        deadline_overrides_dict = {}
        
        if user_email:
            logger.info(f"Fetching Supabase data for user={user_email}, {len(email_ids)} emails")
            # Run Supabase queries in thread pool to avoid blocking event loop
            from app.db.supabase_client import get_flag_status_for_emails, get_deadline_overrides_for_emails
            try:
                flag_status_dict, deadline_overrides_dict = await asyncio.gather(
                    asyncio.to_thread(get_flag_status_for_emails, user_email, email_ids),
                    asyncio.to_thread(get_deadline_overrides_for_emails, user_email, email_ids)
                )
            except Exception as db_error:
                # Log but don't fail the entire request if Supabase is unavailable
                logger.error(f"Supabase query failed: {db_error}")
        else:
            logger.info("No user_email provided, skipping Supabase data fetch")
        
        # Parallel processing function for a single email
        async def analyze_single_email(msg):
            try:
                # Convert to format expected by services
                msg_dict = {
                    'id': msg.get('id', 'unknown'),
                    'from_': msg.get('from_', 'unknown'),
                    'subject': msg.get('subject', ''),
                    'clean_body': msg.get('clean_body', msg.get('body', '')),
                    'body': msg.get('body', ''),
                    'to': msg.get('to', []),
                    'cc': msg.get('cc', []),
                    'date': msg.get('date', '')  # CRITICAL: Pass email date for deadline normalization
                }
                
                # Process all three operations in parallel for each email
                summary_task = summarize_thread([msg_dict])
                tasks_task = extract_tasks([msg_dict])
                
                # Wait for both to complete
                summary, tasks = await asyncio.gather(summary_task, tasks_task)
                
                # Apply deadline overrides from Supabase
                email_id = msg.get('id', 'unknown')
                for task_index, task in enumerate(tasks):
                    override_key = (email_id, task_index)
                    if override_key in deadline_overrides_dict:
                        task.due = deadline_overrides_dict[override_key]
                
                # Calculate priority (needs tasks result)
                priority = await calculate_priority([msg_dict], tasks, [])
                
                return {
                    'summary': summary,
                    'tasks': tasks,
                    'priority': priority.dict()
                }
            except Exception as e:
                # Fallback for failed analysis
                return {
                    'summary': f"Error analyzing email: {str(e)[:100]}",
                    'tasks': [],
                    'priority': {'label': 'P3 - FYI', 'score': 0.0, 'reasons': ['Analysis failed']}
                }
        
        # Process all emails in parallel with batching for better performance
        batch_size = 5  # Process 5 emails at a time to avoid overwhelming the API
        all_results = []
        
        for i in range(0, len(messages), batch_size):
            batch = messages[i:i + batch_size]
            batch_results = await asyncio.gather(*[analyze_single_email(msg) for msg in batch])
            all_results.extend(batch_results)
        
        # Transform into frontend-expected format
        analyzed_emails = []
        urgent_count = 0
        todo_count = 0
        fyi_count = 0
        
        for i, result in enumerate(all_results):
            msg = messages[i]
            priority = result['priority']
            
            logger.info(f"Email {i}: subject={msg.get('subject', 'N/A')}, tasks_count={len(result.get('tasks', []))}")
            
            # Count by priority level
            if 'P1' in priority['label']:
                urgent_count += 1
            elif 'P2' in priority['label']:
                todo_count += 1
            else:
                fyi_count += 1
            
            # Extract first task as task_extracted string (clean title without ISO dates)
            task_extracted = None
            if result['tasks'] and len(result['tasks']) > 0:
                first_task = result['tasks'][0]
                logger.info(f"  First task: {first_task}")
                # Tasks are Pydantic objects, not dicts - access attribute directly
                if hasattr(first_task, 'title'):
                    title = first_task.title
                    # Remove ISO date suffixes like "2023-10-25T16:00:00"
                    import re
                    title = re.sub(r'\s*\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}.*$', '', title)
                    task_extracted = title.strip()
                elif isinstance(first_task, dict):
                    title = first_task.get('title', None)
                    if title:
                        import re
                        title = re.sub(r'\s*\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}.*$', '', title)
                        task_extracted = title.strip()
            
            # Safe snippet handling
            snippet = msg.get('snippet', '') or ''
            if snippet and len(snippet) > 100:
                snippet = snippet[:100]
            
            # Convert tasks to dicts if they are Pydantic objects
            tasks_list = []
            for task in result['tasks']:
                if hasattr(task, 'dict'):
                    task_dict = task.dict()
                    logger.info(f"Task dict for frontend: {task_dict}")
                    tasks_list.append(task_dict)
                elif isinstance(task, dict):
                    logger.info(f"Task dict (already dict) for frontend: {task}")
                    tasks_list.append(task)
                else:
                    logger.info(f"Task (unknown type): {task}")
                    tasks_list.append({'title': str(task)})
            
            # Get flag status from Supabase
            email_id = msg.get('id', 'unknown')
            is_flagged = flag_status_dict.get(email_id, False)
            
            analyzed_emails.append({
                'id': email_id,
                'threadId': msg.get('threadId', msg.get('thread_id', '')),
                'subject': msg.get('subject', ''),
                'from': msg.get('from_', 'unknown'),
                'snippet': snippet,
                'date': msg.get('date', ''),
                'summary': result['summary'],
                'priority': priority,
                'tasks': tasks_list,
                'task_extracted': task_extracted,
                'is_flagged': is_flagged
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
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# Flag Status Routes
# ==========================================

@router.post("/api/flags/toggle", response_model=ToggleFlagResponse)
async def toggle_flag(request: Request, body: ToggleFlagRequest):
    """
    Toggle flag status for an email.
    Requires user authentication.
    """
    try:
        from app.db.supabase_client import toggle_flag_status
        
        # Get user email from session
        user = request.session.get('user')
        if not user or not user.get('email'):
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        user_email = user['email']
        
        # Toggle flag in database
        await toggle_flag_status(user_email, body.email_id, body.is_flagged)
        
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
async def get_flagged_emails_route(request: Request):
    """
    Get all flagged emails for the current user.
    Requires user authentication.
    """
    try:
        from app.db.supabase_client import get_flagged_emails
        
        # Get user email from session
        user = request.session.get('user')
        if not user or not user.get('email'):
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        user_email = user['email']
        
        # Get flagged emails from database
        flagged = await get_flagged_emails(user_email)
        
        return GetFlaggedEmailsResponse(flagged_emails=flagged)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting flagged emails: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/flags/{email_id}", response_model=DeleteFlagResponse)
async def delete_flag(request: Request, email_id: str):
    """
    Delete flag status for an email.
    Requires user authentication.
    """
    try:
        from app.db.supabase_client import delete_flag_status
        
        # Get user email from session
        user = request.session.get('user')
        if not user or not user.get('email'):
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        user_email = user['email']
        
        # Delete flag from database
        await delete_flag_status(user_email, email_id)
        
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
async def set_deadline_override_route(request: Request, body: SetDeadlineOverrideRequest):
    """
    Set or update deadline override for a task.
    Requires user authentication.
    """
    try:
        from app.db.supabase_client import set_deadline_override as db_set_deadline
        
        # Get user email from session
        user = request.session.get('user')
        if not user or not user.get('email'):
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        user_email = user['email']
        
        # Set deadline override in database
        await db_set_deadline(
            user_email,
            body.email_id,
            body.task_index,
            body.original_deadline,
            body.override_deadline
        )
        
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
async def get_deadline_overrides_route(request: Request):
    """
    Get all deadline overrides for the current user.
    Requires user authentication.
    """
    try:
        from app.db.supabase_client import get_deadline_overrides as db_get_deadline_overrides
        
        # Get user email from session
        user = request.session.get('user')
        if not user or not user.get('email'):
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        user_email = user['email']
        
        # Get deadline overrides from database
        overrides = await db_get_deadline_overrides(user_email)
        
        return GetDeadlineOverridesResponse(deadline_overrides=overrides)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting deadline overrides: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/deadline-overrides/{email_id}/{task_index}", response_model=DeleteDeadlineOverrideResponse)
async def delete_deadline_override_route(request: Request, email_id: str, task_index: int):
    """
    Delete deadline override for a task.
    Requires user authentication.
    """
    try:
        from app.db.supabase_client import delete_deadline_override as db_delete_deadline
        
        # Get user email from session
        user = request.session.get('user')
        if not user or not user.get('email'):
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        user_email = user['email']
        
        # Delete deadline override from database
        await db_delete_deadline(user_email, email_id, task_index)
        
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
