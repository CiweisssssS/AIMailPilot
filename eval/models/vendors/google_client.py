import json
import os
import re
from typing import Any, Dict, Tuple

from ..registry import ModelClient


class GoogleClient(ModelClient):
    def __init__(self, model: str):
        self.model = model
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise EnvironmentError("GOOGLE_API_KEY is not set")
        try:
            import google.generativeai as genai  # type: ignore
        except Exception:
            genai = None  # type: ignore
        self._genai = genai
        self._model = None

    def _get_model(self):
        if self._model is None:
            if self._genai is None:
                raise RuntimeError("google-generativeai SDK not installed. pip install google-generativeai")
            self._genai.configure(api_key=self.api_key)  # type: ignore
            # Map shorthand to actual Gemini model id if needed (prefer latest stable names)
            model_id = (self.model or "").strip()
            # Accept fully qualified names like "gemini-2.0-flash-001", "gemini-2.5-flash", "gemini-flash-latest" as-is
            # Provide sensible defaults for shorthand identifiers
            if model_id in ("gemini-flash", "gemini-1.5-flash"):
                # Default to a widely available alias if 1.5 is not enabled on the account
                model_id = "gemini-flash-latest"
            # If user passed vendor prefix accidentally, strip it
            if model_id.startswith("models/"):
                model_id = model_id.split("/", 1)[1]
            self._model = self._genai.GenerativeModel(  # type: ignore
                model_id,
                generation_config={"response_mime_type": "application/json", "temperature": 0.2},
            )
        return self._model

    def summarize(self, email_text: str) -> Tuple[str, Dict[str, Any], float]:
        mdl = self._get_model()
        system = (
            "You are an email summarization assistant. The input starts with 'Received at (UTC): <ISO>'. "
            "Use that timestamp to resolve any relative time phrases into absolute dates.\n"
            "Output STRICT JSON with keys: actor, action, object, deadline, notes.\n"
            "- actor: requester (prefer sender's name). NEVER 'you/we/our team'; null if unknown.\n"
            "- action: one concise verb phrase (send/review/approve/schedule/prepare/update...), not a full sentence.\n"
            "- object: short noun phrase.\n"
            "- deadline: YYYY-MM-DD if resolvable, else null.\n"
            "- notes: brief context or null.\n"
            "No extra fields."
        )
        prompt = f"{system}\n\nSummarize the email into the required JSON fields:\n\n{email_text}\n\nReturn JSON only."

        resp = mdl.generate_content(prompt)
        raw_text = ""
        try:
            raw_text = resp.text or ""
        except Exception:
            raw_text = ""

        def _strip_code_fences(s: str) -> str:
            s = s.strip()
            # remove ```json ... ``` or ``` ... ``` fences if present
            if s.startswith("```"):
                s = re.sub(r"^```(?:json)?\s*", "", s)
                s = re.sub(r"\s*```$", "", s)
            return s.strip()

        def _parse_json_obj(s: str) -> Dict[str, Any]:
            s = _strip_code_fences(s)
            try:
                data = json.loads(s)
                # If model returned a list, try taking the first dict element
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict):
                            return item
                    return {}
                if isinstance(data, dict):
                    return data
                return {}
            except Exception:
                # best-effort: extract first top-level JSON object
                m = re.search(r"\{[\s\S]*\}", s)
                if m:
                    try:
                        cand = json.loads(m.group(0))
                        if isinstance(cand, dict):
                            return cand
                    except Exception:
                        pass
                return {}

        summary_json = _parse_json_obj(raw_text)

        for k in ["actor", "action", "object", "deadline", "notes"]:
            summary_json.setdefault(k, None)
        # Normalize deadline to YYYY-MM-DD if full ISO was returned
        dl = summary_json.get("deadline")
        if isinstance(dl, str) and "T" in dl:
            summary_json["deadline"] = dl.split("T", 1)[0]

        confidence = 0.7 if summary_json else 0.3
        return raw_text, summary_json, confidence

    def extract(self, email_text: str) -> Tuple[str, Dict[str, Any], float]:
        """
        Calls Gemini to extract tasks.
        Must return JSON: { "tasks": [ { owner, action, object, deadline, priority } ] }.
        deadline should be absolute ISO (YYYY-MM-DD or ISO datetime) if resolvable, else null.
        """
        mdl = self._get_model()
        system = (
            "You are an email task extractor. Return ONLY valid JSON with the schema:\n"
            '{ "tasks": [ { "owner": string|null, "action": string|null, "object": string|null, '
            '"deadline": string|null, "priority": "high"|"medium"|"low"|"fyi"|null } ] }\n'
            "- Use the 'Received at (UTC): <ISO>' header in the input to resolve relative time into absolute dates.\n"
            '- "deadline" MUST be absolute ISO date (YYYY-MM-DD) if resolvable, otherwise null.\n'
            "- If no tasks, return {\"tasks\":[]}.\n"
            "No extra text or fields."
        )
        prompt = f"{system}\n\nExtract actionable tasks from the email into the required JSON schema:\n\n{email_text}\n\nReturn JSON only."

        resp = mdl.generate_content(prompt)
        raw_text = ""
        try:
            raw_text = resp.text or ""
        except Exception:
            raw_text = ""

        def _parse_dict(s: str) -> Dict[str, Any]:
            try:
                data = json.loads(s)
                if isinstance(data, dict):
                    return data
            except Exception:
                pass
            return {}

        data = _parse_dict(raw_text)
        tasks = data.get("tasks")
        if not isinstance(tasks, list):
            tasks = []

        normalized = []
        for t in tasks:
            if not isinstance(t, dict):
                continue
            owner = t.get("owner")
            action = t.get("action")
            obj = t.get("object")
            deadline = t.get("deadline")
            priority = t.get("priority")
            # Normalize deadline to YYYY-MM-DD if full ISO provided
            if isinstance(deadline, str) and "T" in deadline:
                deadline = deadline.split("T", 1)[0]
            normalized.append(
                {
                    "owner": owner if owner is not None else "me",
                    "action": action,
                    "object": obj,
                    "deadline": deadline,
                    "priority": priority,
                }
            )

        tasks_json = {"tasks": normalized}
        confidence = 0.7 if isinstance(data, dict) else 0.3
        return raw_text, tasks_json, confidence


