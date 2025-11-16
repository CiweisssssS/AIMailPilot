import json
import os
from typing import Any, Dict, Tuple

from ..registry import ModelClient


class AnthropicClient(ModelClient):
    def __init__(self, model: str):
        self.model = model
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise EnvironmentError("ANTHROPIC_API_KEY is not set")
        try:
            import anthropic  # type: ignore
        except Exception:
            anthropic = None  # type: ignore
        self._anthropic = anthropic
        self._client = None

    def _get_client(self):
        if self._client is None:
            if self._anthropic is None:
                raise RuntimeError("anthropic SDK not installed. pip install anthropic")
            self._client = self._anthropic.Client(api_key=self.api_key)  # type: ignore
        return self._client

    def summarize(self, email_text: str) -> Tuple[str, Dict[str, Any], float]:
        client = self._get_client()
        # Map shorthand to versioned model IDs commonly enabled in accounts
        model_id = (self.model or "").strip()
        mapping = {
            "claude-3-5-haiku": "claude-3-5-haiku-20241022",
            "claude-3-5-sonnet": "claude-3-5-sonnet-20241022",
            "claude-3-haiku": "claude-3-haiku-20240307",
            "claude-3-sonnet": "claude-3-sonnet-20240229",
        }
        model_id = mapping.get(model_id, model_id)

        system = (
            "You are an email summarization assistant. The input starts with 'Received at (UTC): <ISO>'. "
            "Use that timestamp to resolve relative time into absolute dates.\n"
            "Output STRICT JSON with keys: actor, action, object, deadline, notes.\n"
            "- actor: requester (prefer sender's name). NEVER 'you/we/our team'; null if unknown.\n"
            "- action: one concise verb phrase (send/review/approve/schedule/prepare/update...), not a full sentence.\n"
            "- object: short noun phrase.\n"
            "- deadline: YYYY-MM-DD if resolvable, else null.\n"
            "- notes: brief context or null.\n"
            "No extra fields."
        )
        user = f"Summarize the email into the required JSON fields:\n\n{email_text}"

        # Anthropic Messages API
        msg = client.messages.create(
            model=model_id,
            max_tokens=400,
            temperature=0.2,
            system=system,
            messages=[{"role": "user", "content": user + "\n\nReturn JSON only."}],
        )

        raw_text = ""
        try:
            # content is a list of blocks; take first text block
            blocks = msg.content or []
            for b in blocks:
                if getattr(b, "type", None) == "text":
                    raw_text = getattr(b, "text", "") or ""
                    if raw_text:
                        break
            if not raw_text and blocks:
                raw_text = str(blocks[0])
        except Exception:
            raw_text = ""

        try:
            summary_json = json.loads(raw_text)
        except Exception:
            summary_json = {}

        for k in ["actor", "action", "object", "deadline", "notes"]:
            summary_json.setdefault(k, None)
        dl = summary_json.get("deadline")
        if isinstance(dl, str) and "T" in dl:
            summary_json["deadline"] = dl.split("T", 1)[0]

        confidence = 0.75 if summary_json else 0.3
        return raw_text, summary_json, confidence

    def extract(self, email_text: str) -> Tuple[str, Dict[str, Any], float]:
        # Keep placeholder to avoid breaking pipeline; implement later as needed.
        raw = "TASKS_PLACEHOLDER"
        tasks_json = {"tasks": []}
        confidence = 0.5
        return raw, tasks_json, confidence


