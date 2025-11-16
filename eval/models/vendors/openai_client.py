import json
import os
from typing import Any, Dict, Tuple

from ..registry import ModelClient


class OpenAIClient(ModelClient):
    def __init__(self, model: str):
        # Normalize common aliases to public model IDs
        alias = (model or "").strip()
        if alias in ("gpt-4o-mini-high-throughput", "gpt-4o-mini-high", "gpt-4o-mini-ht"):
            alias = "gpt-4o-mini"
        if alias in ("gpt-4o-base", "gpt-4o (base)"):
            alias = "gpt-4o"
        self.model = alias
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise EnvironmentError("OPENAI_API_KEY is not set")
        # Lazy import to avoid hard dependency during scaffolding
        try:
            from openai import OpenAI  # type: ignore
        except Exception as e:
            OpenAI = None  # type: ignore
        self._OpenAI = OpenAI
        self._client = None

    def _get_client(self):
        if self._client is None:
            if self._OpenAI is None:
                raise RuntimeError("openai SDK not installed. pip install openai")
            self._client = self._OpenAI(api_key=self.api_key)  # type: ignore
        return self._client

    def summarize(self, email_text: str) -> Tuple[str, Dict[str, Any], float]:
        """
        Calls OpenAI (e.g., gpt-4o-mini-high-throughput) and requests strict JSON.
        """
        client = self._get_client()
        system = (
            "You are an email summarization assistant. The input starts with 'Received at (UTC): <ISO>'. "
            "Use that timestamp to resolve any relative time phrases into absolute dates.\n"
            "Output STRICT JSON with keys: actor, action, object, deadline, notes.\n"
            "- actor: the person initiating the request (prefer the sender's name). NEVER use 'you/we/our team'. If unknown, null.\n"
            "- action: ONE concise verb phrase (send/review/approve/schedule/prepare/update...). Avoid full sentences.\n"
            "- object: what the action is about, short noun phrase.\n"
            "- deadline: absolute date YYYY-MM-DD if resolvable, else null.\n"
            "- notes: brief extra context or null.\n"
            "No extra fields."
        )
        user = f"Summarize the email into the required JSON fields:\n\n{email_text}"

        # Use Responses API if available, else fallback to Chat Completions
        raw_text = ""
        summary_json: Dict[str, Any] = {}
        try:
            # Prefer chat.completions with response_format json_object
            resp = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
            )
            raw_text = resp.choices[0].message.content or ""
        except Exception:
            # Minimal fallback without response_format
            resp = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user + "\n\nReturn JSON only."},
                ],
                temperature=0.2,
            )
            raw_text = resp.choices[0].message.content or ""

        try:
            summary_json = json.loads(raw_text)
        except Exception:
            summary_json = {}

        # Normalize fields
        for k in ["actor", "action", "object", "deadline", "notes"]:
            summary_json.setdefault(k, None)
        # Normalize deadline to YYYY-MM-DD when possible
        dl = summary_json.get("deadline")
        if isinstance(dl, str):
            # Accept full ISO and truncate to date
            if "T" in dl:
                summary_json["deadline"] = dl.split("T", 1)[0]
            # Very loose guard: if not in form YYYY-MM-DD, leave as-is

        confidence = 0.7 if summary_json else 0.3
        return raw_text, summary_json, confidence

    def extract(self, email_text: str) -> Tuple[str, Dict[str, Any], float]:
        """
        Calls OpenAI (e.g., gpt-4o-mini-high-throughput) to extract tasks.
        Must return JSON: { "tasks": [ { owner, action, object, deadline, priority } ] }
        deadline should be ISO date when resolvable, else null.
        """
        client = self._get_client()
        system = (
            "You are an email task extractor. Return ONLY valid JSON with the schema:\n"
            '{ "tasks": [ { "owner": string|null, "action": string|null, "object": string|null, '
            '"deadline": string|null, "priority": "high"|"medium"|"low"|"fyi"|null } ] }\n'
            '- "deadline" MUST be ISO date (YYYY-MM-DD or YYYY-MM-DDThh:mm:ssZ) if resolvable, otherwise null.\n'
            "- If no tasks, return {\"tasks\":[]}.\n"
            "No extra text or fields."
        )
        user = f"Extract actionable tasks from the email into the required JSON schema:\n\n{email_text}"

        raw_text = ""
        try:
            resp = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
            )
            raw_text = resp.choices[0].message.content or ""
        except Exception:
            resp = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user + "\n\nReturn JSON only."},
                ],
                temperature=0.2,
            )
            raw_text = resp.choices[0].message.content or ""

        try:
            data = json.loads(raw_text)  # type: ignore[name-defined]
            if not isinstance(data, dict):
                data = {}
        except Exception:
            data = {}

        tasks = data.get("tasks")
        if not isinstance(tasks, list):
            tasks = []
        # Normalize each task object
        normalized = []
        for t in tasks:
            if not isinstance(t, dict):
                continue
            normalized.append(
                {
                    "owner": t.get("owner"),
                    "action": t.get("action"),
                    "object": t.get("object"),
                    "deadline": t.get("deadline"),
                    "priority": t.get("priority"),
                }
            )
        tasks_json = {"tasks": normalized}

        confidence = 0.7 if tasks_json is not None else 0.3
        return raw_text, tasks_json, confidence


