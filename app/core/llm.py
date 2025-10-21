import json
from typing import List, Dict, Any, Optional
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
from app.core.config import settings
from app.core.prompts import SUMMARY_PROMPT, EXTRACTION_PROMPT, QA_PROMPT


class LLMProvider:
    def __init__(self):
        self.provider = settings.llm_provider
        self.api_key = settings.openai_api_key
        self.model = settings.openai_model
        self.use_mock = not self.api_key or self.provider == "mock"
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _call_openai(self, messages: List[Dict[str, str]], temperature: float = 0.7) -> str:
        if self.use_mock:
            return self._mock_response(messages)
        
        import logging
        logger = logging.getLogger(__name__)
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": 500
                    }
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
    
    def _mock_response(self, messages: List[Dict[str, str]]) -> str:
        last_msg = messages[-1]["content"].lower()
        
        if "summarize" in last_msg:
            return "Team discussion about project kickoff. Meeting scheduled, with assigned owners for different tasks."
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
        elif "answer" in last_msg:
            return "Based on the thread, you need to complete the assigned tasks. Sources: m1"
        
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
            
            return await self._call_openai(llm_messages, temperature=0.5)
        
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
            
            summary = await self._call_openai(llm_messages, temperature=0.5)
            summaries.append(summary)
        
        final_text = "\n\n".join(summaries)
        llm_messages = [
            {"role": "system", "content": SUMMARY_PROMPT},
            {"role": "user", "content": final_text}
        ]
        
        return await self._call_openai(llm_messages, temperature=0.5)
    
    async def extract_tasks(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        combined_text = "\n\n".join([
            f"Message ID: {msg.get('id', 'unknown')}\nFrom: {msg.get('from_', 'Unknown')}\nSubject: {msg.get('subject', '')}\n{msg.get('clean_body', msg.get('body', ''))}"
            for msg in messages
        ])
        
        llm_messages = [
            {"role": "system", "content": EXTRACTION_PROMPT},
            {"role": "user", "content": combined_text}
        ]
        
        response = await self._call_openai(llm_messages, temperature=0.3)
        
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
        
        response = await self._call_openai(llm_messages, temperature=0.3)
        
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
