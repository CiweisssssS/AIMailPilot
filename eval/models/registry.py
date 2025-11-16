from typing import Any, Dict, Tuple


class ModelClient:
    def summarize(self, email_text: str) -> Tuple[str, Dict[str, Any], float]:
        """
        Returns (raw_text, summary_json, confidence).
        summary_json should include: actor, action, object, deadline, notes.
        """
        raise NotImplementedError("Implement summarize in concrete model client")

    def extract(self, email_text: str) -> Tuple[str, Dict[str, Any], float]:
        """
        Returns (raw_text, tasks_json, confidence).
        tasks_json: { tasks: [ {owner,action,object,deadline,priority}, ... ] }
        """
        raise NotImplementedError("Implement extract in concrete model client")


def get_model_client(vendor_model: str) -> ModelClient:
    """
    vendor_model examples:
      - openai:gpt-4o-mini-high-throughput
      - openai:gpt-4o
      - anthropic:claude-3-5-haiku
      - google:gemini-flash
    """
    vendor, model = vendor_model.split(":", 1)
    if vendor == "openai":
        from .vendors.openai_client import OpenAIClient
        return OpenAIClient(model=model)
    if vendor == "anthropic":
        from .vendors.anthropic_client import AnthropicClient
        return AnthropicClient(model=model)
    if vendor == "google":
        from .vendors.google_client import GoogleClient
        return GoogleClient(model=model)
    raise ValueError(f"Unknown vendor prefix: {vendor_model}")


