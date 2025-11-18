import json
import re
import os
from typing import List, Dict, Any, Optional
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
from app.core.config import settings
from app.core.prompts import SUMMARY_PROMPT, EXTRACTION_PROMPT, QA_PROMPT
import logging

logger = logging.getLogger(__name__)


def _parse_model_id(model_id: str) -> tuple:
    """Parse model ID like 'anthropic:claude-3-5-haiku' into (provider, model_name)"""
    if ":" in model_id:
        provider, model_name = model_id.split(":", 1)
        return provider.lower(), model_name
    # Default to OpenAI if no provider prefix
    return "openai", model_id


class LLMProvider:
    def __init__(self):
        # Legacy OpenAI settings (for backward compatibility)
        self.provider = settings.llm_provider
        self.openai_api_key = settings.openai_api_key
        self.openai_model = settings.openai_model
        self.summary_model = settings.openai_summary_model or self.openai_model
        self.extractor_model = settings.openai_extractor_model or self.openai_model
        
        # New multi-provider settings
        self.anthropic_api_key = settings.anthropic_api_key
        self.google_api_key = settings.google_api_key
        
        # Default models from config
        self.default_summarizer_model = settings.summarizer_model
        self.default_extractor_model = settings.extractor_model
        self.default_extractor_fallback_model = settings.extractor_fallback_model
        
        # Check if we should use mock (no API keys at all)
        self.use_mock = (
            not self.openai_api_key and 
            not self.anthropic_api_key and 
            not self.google_api_key
        ) or self.provider == "mock"
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _call_openai(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        response_format: Optional[Dict[str, str]] = None,
        model_name: Optional[str] = None,
    ) -> str:
        """Call OpenAI API"""
        if self.use_mock:
            return self._mock_response(messages)
        
        if not self.openai_api_key:
            raise ValueError("OpenAI API key not set")
        
        model = model_name or self.openai_model
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                payload = {
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": 500
                }
                
                if response_format:
                    payload["response_format"] = response_format
                
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.openai_api_key}",
                        "Content-Type": "application/json"
                    },
                    json=payload
                )
                response.raise_for_status()
                result = response.json()
                return result["choices"][0]["message"]["content"]
            except httpx.HTTPStatusError as e:
                logger.error(f"OpenAI API error: {e.response.status_code} - {e.response.text}")
                raise
            except Exception as e:
                logger.error(f"OpenAI API call failed: {e}")
                raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _call_anthropic(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        model_name: Optional[str] = None,
    ) -> str:
        """Call Anthropic (Claude) API"""
        if self.use_mock:
            return self._mock_response(messages)
        
        if not self.anthropic_api_key:
            raise ValueError("Anthropic API key not set")
        
        try:
            import anthropic
        except ImportError:
            raise RuntimeError("anthropic SDK not installed. pip install anthropic")
        
        client = anthropic.Client(api_key=self.anthropic_api_key)
        
        # Map model names
        model = model_name or "claude-3-5-haiku-20241022"
        model_mapping = {
            "claude-3-5-haiku": "claude-3-5-haiku-20241022",
            "claude-3-5-sonnet": "claude-3-5-sonnet-20241022",
            "claude-3-haiku": "claude-3-haiku-20240307",
            "claude-3-sonnet": "claude-3-sonnet-20240229",
        }
        model = model_mapping.get(model, model)
        
        # Convert messages format (Anthropic uses different format)
        system_msg = None
        user_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_msg = msg["content"]
            else:
                user_messages.append(msg)
        
        # Combine user messages
        user_content = "\n\n".join([m["content"] for m in user_messages])
        
        try:
            response = client.messages.create(
                model=model,
                max_tokens=1024,
                temperature=temperature,
                system=system_msg or "",
                messages=[{"role": "user", "content": user_content}]
            )
            return response.content[0].text
        except Exception as e:
            logger.error(f"Anthropic API call failed: {e}")
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _call_google(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        model_name: Optional[str] = None,
    ) -> str:
        """Call Google (Gemini) API"""
        if self.use_mock:
            return self._mock_response(messages)
        
        if not self.google_api_key:
            raise ValueError("Google API key not set")
        
        try:
            import google.generativeai as genai
        except ImportError:
            raise RuntimeError("google-generativeai SDK not installed. pip install google-generativeai")
        
        genai.configure(api_key=self.google_api_key)
        
        # Map model names
        model = model_name or "gemini-flash-latest"
        if model in ("gemini-flash", "gemini-1.5-flash"):
            model = "gemini-flash-latest"
        if model.startswith("models/"):
            model = model.split("/", 1)[1]
        
        try:
            gemini_model = genai.GenerativeModel(
                model,
                generation_config={
                    "temperature": temperature,
                    "max_output_tokens": 1024,
                }
            )
            
            # Combine messages
            prompt_parts = []
            for msg in messages:
                if msg["role"] == "system":
                    prompt_parts.append(f"System: {msg['content']}")
                else:
                    prompt_parts.append(f"{msg['role'].capitalize()}: {msg['content']}")
            
            prompt = "\n\n".join(prompt_parts)
            response = gemini_model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Google API call failed: {e}")
            raise
    
    async def _call_model(
        self,
        messages: List[Dict[str, str]],
        model_id: Optional[str] = None,
        temperature: float = 0.7,
        response_format: Optional[Dict[str, str]] = None,
    ) -> str:
        """Call the appropriate model based on model_id"""
        if model_id:
            provider, model_name = _parse_model_id(model_id)
        else:
            provider = "openai"
            model_name = None
        
        if provider == "anthropic":
            return await self._call_anthropic(messages, temperature=temperature, model_name=model_name)
        elif provider == "google":
            return await self._call_google(messages, temperature=temperature, model_name=model_name)
        else:  # Default to OpenAI
            return await self._call_openai(
                messages, 
                temperature=temperature, 
                response_format=response_format,
                model_name=model_name
            )
    
    async def call_with_json_mode(
        self, 
        messages: List[Dict[str, str]], 
        temperature: float = 0.2, 
        model_override: Optional[str] = None
    ) -> str:
        """Call model with JSON response format enforced"""
        # Determine which model to use
        model_id = model_override or self.default_summarizer_model
        
        # For OpenAI, use JSON mode
        provider, _ = _parse_model_id(model_id)
        if provider == "openai":
            return await self._call_openai(
                messages,
                temperature=temperature,
                response_format={"type": "json_object"},
                model_name=model_id.split(":", 1)[1] if ":" in model_id else model_id
            )
        else:
            # For other providers, request JSON in the prompt
            json_messages = messages.copy()
            if json_messages and json_messages[-1]["role"] == "user":
                json_messages[-1]["content"] += "\n\nIMPORTANT: Return ONLY valid JSON, no other text."
            response = await self._call_model(json_messages, model_id=model_id, temperature=temperature)
            # Try to extract JSON from response
            response = response.strip()
            if response.startswith("```json"):
                response = response.split("```json")[1].split("```")[0].strip()
            elif response.startswith("```"):
                response = response.split("```")[1].split("```")[0].strip()
            return response
    
    def _mock_response(self, messages: List[Dict[str, str]]) -> str:
        last_msg = messages[-1]["content"].lower()
        system_msg = messages[0]["content"].lower() if messages else ""
        
        if "summarizer" in system_msg or ("subject:" in last_msg and "from:" in last_msg):
            sender_match = re.search(r'from:\s*(\w+)', last_msg)
            sender = sender_match.group(1) if sender_match else "They"
            return json.dumps({
                "summary": f"{sender} shares project updates and next steps."
            })
        elif "json" in last_msg and "task" in last_msg:
            return json.dumps([
                {
                    "title": "Complete project tasks",
                    "owner": "team",
                    "due": None,
                    "source_message_id": "m1",
                    "type": "action"
                }
            ])
        elif "answer" in last_msg or "question" in last_msg:
            return "Based on the thread, you need to complete the assigned tasks. Sources: m1"
        elif "summarize" in last_msg:
            return "Team discussion about project kickoff with assigned tasks and deadlines."
        
        return "Mock LLM response"
    
    async def summarize_map_reduce(self, messages: List[Dict[str, Any]]) -> str:
        if len(messages) == 0:
            return "Empty thread"
        
        if len(messages) <= 3:
            combined_text = "\n\n".join([
                f"From: {msg.get('from_', 'Unknown')}\nSubject: {msg.get('subject', '')}\n{msg.get('clean_body', msg.get('body', ''))}"
                for msg in messages
            ])
            
            llm_messages = [
                {"role": "system", "content": SUMMARY_PROMPT},
                {"role": "user", "content": combined_text}
            ]
            
            return await self._call_model(llm_messages, model_id=self.default_summarizer_model, temperature=0.5)
        
        summaries = []
        for i in range(0, len(messages), 2):
            batch = messages[i:i+2]
            batch_text = "\n\n".join([
                f"From: {msg.get('from_', 'Unknown')}\nSubject: {msg.get('subject', '')}\n{msg.get('clean_body', msg.get('body', ''))}"
                for msg in batch
            ])
            
            llm_messages = [
                {"role": "system", "content": "Summarize this email exchange briefly."},
                {"role": "user", "content": batch_text}
            ]
            
            summary = await self._call_model(llm_messages, model_id=self.default_summarizer_model, temperature=0.5)
            summaries.append(summary)
        
        final_text = "\n\n".join(summaries)
        llm_messages = [
            {"role": "system", "content": SUMMARY_PROMPT},
            {"role": "user", "content": final_text}
        ]
        
        return await self._call_model(llm_messages, model_id=self.default_summarizer_model, temperature=0.5)
    
    async def extract_tasks(
        self, 
        messages: List[Dict[str, Any]], 
        use_fallback: bool = False
    ) -> List[Dict[str, Any]]:
        """Extract tasks using the configured extractor model, with optional fallback"""
        combined_text = "\n\n".join([
            f"Message ID: {msg.get('id', 'unknown')}\nFrom: {msg.get('from_', 'Unknown')}\nSubject: {msg.get('subject', '')}\n{msg.get('clean_body', msg.get('body', ''))}"
            for msg in messages
        ])
        
        llm_messages = [
            {"role": "system", "content": EXTRACTION_PROMPT},
            {"role": "user", "content": combined_text}
        ]
        
        # Use fallback model if requested, otherwise use default extractor model
        model_id = self.default_extractor_fallback_model if use_fallback else self.default_extractor_model
        
        response = await self._call_model(llm_messages, model_id=model_id, temperature=0.3)
        
        try:
            if response.strip().startswith('['):
                return json.loads(response)
            elif response.strip().startswith('{'):
                return [json.loads(response)]
            else:
                response_clean = response.strip()
                if '```json' in response_clean:
                    response_clean = response_clean.split('```json')[1].split('```')[0].strip()
                elif '```' in response_clean:
                    response_clean = response_clean.split('```')[1].split('```')[0].strip()
                return json.loads(response_clean)
        except json.JSONDecodeError:
            return []
    
    async def answer(self, question: str, snippets: List[Dict[str, str]]) -> Dict[str, Any]:
        context = "\n\n".join([
            f"[Message {snippet['message_id']}]: {snippet['text']}"
            for snippet in snippets
        ])
        
        llm_messages = [
            {"role": "system", "content": QA_PROMPT},
            {"role": "user", "content": f"Question: {question}\n\nContext:\n{context}"}
        ]
        
        response = await self._call_model(llm_messages, model_id=self.default_summarizer_model, temperature=0.3)
        
        sources = []
        for snippet in snippets:
            if snippet['message_id'] in response or snippet['text'][:50] in response:
                sources.append(snippet['message_id'])
        
        if not sources:
            sources = [s['message_id'] for s in snippets[:2]]
        
        return {
            "answer": response,
            "sources": sources
        }


llm_provider = LLMProvider()
