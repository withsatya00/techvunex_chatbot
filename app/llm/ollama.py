import json
import httpx
from typing import List, Dict, AsyncIterator
from app.llm.base import BaseLLMProvider, LLMResponse
from app.config import settings
from app.core.logging import logger
from app.core.exceptions import LLMProviderError

class OllamaProvider(BaseLLMProvider):
    """Local Ollama LLM Provider"""
    def __init__(self, base_url: str = settings.OLLAMA_BASE_URL, model_name: str = settings.OLLAMA_MODEL):
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name

    async def generate(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 1000
    ) -> LLMResponse:
        formatted_messages = [{"role": "system", "content": system_prompt}] + messages
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model_name,
            "messages": formatted_messages,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens}
        }
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code != 200:
                    raise LLMProviderError(f"Ollama returned HTTP {resp.status_code}: {resp.text}")
                data = resp.json()
                content = data.get("message", {}).get("content", "")
                return LLMResponse(
                    content=content,
                    prompt_tokens=data.get("prompt_eval_count", 0),
                    completion_tokens=data.get("eval_count", 0),
                    total_tokens=data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
                    model=self.model_name
                )
        except Exception as e:
            logger.error(f"Ollama generate error: {e}")
            raise LLMProviderError(f"Ollama error: {str(e)}")

    async def stream(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 1000
    ) -> AsyncIterator[str]:
        formatted_messages = [{"role": "system", "content": system_prompt}] + messages
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model_name,
            "messages": formatted_messages,
            "stream": True,
            "options": {"temperature": temperature, "num_predict": max_tokens}
        }
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream("POST", url, json=payload) as response:
                    async for line in response.aiter_lines():
                        if line:
                            data = json.loads(line)
                            delta = data.get("message", {}).get("content", "")
                            if delta:
                                yield delta
        except Exception as e:
            logger.error(f"Ollama stream error: {e}")
            raise LLMProviderError(f"Ollama stream error: {str(e)}")
