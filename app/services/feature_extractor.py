from typing import Dict, List, Any
import re
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# Feature lexicons
DEADLINE_TERMS = [
    r'by\s+eod', r'by\s+end\s+of\s+day', r'\bcob\b', r'\btoday\b', r'\btonight\b',
    r'\btomorrow\b', r'next\s+week', r'this\s+week', r'by\s+\d{1,2}[:/]\d{1,2}',
    r'\bdue\b', r'\bdeadline\b', r'\bcutoff\b', r'\bsla\b', r'due\s+date',
    r'by\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)',
    r'within\s+\d+\s+(hour|day|week)s?'
]

URGENT_TERMS = [
    r'\burgent\b', r'\basap\b', r'\bimmediately\b', r'\bcritical\b',
    r'time[- ]sensitive', r'right\s+away', r'\bblocking\b', r'\bblocker\b',
    r'\boutage\b', r'\bescalate\b', r'sev[- ]?1', r'\bp0\b', r'\bp1\b',
    r'\bemergency\b', r'\bhigh\s+priority\b', r'need\s+this\s+now'
]

REQUEST_TERMS = [
    r'\bplease\b', r'could\s+you', r'can\s+you', r'would\s+you', r'\bkindly\b',
    r'help\s+me', r'\bassist\b', r'\bconfirm\b', r'\bapproval\b', r'sign\s+off',
    r'\badvise\b', r'\bfeedback\b', r'let\s+me\s+know', r'set\s+up',
    r'\bschedule\b', r'\bbook\b', r'\barrange\b', r'calendar\s+invite',
    r'join\s+call', r'\bbrainstorm\b', r'need\s+your', r'waiting\s+for'
]

DEESCALATOR_TERMS = [
    r'no\s+rush', r'\bwhenever\b', r'not\s+urgent', r'at\s+your\s+convenience',
    r'when\s+you\s+(get\s+)?a\s+chance', r'no\s+hurry', r'take\s+your\s+time',
    r'fyi\s+only', r'just\s+fyi'
]

NOISE_TERMS = [
    r'\bunsubscribe\b', r'%\s*off', r'\bsale\b', r'\bpromotion\b',
    r'\bnewsletter\b', r'privacy\s+policy', r'\bmarketing\b', r'\bcoupon\b',
    r'click\s+here', r'limited\s+time', r'act\s+now', r'free\s+shipping',
    r'special\s+offer', r'discount'
]


def extract_features(messages: List[Dict[str, Any]]) -> Dict[str, float]:
    """
    Extract rule-based features from email messages.
    Returns a dict with feature names and 0-1 values.
    """
    features = {
        "deadline_proximity": 0.0,
        "urgent_terms": 0.0,
        "request_terms": 0.0,
        "deescalators": 0.0,
        "noise_signals": 0.0,
        "sender_weight": 0.0,
        "direct_recipient": 0.0
    }
    
    # Combine all text from messages
    combined_text = ""
    senders = []
    recipients = []
    
    for msg in messages:
        subject = msg.get('subject', '')
        body = msg.get('clean_body', msg.get('body', ''))
        combined_text += f"{subject} {body} "
        
        sender = msg.get('from_', '').lower()
        senders.append(sender)
        
        to_field = msg.get('to', '').lower()
        recipients.append(to_field)
    
    combined_text = combined_text.lower()
    
    # 1. Deadline proximity (0-1)
    deadline_score = 0.0
    for pattern in DEADLINE_TERMS:
        if re.search(pattern, combined_text, re.IGNORECASE):
            # Check for specific temporal indicators
            if re.search(r'by\s+eod|by\s+end\s+of\s+day|\btoday\b|\btonight\b', combined_text, re.IGNORECASE):
                deadline_score = max(deadline_score, 1.0)  # <24h
            elif re.search(r'\btomorrow\b', combined_text, re.IGNORECASE):
                deadline_score = max(deadline_score, 0.8)  # 24-48h
            elif re.search(r'this\s+week|next\s+week', combined_text, re.IGNORECASE):
                deadline_score = max(deadline_score, 0.5)  # 48-72h
            else:
                deadline_score = max(deadline_score, 0.3)  # generic deadline
    
    features["deadline_proximity"] = deadline_score
    
    # 2. Urgent terms (0-1)
    urgent_count = 0
    for pattern in URGENT_TERMS:
        if re.search(pattern, combined_text, re.IGNORECASE):
            urgent_count += 1
    
    if urgent_count >= 2:
        features["urgent_terms"] = 1.0  # strong hit
    elif urgent_count == 1:
        features["urgent_terms"] = 0.5  # weak hit
    
    # 3. Request terms (0-1)
    request_count = 0
    for pattern in REQUEST_TERMS:
        if re.search(pattern, combined_text, re.IGNORECASE):
            request_count += 1
    
    if request_count >= 3:
        features["request_terms"] = 0.8  # explicit request
    elif request_count >= 1:
        features["request_terms"] = 0.4  # mild request
    
    # 4. De-escalators (0-1)
    for pattern in DEESCALATOR_TERMS:
        if re.search(pattern, combined_text, re.IGNORECASE):
            features["deescalators"] = 1.0
            break
    
    # 5. Noise signals (0-1)
    noise_count = 0
    for pattern in NOISE_TERMS:
        if re.search(pattern, combined_text, re.IGNORECASE):
            noise_count += 1
    
    if noise_count >= 2:
        features["noise_signals"] = 1.0
    elif noise_count == 1:
        features["noise_signals"] = 0.5
    
    # 6. Sender weight (0-1)
    boss_domains = ['ceo', 'boss', 'manager', 'director', 'vp', 'chief', 'president']
    client_domains = ['client', 'customer']
    
    for sender in senders:
        for domain in boss_domains + client_domains:
            if domain in sender:
                features["sender_weight"] = 1.0
                break
        if features["sender_weight"] == 1.0:
            break
    
    if features["sender_weight"] == 0.0:
        features["sender_weight"] = 0.3  # default for other senders
    
    # 7. Direct recipient (0-1)
    # This would require knowing the user's email, for now use heuristic
    for to_field in recipients:
        if to_field and '@' in to_field:
            # If there's a single recipient, likely direct
            if to_field.count('@') == 1:
                features["direct_recipient"] = 1.0
                break
            else:
                features["direct_recipient"] = 0.3  # CC/multiple
    
    if features["direct_recipient"] == 0.0:
        features["direct_recipient"] = 0.5  # default
    
    return features


def format_features_for_llm(features: Dict[str, float]) -> str:
    """
    Format extracted features as human-readable text for LLM context.
    """
    lines = [
        "**Extracted Features (Rule-Based Analysis):**",
        f"- Deadline Proximity: {features['deadline_proximity']:.2f} (0=none, 1=<24h)",
        f"- Urgent Terms: {features['urgent_terms']:.2f} (0=none, 1=strong)",
        f"- Request Terms: {features['request_terms']:.2f} (0=none, 1=explicit)",
        f"- De-escalators: {features['deescalators']:.2f} (0=none, 1=present)",
        f"- Noise Signals: {features['noise_signals']:.2f} (0=none, 1=spam/newsletter)",
        f"- Sender Weight: {features['sender_weight']:.2f} (0.3=normal, 1.0=boss/client)",
        f"- Direct Recipient: {features['direct_recipient']:.2f} (0.3=CC, 1.0=direct)"
    ]
    return "\n".join(lines)
