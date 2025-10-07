from typing import List, Dict, Any
from datetime import datetime, timedelta
import logging
from app.models.schemas import Priority, Task, PersonalizedKeyword
from app.core.model_manager import model_manager

logger = logging.getLogger(__name__)

BOSS_DOMAINS = ['ceo', 'boss', 'manager', 'director']
CLIENT_DOMAINS = ['client', 'customer']

# Semantic similarity threshold for keyword matching
SEMANTIC_THRESHOLD = 0.65  # Lower than exact match but higher than random


def calculate_priority(
    messages: List[Dict[str, Any]],
    tasks: List[Task],
    personalized_keywords: List[PersonalizedKeyword]
) -> Priority:
    score = 0.0
    reasons = []
    
    now = datetime.now()
    
    for task in tasks:
        if task.due:
            try:
                due_date = datetime.fromisoformat(task.due.replace('Z', '+00:00'))
                time_diff = (due_date - now).total_seconds() / 3600
                
                if time_diff <= 24:
                    score += 0.4
                    reasons.append(f"due date within 24h ({task.title[:30]}...)")
                elif time_diff <= 72:
                    score += 0.2
                    reasons.append(f"due date within 72h ({task.title[:30]}...)")
                
                if task.type == "meeting" and time_diff <= 48:
                    score += 0.3
                    reasons.append(f"meeting within 48h ({task.title[:30]}...)")
            except:
                pass
    
    for msg in messages:
        sender = msg.get('from_', '').lower()
        
        for domain in BOSS_DOMAINS + CLIENT_DOMAINS:
            if domain in sender:
                score += 0.2
                reasons.append(f"important sender: {domain}")
                break
    
    # Semantic keyword matching with MiniLM
    weight_map = {"High": 2.0, "Medium": 1.0, "Low": 0.5}
    
    for keyword in personalized_keywords:
        term = keyword.term.lower()
        weight_value = weight_map.get(keyword.weight, 1.0)
        scope = keyword.scope.lower()
        
        try:
            # Embed keyword once
            keyword_emb = model_manager.embed_texts([term])[0]
            
            # Check for zero vector
            if sum(keyword_emb) == 0 or any(x != x for x in keyword_emb):  # NaN check
                logger.warning(f"Invalid embedding for keyword '{term}', using fallback")
                # Fallback to simple substring matching
                for msg in messages:
                    match_found = False
                    
                    if 'subject' in scope and term in msg.get('subject', '').lower():
                        score += 0.1 * weight_value
                        reasons.append(f"keyword '{term}' in subject (exact)")
                        match_found = True
                    
                    if not match_found and 'body' in scope and term in msg.get('clean_body', msg.get('body', '')).lower():
                        score += 0.1 * weight_value
                        reasons.append(f"keyword '{term}' in body (exact)")
                        match_found = True
                    
                    if not match_found and 'sender' in scope and term in msg.get('from_', '').lower():
                        score += 0.1 * weight_value
                        reasons.append(f"keyword '{term}' in sender (exact)")
                    
                    if match_found:
                        break
                continue
            
            for msg in messages:
                match_found = False
                
                if 'subject' in scope:
                    subject = msg.get('subject', '')
                    if subject:
                        subject_emb = model_manager.embed_texts([subject])[0]
                        similarity = cosine_similarity(keyword_emb, subject_emb)
                        
                        if similarity >= SEMANTIC_THRESHOLD:
                            score += 0.1 * weight_value
                            reasons.append(f"keyword '{term}' in subject (semantic {similarity:.2f})")
                            match_found = True
                
                if not match_found and 'body' in scope:
                    body = msg.get('clean_body', msg.get('body', ''))
                    if body:
                        # For long bodies, chunk into sentences and find best match
                        body_sentences = body.split('. ')[:10]  # Limit to first 10 sentences
                        body_embs = model_manager.embed_texts(body_sentences)
                        
                        max_sim = max(
                            (cosine_similarity(keyword_emb, emb) for emb in body_embs),
                            default=0.0
                        )
                        
                        if max_sim >= SEMANTIC_THRESHOLD:
                            score += 0.1 * weight_value
                            reasons.append(f"keyword '{term}' in body (semantic {max_sim:.2f})")
                            match_found = True
                
                if not match_found and 'sender' in scope:
                    sender = msg.get('from_', '')
                    if sender:
                        sender_emb = model_manager.embed_texts([sender])[0]
                        similarity = cosine_similarity(keyword_emb, sender_emb)
                        
                        if similarity >= SEMANTIC_THRESHOLD:
                            score += 0.1 * weight_value
                            reasons.append(f"keyword '{term}' in sender (semantic {similarity:.2f})")
                
                if match_found:
                    break
                    
        except Exception as e:
            logger.error(f"Semantic matching failed for keyword '{term}': {e}")
            # Silent fallback - skip this keyword
            continue
    
    score = min(score, 1.0)
    
    if score >= 0.75:
        label = "P1"
    elif score >= 0.45:
        label = "P2"
    else:
        label = "P3"
    
    if not reasons:
        reasons = ["no urgent indicators found"]
    
    return Priority(
        label=label,
        score=round(score, 2),
        reasons=reasons[:5]
    )


def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """Compute cosine similarity between two vectors"""
    if len(vec_a) != len(vec_b):
        return 0.0
    
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = (sum(a ** 2 for a in vec_a)) ** 0.5
    norm_b = (sum(b ** 2 for b in vec_b)) ** 0.5
    
    if norm_a < 1e-9 or norm_b < 1e-9:
        return 0.0
    
    return dot / (norm_a * norm_b)
