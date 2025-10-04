from typing import List, Dict, Any
from datetime import datetime, timedelta
from rapidfuzz import fuzz
from app.models.schemas import Priority, Task, PersonalizedKeyword


BOSS_DOMAINS = ['ceo', 'boss', 'manager', 'director']
CLIENT_DOMAINS = ['client', 'customer']


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
    
    weight_map = {"High": 2.0, "Medium": 1.0, "Low": 0.5}
    
    for keyword in personalized_keywords:
        term = keyword.term.lower()
        weight_value = weight_map.get(keyword.weight, 1.0)
        scope = keyword.scope.lower()
        
        for msg in messages:
            match_found = False
            
            if 'subject' in scope:
                subject = msg.get('subject', '').lower()
                ratio = fuzz.partial_ratio(term, subject)
                if ratio > 70:
                    score += 0.1 * weight_value
                    reasons.append(f"personalized keyword hit: {term} (weight {keyword.weight})")
                    match_found = True
            
            if not match_found and 'body' in scope:
                body = msg.get('clean_body', msg.get('body', '')).lower()
                ratio = fuzz.partial_ratio(term, body)
                if ratio > 70:
                    score += 0.1 * weight_value
                    reasons.append(f"personalized keyword hit: {term} (weight {keyword.weight})")
                    match_found = True
            
            if not match_found and 'sender' in scope:
                sender = msg.get('from_', '').lower()
                ratio = fuzz.partial_ratio(term, sender)
                if ratio > 70:
                    score += 0.1 * weight_value
                    reasons.append(f"personalized keyword hit in sender: {term} (weight {keyword.weight})")
            
            if match_found:
                break
    
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
