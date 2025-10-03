from typing import List, Dict, Any
from rapidfuzz import fuzz
from app.models.schemas import ThreadData, ChatbotQAResponse
from app.core.llm import llm_provider


def build_index(thread: ThreadData) -> List[Dict[str, str]]:
    index = []
    
    for msg in thread.normalized_messages:
        index.append({
            'message_id': msg.id,
            'text': msg.clean_body
        })
    
    return index


def retrieve_snippets(question: str, index: List[Dict[str, str]], top_k: int = 3) -> List[Dict[str, str]]:
    scored_snippets = []
    
    for snippet in index:
        score = fuzz.partial_ratio(question.lower(), snippet['text'].lower())
        scored_snippets.append((score, snippet))
    
    scored_snippets.sort(reverse=True, key=lambda x: x[0])
    
    return [snippet for score, snippet in scored_snippets[:top_k]]


async def answer_question(question: str, thread: ThreadData) -> ChatbotQAResponse:
    index = build_index(thread)
    
    if not index:
        return ChatbotQAResponse(
            answer="Not found in thread.",
            sources=[]
        )
    
    snippets = retrieve_snippets(question, index, top_k=3)
    
    if llm_provider.api_key:
        result = await llm_provider.answer(question, snippets)
        return ChatbotQAResponse(
            answer=result['answer'],
            sources=result['sources']
        )
    else:
        answer_parts = []
        sources = []
        
        for snippet in snippets:
            answer_parts.append(snippet['text'][:100])
            sources.append(snippet['message_id'])
        
        answer = ' '.join(answer_parts)
        if len(answer) > 200:
            answer = answer[:197] + "..."
        
        return ChatbotQAResponse(
            answer=answer or "Not found in thread.",
            sources=sources
        )
