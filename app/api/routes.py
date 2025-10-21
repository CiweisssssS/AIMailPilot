from fastapi import APIRouter, HTTPException
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
    PrioritizeResponse
)
from app.services.normalizer import normalize_thread
from app.services.summarizer import summarize_thread
from app.services.extractor import extract_tasks
from app.services.prioritizer import calculate_priority
from app.services.qa import answer_question
from app.services.user_settings import update_user_settings, get_user_keywords
import asyncio


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
        # Convert simple thread array to ThreadData if needed
        thread_data = request.thread
        
        # If thread is a list (from Apps Script), validate and convert to ThreadData
        if isinstance(thread_data, list):
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
    """
    try:
        results = []
        threads = request.threads
        keywords = request.keywords
        
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
                
                # Prioritize with hybrid approach (rule-based + GPT-4o-mini)
                priority = await calculate_priority(
                    messages_dict,
                    tasks,
                    keywords
                )
                
                return ThreadAnalysisResult(
                    id=thread.id,
                    summary=summary,
                    priority=priority,
                    tasks=tasks
                )
            except Exception as e:
                from app.models.schemas import Priority
                return ThreadAnalysisResult(
                    id=thread.id,
                    summary=f"Error: {str(e)}",
                    priority=Priority(label="P3", score=0.0, reasons=["analysis failed"]),
                    tasks=[]
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
    """Extract tasks using MiniLM + NER + Flan-T5 with rule-based fallback"""
    try:
        tasks = await extract_tasks([{
            'id': 'temp',
            'subject': request.subject if hasattr(request, 'subject') else '',
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
