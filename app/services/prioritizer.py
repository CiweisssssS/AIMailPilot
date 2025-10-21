from typing import List, Dict, Any
import json
import logging
from app.models.schemas import Priority, Task, PersonalizedKeyword
from app.services.feature_extractor import extract_features, format_features_for_llm
from app.core.llm import llm_provider
from app.core.prompts import PRIORITIZATION_PROMPT

logger = logging.getLogger(__name__)


async def calculate_priority(
    messages: List[Dict[str, Any]],
    tasks: List[Task],
    personalized_keywords: List[PersonalizedKeyword]
) -> Priority:
    """
    Hybrid prioritization: Rule-based feature extraction + GPT-4o-mini decision
    
    Args:
        messages: List of email message dicts
        tasks: Extracted tasks (not currently used, reserved for future)
        personalized_keywords: User keywords (not currently used, reserved for future)
    
    Returns:
        Priority object with label, score, and reasons
    """
    
    # Step 1: Extract rule-based features (0-1 values)
    features = extract_features(messages)
    
    # Step 2: Prepare email content for LLM
    combined_text = ""
    for msg in messages:
        subject = msg.get('subject', '')
        body = msg.get('clean_body', msg.get('body', ''))
        sender = msg.get('from_', 'Unknown')
        combined_text += f"From: {sender}\nSubject: {subject}\n{body}\n\n"
    
    # Limit text length to avoid token limits
    if len(combined_text) > 3000:
        combined_text = combined_text[:3000] + "... [truncated]"
    
    # Step 3: Format features for LLM context
    features_text = format_features_for_llm(features)
    
    # Step 4: Call GPT-4o-mini for final classification
    llm_messages = [
        {"role": "system", "content": PRIORITIZATION_PROMPT},
        {"role": "user", "content": f"{features_text}\n\n**Email Content:**\n{combined_text}"}
    ]
    
    try:
        response = await llm_provider._call_openai(llm_messages, temperature=0.3)
        
        # Parse JSON response
        response_clean = response.strip()
        if '```json' in response_clean:
            response_clean = response_clean.split('```json')[1].split('```')[0].strip()
        elif '```' in response_clean:
            response_clean = response_clean.split('```')[1].split('```')[0].strip()
        
        result = json.loads(response_clean)
        
        priority_label = result.get('priority', 'P3')
        reason = result.get('reason', 'LLM classification')
        
        # Map priority to score
        score_map = {"P1": 0.85, "P2": 0.55, "P3": 0.25}
        score = score_map.get(priority_label, 0.5)
        
        logger.info(f"GPT-4o-mini classified as {priority_label}: {reason}")
        
        return Priority(
            label=priority_label,
            score=score,
            reasons=[reason]
        )
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response as JSON: {e}, using fallback")
    except Exception as e:
        logger.error(f"LLM prioritization failed: {e}, using fallback")
    
    # Fallback: Use rule-based scoring if LLM fails
    return _fallback_priority(features)


def _fallback_priority(features: Dict[str, float]) -> Priority:
    """
    Fallback rule-based prioritization using weighted scoring
    """
    score = (
        0.40 * features["deadline_proximity"]
        + 0.25 * features["urgent_terms"]
        + 0.20 * features["request_terms"]
        + 0.10 * features["sender_weight"]
        + 0.05 * features["direct_recipient"]
        - 0.15 * features["deescalators"]
        - 0.20 * features["noise_signals"]
    )
    
    score = max(0.0, min(1.0, score))
    
    if score >= 0.75:
        label = "P1"
        reason = "High urgency based on deadline and urgent terms"
    elif score >= 0.45:
        label = "P2"
        reason = "Action required based on request terms"
    else:
        label = "P3"
        reason = "Low priority or informational content"
    
    logger.info(f"Fallback classification: {label} (score={score:.2f})")
    
    return Priority(
        label=label,
        score=round(score, 2),
        reasons=[reason]
    )
