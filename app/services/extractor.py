"""
Task Extractor Service - Extract tasks using MiniLM + NER + optional Flan-T5
"""

import re
import json
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from dateutil import parser as date_parser
from app.core.model_manager import model_manager
from app.models.schemas import Task
import logging

logger = logging.getLogger(__name__)

# Action verbs indicating tasks
ACTION_VERBS = [
    'finalize', 'submit', 'schedule', 'prepare', 'review', 'complete', 
    'update', 'send', 'create', 'deliver', 'approve', 'confirm', 'fix'
]

# Task intent embeddings (computed once)
TASK_INTENT_PHRASES = [
    "please complete this task",
    "action item to do",
    "deadline for submission",
    "meeting scheduled",
    "review required"
]


def parse_date_from_text(text: str, reference_date: Optional[datetime] = None) -> Optional[str]:
    """Enhanced date parsing with custom EOD/COB vocabulary"""
    if reference_date is None:
        reference_date = datetime.now()
    
    text_lower = text.lower()
    
    # EOD/COB patterns
    if any(term in text_lower for term in ['eod', 'end of day', 'cob', 'close of business']):
        day_match = re.search(r'(mon|tue|wed|thu|fri|sat|sun|today|tomorrow)\w*', text_lower)
        if day_match:
            day_str = day_match.group(0)
            
            if 'today' in day_str:
                return reference_date.replace(hour=17, minute=0, second=0).isoformat()
            elif 'tomorrow' in day_str:
                tomorrow = reference_date + timedelta(days=1)
                return tomorrow.replace(hour=17, minute=0, second=0).isoformat()
            else:
                days = {'mon': 0, 'tue': 1, 'wed': 2, 'thu': 3, 'fri': 4, 'sat': 5, 'sun': 6}
                for key, val in days.items():
                    if day_str.startswith(key):
                        target_day = val
                        current_day = reference_date.weekday()
                        days_ahead = (target_day - current_day) % 7
                        if days_ahead == 0:
                            days_ahead = 7
                        target_date = reference_date + timedelta(days=days_ahead)
                        return target_date.replace(hour=17, minute=0, second=0).isoformat()
    
    # Try dateutil parser
    try:
        parsed_date = date_parser.parse(text, fuzzy=True)
        if parsed_date:
            return parsed_date.isoformat()
    except:
        pass
    
    return None


def extract_owner_with_ner(text: str, entities: List[Dict[str, Any]]) -> str:
    """Extract owner using NER entities + rule-based fallback"""
    
    # First try NER-detected persons - join multi-token entities
    person_tokens = []
    for entity in entities:
        if entity.get('entity_group') in ['PER', 'PERSON']:
            person_tokens.append(entity['word'].strip())
    
    if person_tokens:
        # Join tokens (e.g., ["Alex", "Johnson"] -> "Alex Johnson")
        return ' '.join(person_tokens)
    
    # Fallback to rules
    text_lower = text.lower()
    
    if 'you' in text_lower or 'your' in text_lower:
        return 'you'
    
    # Email pattern
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(email_pattern, text)
    if emails:
        return emails[0]
    
    # Name pattern (capture full names)
    name_pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(?:owns|responsible|assigned|will|should)\b'
    names = re.findall(name_pattern, text)
    if names:
        return names[0]
    
    # Check for organizations - join tokens
    org_tokens = []
    for entity in entities:
        if entity.get('entity_group') in ['ORG', 'ORGANIZATION']:
            org_tokens.append(entity['word'].strip())
    
    if org_tokens:
        return ' '.join(org_tokens)
    
    return 'team'


def select_candidate_sentences(
    text: str, 
    subject: str = "", 
    top_k: int = 5
) -> List[Tuple[str, int, int]]:
    """
    Select candidate sentences using MiniLM embeddings + subject context
    Returns: [(sentence, start_offset, end_offset), ...]
    """
    sentences = re.split(r'[.!?]\s+', text)
    if not sentences:
        return []
    
    # Filter out very short sentences
    valid_sentences = []
    offsets = []
    current_pos = 0
    
    for sentence in sentences:
        sentence = sentence.strip()
        if len(sentence) > 10:  # Minimum length
            start = text.find(sentence, current_pos)
            if start == -1:  # Sentence not found, estimate
                start = current_pos
            end = start + len(sentence)
            valid_sentences.append(sentence)
            offsets.append((start, end))
            current_pos = end
    
    if not valid_sentences:
        return []
    
    try:
        # Build intent context (include subject if available)
        intent_texts = TASK_INTENT_PHRASES.copy()
        if subject:
            intent_texts.append(subject)
        
        # Compute task intent embedding
        intent_embeddings = model_manager.embed_texts(intent_texts)
        
        # Check for zero vectors (model failure)
        if all(sum(emb) == 0 for emb in intent_embeddings):
            raise ValueError("MiniLM returned zero vectors")
        
        intent_vec = [sum(col)/len(col) for col in zip(*intent_embeddings)]
        
        # Embed candidate sentences
        sentence_embeddings = model_manager.embed_texts(valid_sentences)
        
        # Check for zero vectors
        if all(sum(emb) == 0 for emb in sentence_embeddings):
            raise ValueError("MiniLM returned zero vectors for sentences")
        
        # Compute cosine similarity
        def cosine_sim(a, b):
            dot = sum(x*y for x,y in zip(a,b))
            norm_a = (sum(x**2 for x in a))**0.5
            norm_b = (sum(x**2 for x in b))**0.5
            if norm_a < 1e-9 or norm_b < 1e-9:
                return 0.0
            return dot / (norm_a * norm_b)
        
        scores = [cosine_sim(intent_vec, emb) for emb in sentence_embeddings]
        
        # Sort by score
        ranked = sorted(
            zip(valid_sentences, offsets, scores), 
            key=lambda x: x[2], 
            reverse=True
        )
        
        # Return top-k with offsets
        result = [(sent, start, end) for (sent, (start, end), score) in ranked[:top_k]]
        return result
        
    except Exception as e:
        logger.error(f"Semantic selection failed: {e}, using rule-based")
        # Fallback: sentences with action verbs
        action_sentences = []
        for sent, (start, end) in zip(valid_sentences, offsets):
            if any(verb in sent.lower() for verb in ACTION_VERBS):
                action_sentences.append((sent, start, end))
        return action_sentences[:top_k]


def extract_with_models(text: str, subject: str = "") -> List[Dict[str, Any]]:
    """
    Extract tasks using MiniLM + NER + optional Flan-T5
    Returns list of task dicts
    """
    # Step 1: Select candidate sentences
    candidates = select_candidate_sentences(text, subject, top_k=5)
    
    if not candidates:
        return []
    
    tasks = []
    
    for sentence, start, end in candidates:
        # Step 2: NER for entities
        try:
            entities = model_manager.extract_entities(sentence)
        except:
            entities = []
        
        # Step 3: Extract owner using NER
        owner = extract_owner_with_ner(sentence, entities)
        
        # Step 4: Parse date
        due_iso = parse_date_from_text(sentence)
        
        # Step 5: Optional Flan-T5 for structured output
        title = sentence.strip()[:100]  # Default title
        
        try:
            # Construct prompt for Flan-T5
            prompt = f"""Extract the main action from this task:
"{sentence}"

Return only the action verb and object (e.g., "submit report", "schedule meeting").
Action:"""
            
            generated = model_manager.generate_text(prompt, max_new_tokens=20)
            if generated and len(generated.strip()) > 3:
                title = generated.strip()
        except:
            pass
        
        # Build task dict
        task = {
            "title": title,
            "owner": owner,
            "due_iso": due_iso,
            "source_span": {"start": start, "end": end}
        }
        tasks.append(task)
    
    return tasks


def rule_based_extraction(text: str, subject: str = "") -> List[Dict[str, Any]]:
    """
    Rule-based fallback extraction
    Returns list of task dicts matching endpoint schema
    """
    sentences = re.split(r'[.!?]\s+', text)
    tasks = []
    current_pos = 0
    
    for sentence in sentences:
        sentence = sentence.strip()
        sentence_lower = sentence.lower()
        
        # Check for action verbs or meeting
        has_action = any(verb in sentence_lower for verb in ACTION_VERBS)
        
        if has_action or 'meeting' in sentence_lower:
            # Find position in original text
            start = text.find(sentence, current_pos)
            if start == -1:
                # Sentence not found exactly, estimate position
                start = max(0, current_pos)
            end = start + len(sentence)
            current_pos = end
            
            due_iso = parse_date_from_text(sentence)
            owner = extract_owner_with_ner(sentence, [])  # No NER entities in fallback
            
            title = sentence[:100]
            
            tasks.append({
                "title": title,
                "owner": owner,
                "due_iso": due_iso,
                "source_span": {"start": max(0, start), "end": end}  # Ensure valid span
            })
    
    return tasks


async def extract_tasks_from_text(text: str, subject: str = "") -> Dict[str, Any]:
    """
    Main extraction function matching endpoint contract
    
    Input: { text: string, subject?: string }
    Output: { tasks: [{ title, owner, due_iso, source_span }] }
    """
    if not text:
        return {"tasks": []}
    
    try:
        # Try model-based extraction first
        tasks = extract_with_models(text, subject)
        
        if tasks:
            logger.info(f"Extracted {len(tasks)} tasks using models")
            return {"tasks": tasks}
        else:
            logger.warning("Model extraction returned no tasks, using fallback")
            raise ValueError("No tasks from models")
            
    except Exception as e:
        logger.error(f"Model extraction failed: {e}, using rule-based fallback")
    
    # Fallback to rule-based
    tasks = rule_based_extraction(text, subject)
    logger.info(f"Extracted {len(tasks)} tasks using rule-based fallback")
    
    return {"tasks": tasks[:10]}  # Limit to 10 tasks


async def extract_tasks(messages: List[Dict[str, Any]]) -> List[Task]:
    """
    Legacy function for backward compatibility
    Extracts tasks from message list and returns Task objects
    """
    if not messages:
        return []
    
    # Combine text from messages
    text_parts = []
    for msg in messages:
        body = msg.get('clean_body', msg.get('body', ''))
        if body:
            text_parts.append(body)
    
    combined_text = ' '.join(text_parts)
    subject = messages[0].get('subject', '') if messages else ""
    
    # Call new extraction function
    result = await extract_tasks_from_text(combined_text, subject)
    
    # Convert to Task objects
    tasks = []
    for task_dict in result['tasks']:
        try:
            task = Task(
                title=task_dict['title'],
                owner=task_dict['owner'],
                due=task_dict.get('due_iso'),
                source_message_id=messages[0].get('id', 'unknown') if messages else 'unknown',
                type="action"  # Default type
            )
            tasks.append(task)
        except Exception as e:
            logger.error(f"Failed to create Task object: {e}")
            continue
    
    return tasks[:10]
