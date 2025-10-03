from fastapi import APIRouter, HTTPException
from app.models.schemas import (
    ProcessThreadRequest,
    ProcessThreadResponse,
    ChatbotQARequest,
    ChatbotQAResponse,
    UpdateUserSettingsRequest,
    UpdateUserSettingsResponse,
    PersonalizedKeyword
)
from app.services.normalizer import normalize_thread
from app.services.summarizer import summarize_thread
from app.services.extractor import extract_tasks
from app.services.prioritizer import calculate_priority
from app.services.qa import answer_question
from app.services.user_settings import update_user_settings, get_user_keywords


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
        
        priority = calculate_priority(messages_dict, tasks, request.personalized_keywords)
        
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
        response = await answer_question(request.question, request.thread)
        return response
    
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
