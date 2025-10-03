import re
from typing import List, Dict, Any
from app.core.llm import llm_provider


async def summarize_thread(messages: List[Dict[str, Any]]) -> str:
    if llm_provider.api_key:
        return await llm_provider.summarize_map_reduce(messages)
    else:
        return rule_based_summary(messages)


def rule_based_summary(messages: List[Dict[str, Any]]) -> str:
    if not messages:
        return "Empty thread."
    
    first_msg = messages[0]
    last_msg = messages[-1]
    
    imperative_verbs = ['finalize', 'submit', 'schedule', 'prepare', 'review', 'complete', 'update', 'send', 'create']
    
    key_sentences = []
    
    for msg in [first_msg, last_msg]:
        body = msg.get('clean_body', msg.get('body', ''))
        sentences = re.split(r'[.!?]\s+', body)
        
        for sentence in sentences:
            for verb in imperative_verbs:
                if verb in sentence.lower():
                    key_sentences.append(sentence.strip())
                    break
    
    if not key_sentences:
        subject = first_msg.get('subject', 'Discussion')
        return f"{subject}. Thread involves {len(messages)} messages."
    
    summary = ' '.join(key_sentences[:3])
    
    if len(summary) > 200:
        summary = summary[:197] + "..."
    
    return summary
