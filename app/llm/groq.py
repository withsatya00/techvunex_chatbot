from typing import List, Dict, AsyncIterator
from groq import AsyncGroq
from app.llm.base import BaseLLMProvider, LLMResponse
from app.config import settings
from app.core.logging import logger
from app.core.exceptions import LLMProviderError

class GroqProvider(BaseLLMProvider):
    """Groq Cloud LLM Provider"""
    def __init__(self, api_key: str = settings.GROQ_API_KEY, model_name: str = settings.GROQ_MODEL):
        self.api_key = api_key
        self.model_name = model_name
        self.client = AsyncGroq(api_key=api_key) if api_key else None

    async def generate(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 1000
    ) -> LLMResponse:
        if not self.client:
            raise LLMProviderError("GROQ_API_KEY is not configured.")

        formatted_messages = [{"role": "system", "content": system_prompt}] + messages
        try:
            resp = await self.client.chat.completions.create(
                model=self.model_name,
                messages=formatted_messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            choice = resp.choices[0].message
            usage = resp.usage
            return LLMResponse(
                content=choice.content or "",
                prompt_tokens=usage.prompt_tokens if usage else 0,
                completion_tokens=usage.completion_tokens if usage else 0,
                total_tokens=usage.total_tokens if usage else 0,
                model=self.model_name
            )
        except Exception as e:
            logger.error(f"Groq generate error: {e}")
            raise LLMProviderError(f"Groq API error: {str(e)}")

    async def stream(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 1000
    ) -> AsyncIterator[str]:
        if not self.client:
            raise LLMProviderError("GROQ_API_KEY is not configured.")

        formatted_messages = [{"role": "system", "content": system_prompt}] + messages
        try:
            stream = await self.client.chat.completions.create(
                model=self.model_name,
                messages=formatted_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True
            )
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"Groq stream error: {e}")
            raise LLMProviderError(f"Groq stream error: {str(e)}")
