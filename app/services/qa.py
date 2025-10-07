from typing import List, Dict, Any
import logging
from app.models.schemas import ThreadData, ChatbotQAResponse
from app.core.model_manager import model_manager

logger = logging.getLogger(__name__)

# Retrieval and reranking thresholds
RETRIEVAL_TOP_K = 10  # Initial retrieval with MiniLM
RERANK_TOP_K = 3      # After cross-encoder reranking


def build_index(thread: ThreadData) -> List[Dict[str, Any]]:
    """Build searchable index from thread messages"""
    index = []
    
    for msg in thread.normalized_messages:
        # Split long messages into chunks for better retrieval
        text = msg.clean_body
        if len(text) > 500:
            # Chunk into sentences (max 3 per chunk)
            sentences = text.split('. ')
            chunks = []
            current_chunk = []
            
            for sent in sentences:
                current_chunk.append(sent)
                if len(current_chunk) >= 3:
                    chunks.append('. '.join(current_chunk) + '.')
                    current_chunk = []
            
            if current_chunk:
                chunks.append('. '.join(current_chunk))
            
            for i, chunk in enumerate(chunks):
                index.append({
                    'message_id': msg.id,
                    'chunk_id': f"{msg.id}_{i}",
                    'text': chunk
                })
        else:
            index.append({
                'message_id': msg.id,
                'chunk_id': msg.id,
                'text': text
            })
    
    return index


def retrieve_snippets(question: str, index: List[Dict[str, Any]], top_k: int = RETRIEVAL_TOP_K) -> List[Dict[str, Any]]:
    """Retrieve relevant snippets using MiniLM semantic search"""
    if not index:
        return []
    
    try:
        # Embed question
        question_emb = model_manager.embed_texts([question])[0]
        
        # Check for zero vector
        if sum(question_emb) == 0 or any(x != x for x in question_emb):
            logger.warning("Invalid question embedding, using keyword fallback")
            # Fallback: simple keyword matching
            scored_snippets = []
            question_words = set(question.lower().split())
            
            for snippet in index:
                text_words = set(snippet['text'].lower().split())
                overlap = len(question_words & text_words)
                scored_snippets.append((overlap, snippet))
            
            scored_snippets.sort(reverse=True, key=lambda x: x[0])
            return [snippet for score, snippet in scored_snippets[:top_k]]
        
        # Embed all snippets
        snippet_texts = [s['text'] for s in index]
        snippet_embs = model_manager.embed_texts(snippet_texts)
        
        # Compute cosine similarity
        def cosine_sim(a, b):
            dot = sum(x*y for x,y in zip(a,b))
            norm_a = (sum(x**2 for x in a))**0.5
            norm_b = (sum(x**2 for x in b))**0.5
            if norm_a < 1e-9 or norm_b < 1e-9:
                return 0.0
            return dot / (norm_a * norm_b)
        
        scored_snippets = []
        for snippet, emb in zip(index, snippet_embs):
            score = cosine_sim(question_emb, emb)
            scored_snippets.append((score, snippet))
        
        scored_snippets.sort(reverse=True, key=lambda x: x[0])
        
        return [snippet for score, snippet in scored_snippets[:top_k]]
        
    except Exception as e:
        logger.error(f"Retrieval failed: {e}, using fallback")
        # Fallback: return first few snippets
        return index[:top_k]


def rerank_snippets(question: str, snippets: List[Dict[str, Any]], top_k: int = RERANK_TOP_K) -> List[Dict[str, Any]]:
    """Rerank snippets using cross-encoder for better precision"""
    if not snippets or len(snippets) <= top_k:
        return snippets
    
    try:
        # Prepare documents for cross-encoder
        documents = [s['text'] for s in snippets]
        
        # Rerank using cross-encoder
        scores = model_manager.rerank(question, documents)
        
        # Sort by reranking score
        ranked = sorted(
            zip(scores, snippets),
            key=lambda x: x[0],
            reverse=True
        )
        
        return [snippet for score, snippet in ranked[:top_k]]
        
    except Exception as e:
        logger.error(f"Reranking failed: {e}, using original order")
        return snippets[:top_k]


def generate_answer_with_flan(question: str, context_snippets: List[Dict[str, Any]]) -> str:
    """Generate answer using Flan-T5"""
    if not context_snippets:
        return "I couldn't find relevant information in the thread."
    
    try:
        # Build context from snippets
        context_parts = []
        for i, snippet in enumerate(context_snippets[:3], 1):
            context_parts.append(f"[{i}] {snippet['text'][:200]}")
        
        context = "\n".join(context_parts)
        
        # Build prompt for Flan-T5
        prompt = f"""Answer the question based on the context below.

Context:
{context}

Question: {question}

Answer:"""
        
        # Generate with Flan-T5
        answer = model_manager.generate_text(prompt, max_new_tokens=150)
        
        # Clean up answer
        answer = answer.strip()
        
        # Remove common artifacts
        if answer.startswith("Answer:"):
            answer = answer[7:].strip()
        
        # If answer is too short or seems invalid, use extractive fallback
        if len(answer) < 10 or answer.lower() in ['yes', 'no', 'unknown']:
            # Extractive fallback: return most relevant snippet
            return context_snippets[0]['text'][:200] + "..."
        
        return answer
        
    except Exception as e:
        logger.error(f"Answer generation failed: {e}")
        # Extractive fallback
        return context_snippets[0]['text'][:200] + "..."


async def answer_question(question: str, thread: ThreadData) -> ChatbotQAResponse:
    """Answer question using RAG pipeline: MiniLM retrieval → cross-encoder rerank → Flan-T5 generation"""
    index = build_index(thread)
    
    if not index:
        return ChatbotQAResponse(
            answer="No content found in this thread.",
            sources=[]
        )
    
    # Step 1: Semantic retrieval with MiniLM
    retrieved_snippets = retrieve_snippets(question, index, top_k=RETRIEVAL_TOP_K)
    
    if not retrieved_snippets:
        return ChatbotQAResponse(
            answer="I couldn't find relevant information in the thread.",
            sources=[]
        )
    
    # Step 2: Rerank with cross-encoder
    reranked_snippets = rerank_snippets(question, retrieved_snippets, top_k=RERANK_TOP_K)
    
    # Step 3: Generate answer with Flan-T5
    answer = generate_answer_with_flan(question, reranked_snippets)
    
    # Extract sources
    sources = []
    seen_ids = set()
    for snippet in reranked_snippets:
        msg_id = snippet['message_id']
        if msg_id not in seen_ids:
            sources.append(msg_id)
            seen_ids.add(msg_id)
    
    return ChatbotQAResponse(
        answer=answer,
        sources=sources[:3]  # Limit to top 3 sources
    )
