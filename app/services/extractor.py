import re
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dateutil import parser as date_parser
from app.core.llm import llm_provider
from app.models.schemas import Task


ACTION_VERBS = ['finalize', 'submit', 'schedule', 'prepare', 'review', 'complete', 'update', 'send', 'create', 'deliver']


def parse_date_from_text(text: str, reference_date: Optional[datetime] = None) -> Optional[str]:
    if reference_date is None:
        reference_date = datetime.now()
    
    text_lower = text.lower()
    
    if 'eod' in text_lower or 'end of day' in text_lower:
        match = re.search(r'(mon|tue|wed|thu|fri|sat|sun)\w*', text_lower)
        if match:
            day_name = match.group(0)
            days = {'mon': 0, 'tue': 1, 'wed': 2, 'thu': 3, 'fri': 4, 'sat': 5, 'sun': 6}
            for key, val in days.items():
                if day_name.startswith(key):
                    target_day = val
                    current_day = reference_date.weekday()
                    days_ahead = (target_day - current_day) % 7
                    if days_ahead == 0:
                        days_ahead = 7
                    target_date = reference_date + timedelta(days=days_ahead)
                    return target_date.replace(hour=23, minute=59, second=0).isoformat()
    
    time_patterns = [
        r'(\d{1,2})\s*(am|pm)',
        r'(\d{1,2}):(\d{2})\s*(am|pm)?',
    ]
    
    for pattern in time_patterns:
        match = re.search(pattern, text_lower)
        if match:
            try:
                day_match = re.search(r'(mon|tue|wed|thu|fri|sat|sun)\w*', text_lower)
                if day_match:
                    day_name = day_match.group(0)
                    days = {'mon': 0, 'tue': 1, 'wed': 2, 'thu': 3, 'fri': 4, 'sat': 5, 'sun': 6}
                    for key, val in days.items():
                        if day_name.startswith(key):
                            target_day = val
                            current_day = reference_date.weekday()
                            days_ahead = (target_day - current_day) % 7
                            if days_ahead == 0:
                                days_ahead = 7
                            target_date = reference_date + timedelta(days=days_ahead)
                            
                            hour = int(match.group(1))
                            if len(match.groups()) > 2 and match.group(3):
                                if match.group(3).lower() == 'pm' and hour < 12:
                                    hour += 12
                                elif match.group(3).lower() == 'am' and hour == 12:
                                    hour = 0
                            
                            minute = int(match.group(2)) if len(match.groups()) > 1 and match.group(2) else 0
                            
                            return target_date.replace(hour=hour, minute=minute, second=0).isoformat()
            except:
                pass
    
    try:
        parsed_date = date_parser.parse(text, fuzzy=True)
        return parsed_date.isoformat()
    except:
        pass
    
    return None


def extract_owner(text: str, message: Dict[str, Any]) -> str:
    text_lower = text.lower()
    
    if 'you' in text_lower:
        recipients = message.get('to', [])
        if len(recipients) == 1:
            return recipients[0]
        return 'you'
    
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(email_pattern, text)
    if emails:
        return emails[0]
    
    name_pattern = r'\b([A-Z][a-z]+)\s+(?:owns|responsible|assigned|will)\b'
    names = re.findall(name_pattern, text)
    if names:
        return names[0]
    
    return 'team'


def rule_based_extraction(messages: List[Dict[str, Any]]) -> List[Task]:
    tasks = []
    
    for msg in messages:
        body = msg.get('clean_body', msg.get('body', ''))
        sentences = re.split(r'[.!?]\s+', body)
        
        for sentence in sentences:
            sentence_lower = sentence.lower()
            
            has_action = any(verb in sentence_lower for verb in ACTION_VERBS)
            
            if has_action or 'meeting' in sentence_lower:
                due_date = parse_date_from_text(sentence, datetime.now())
                owner = extract_owner(sentence, msg)
                
                task_type = "action"
                if 'meeting' in sentence_lower:
                    task_type = "meeting"
                elif due_date and ('deadline' in sentence_lower or 'due' in sentence_lower or 'eod' in sentence_lower):
                    task_type = "deadline"
                
                title = sentence.strip()[:100]
                
                task = Task(
                    title=title,
                    owner=owner,
                    due=due_date,
                    source_message_id=msg.get('id', 'unknown'),
                    type=task_type
                )
                tasks.append(task)
    
    return tasks


async def extract_tasks(messages: List[Dict[str, Any]]) -> List[Task]:
    rule_tasks = rule_based_extraction(messages)
    
    if llm_provider.api_key and len(messages) > 0:
        try:
            llm_tasks_data = await llm_provider.extract_tasks(messages)
            llm_tasks = [Task(**task_data) for task_data in llm_tasks_data if all(k in task_data for k in ['title', 'owner', 'source_message_id', 'type'])]
            
            if llm_tasks:
                return llm_tasks
        except Exception:
            pass
    
    return rule_tasks[:10]
