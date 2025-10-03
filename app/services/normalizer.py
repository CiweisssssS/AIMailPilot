import re
from typing import List
from datetime import datetime
from app.models.schemas import EmailMessage, ThreadData, TimelineItem, NormalizedMessage


def strip_quoted_replies(body: str) -> str:
    lines = body.split('\n')
    cleaned_lines = []
    
    for line in lines:
        if line.strip().startswith('>'):
            continue
        
        if re.match(r'^On .+ wrote:$', line.strip()):
            break
        
        if re.match(r'^-{2,}|_{2,}', line.strip()):
            break
        
        if re.match(r'^(Best|Regards|Thanks|Sincerely|Cheers),?\s*$', line.strip(), re.IGNORECASE):
            break
        
        cleaned_lines.append(line)
    
    return '\n'.join(cleaned_lines).strip()


def normalize_thread(messages: List[EmailMessage]) -> ThreadData:
    sorted_messages = sorted(messages, key=lambda m: datetime.fromisoformat(m.date.replace('Z', '+00:00')))
    
    seen_ids = set()
    unique_messages = []
    for msg in sorted_messages:
        if msg.id not in seen_ids:
            seen_ids.add(msg.id)
            unique_messages.append(msg)
    
    participants = set()
    for msg in unique_messages:
        participants.add(msg.from_)
        participants.update(msg.to)
        participants.update(msg.cc)
    
    timeline = [
        TimelineItem(
            id=msg.id,
            date=msg.date,
            subject=msg.subject
        )
        for msg in unique_messages
    ]
    
    normalized_messages = [
        NormalizedMessage(
            id=msg.id,
            clean_body=strip_quoted_replies(msg.body)
        )
        for msg in unique_messages
    ]
    
    thread_id = unique_messages[0].thread_id if unique_messages else "unknown"
    
    return ThreadData(
        thread_id=thread_id,
        participants=sorted(list(participants)),
        timeline=timeline,
        normalized_messages=normalized_messages
    )
