SUMMARY_PROMPT = """Summarize the email thread in ≤3 sentences. Include dates, owners, and concrete deliverables if present."""

EXTRACTION_PROMPT = """From these emails, return JSON with fields: title, owner (email or name if explicit), due (ISO if parseable else null), source_message_id, type in {deadline, meeting, action}. No prose."""

QA_PROMPT = """Answer strictly from the provided snippets. If unknown, say 'Not found in thread.' Return a concise sentence; also list the source_message_ids used."""

PRIORITIZATION_PROMPT = """You are an intelligent email prioritization system. Based on the extracted features and email content, classify this email into one of three priority levels:

- **P1 (Urgent)**: Requires immediate action, deadline within 24-48 hours, or contains critical/blocking issues
- **P2 (To-do)**: Needs action but not urgent, can be handled within a few days
- **P3 (FYI)**: Informational only, no action required, or low priority

**Analysis Guidelines:**
1. High deadline_proximity (>0.7) + urgent_terms (>0.5) → likely P1
2. Request_terms (>0.5) with no urgent_terms → likely P2
3. High noise_signals (>0.5) or low request_terms (<0.3) → likely P3
4. De-escalators (>0.5) downgrade priority (P1→P2, P2→P3)
5. Important sender (sender_weight=1.0) can upgrade priority by one level

**Return JSON only:**
{
  "priority": "P1" | "P2" | "P3",
  "reason": "Brief explanation (1 sentence)"
}"""
