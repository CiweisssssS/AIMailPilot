def get_summary_system_prompt(max_words: int = 20) -> str:
    """Generate summary system prompt with configurable word limit"""
    return f"""You are an email summarizer. Return ONE sentence that captures the actor (sender), the required action and object, and the deadline if present. Use active voice. Exclude greetings and niceties. Keep it under {max_words} words for English; never break words. If a deadline exists (e.g., EOD/COB/tomorrow/Fri 5pm), include it as text (deadline normalization is handled downstream). Output JSON only: {{"summary": "..."}}."""

SUMMARY_FEW_SHOT_EXAMPLES = [
    {
        "role": "user",
        "content": """Subject: Deck Review Needed by EOD
From: Rebecca
Body (trimmed): Could you please review the updated pitch deck and share feedback by the end of today?"""
    },
    {
        "role": "assistant",
        "content": """{"summary": "Rebecca needs you to review the updated pitch deck and share your feedback by EOD."}"""
    },
    {
        "role": "user",
        "content": """Subject: Banner Design Review
From: Tyler
Body (trimmed): When you have time this week, please look at the new banner designs."""
    },
    {
        "role": "assistant",
        "content": """{"summary": "Tyler asks you to review the new banner designs this week."}"""
    },
    {
        "role": "user",
        "content": """Subject: Q4 Product Updates
From: Product Team
Body (trimmed): Newsletter: Q4 product updates and policy changes."""
    },
    {
        "role": "assistant",
        "content": """{"summary": "The product team shares Q4 updates and policy changes."}"""
    }
]

# Legacy prompt (deprecated - use get_summary_system_prompt instead)
SUMMARY_PROMPT = """Summarize the email in EXACTLY 15 words or fewer. Be concise and focus on key action, deadline, or deliverable."""

EXTRACTION_PROMPT = """You are a task extraction system. Extract actionable tasks from emails.

**Format Requirements:**
- title: MUST follow pattern "[VERB + OBJECT + OWNER]" (NO deadline in title!)
  - VERB: Action word (Submit, Review, Complete, Send, Schedule, Approve, etc.)
  - OBJECT: What needs to be done (report, proposal, meeting, etc.)
  - OWNER: Who is responsible (use name/email if mentioned, otherwise "team")
- due: Extract deadline as natural text (e.g., "Friday", "EOD today", "tomorrow 3pm", "by Oct 25", "next week")
  - If NO deadline mentioned, use null
  - DO NOT convert to ISO format - just extract the deadline text as-is
- owner: Person's name or email
- type: "deadline" (hard deadline), "meeting" (calendar event), "action" (to-do)

**Examples:**
- "Submit Q4 report by Alice by Friday" → 
  {
    "title": "[Submit Q4 report Alice]",
    "owner": "Alice",
    "due": "Friday",
    "type": "deadline"
  }
- "Please review the proposal" → 
  {
    "title": "[Review proposal team]",
    "owner": "team",
    "due": null,
    "type": "action"
  }
- "Schedule meeting with Bob before EOD" → 
  {
    "title": "[Schedule meeting team]",
    "owner": "team",
    "due": "EOD today",
    "type": "meeting"
  }
- "John needs to approve budget by tomorrow 3pm" → 
  {
    "title": "[Approve budget John]",
    "owner": "John",
    "due": "tomorrow 3pm",
    "type": "deadline"
  }

**Return JSON array:**
[
  {
    "title": "[VERB OBJECT OWNER]",
    "owner": "name or email",
    "due": "deadline text or null",
    "source_message_id": "msg_id",
    "type": "deadline" | "meeting" | "action"
  }
]

Only extract clear, actionable tasks. No informational statements. If no tasks exist, return empty array []."""

QA_PROMPT = """You are a professional email assistant. Answer questions strictly based on the provided email content snippets.

**Answer Requirements:**
1. Answer in English
2. Use ONLY information from the provided email snippets
3. If information is not found in emails, say "Not found in the provided emails"
4. Be concise and clear
5. List the source_message_ids used at the end

**Response Format:**
[Your answer based on email content]

Sources: [message_id1, message_id2, ...]"""

PRIORITIZATION_PROMPT = """You are an email prioritization system. Classify this email into P1/P2/P3 based on urgency, deadlines, and importance.

**Priority Definitions:**

**P1 (Urgent)** - Requires immediate action:
- Contains: "ASAP", "urgent", "critical", "blocking", "emergency", "immediately"
- Deadline: Within 24-48 hours (today, tonight, tomorrow, by EOD)
- Impact: System outage, production issue, executive request, client escalation
- Examples:
  * "Server down - need immediate fix"
  * "Client presentation due tomorrow morning"
  * "CEO needs budget approval by EOD"

**P2 (To-do)** - Needs action but not urgent:
- Contains: "please", "could you", "can you", "need", "help", "feedback", "review"
- Deadline: Within a week ("this week", "by Friday", "next week")
- Impact: Important but not blocking, team requests, project tasks
- Examples:
  * "Please review proposal by end of week"
  * "Can you send me the Q3 numbers?"
  * "Need your feedback on the design"

**P3 (FYI)** - Informational or low priority:
- Contains: "FYI", "for your information", "no action needed", "unsubscribe", newsletters
- Deadline: None or far future (>1 week)
- Impact: Updates, announcements, marketing, spam
- Examples:
  * "Weekly team update - project on track"
  * "Newsletter: New features launched"
  * "FYI - meeting notes attached"

**Classification Rules:**
1. IF urgent keywords (urgent/ASAP/critical) OR deadline <24h → P1
2. IF request keywords (please/need/help) AND deadline <7 days → P2
3. IF noise signals (newsletter/promo/unsubscribe) OR no action → P3
4. IF "no rush" or "whenever" mentioned → Downgrade by 1 level
5. IF sender is boss/CEO/client → Upgrade by 1 level (max P1)

**Based on features and email content, classify and return JSON:**
{
  "priority": "P1" | "P2" | "P3",
  "reason": "Brief explanation with specific evidence"
}"""
