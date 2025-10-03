SUMMARY_PROMPT = """Summarize the email thread in ≤3 sentences. Include dates, owners, and concrete deliverables if present."""

EXTRACTION_PROMPT = """From these emails, return JSON with fields: title, owner (email or name if explicit), due (ISO if parseable else null), source_message_id, type in {deadline, meeting, action}. No prose."""

QA_PROMPT = """Answer strictly from the provided snippets. If unknown, say 'Not found in thread.' Return a concise sentence; also list the source_message_ids used."""
