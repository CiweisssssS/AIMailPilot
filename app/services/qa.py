from typing import List, Dict, Any
import logging
from app.models.schemas import ThreadData, ChatbotQAResponse
from app.core.llm import llm_provider

logger = logging.getLogger(__name__)


def build_context_snippets(thread: ThreadData, max_snippets: int = 5) -> List[Dict[str, str]]:
    """
    Build context snippets from thread messages for LLM.
    Simple chunking by message, no embeddings needed.
    """
    snippets = []
    
    for msg in thread.normalized_messages[-max_snippets:]:  # Use last N messages for recency
        snippets.append({
            'message_id': msg.id,
            'text': f"{msg.clean_body[:500]}"  # Truncate long messages
        })
    
    return snippets


async def answer_question(question: str, thread: ThreadData) -> ChatbotQAResponse:
    """
    Answer question using GPT-4o-mini with simple RAG (no embeddings)
    """
    if not thread.normalized_messages:
        return ChatbotQAResponse(
            answer="No content found in this thread.",
            sources=[]
        )
    
    # Build context snippets from messages
    snippets = build_context_snippets(thread, max_snippets=5)
    
    try:
        # Call LLM provider's answer method
        result = await llm_provider.answer(question, snippets)
        
        return ChatbotQAResponse(
            answer=result['answer'],
            sources=result['sources'][:3]  # Limit to top 3 sources
        )
        
    except Exception as e:
        logger.error(f"GPT-4o-mini QA failed: {e}")
        return ChatbotQAResponse(
            answer="I encountered an error processing your question. Please try again.",
            sources=[]
        )
