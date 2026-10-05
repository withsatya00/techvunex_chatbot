from abc import ABC, abstractmethod
from typing import List, Dict, Any, AsyncIterator, Optional
from pydantic import BaseModel

class LLMResponse(BaseModel):
    content: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    model: str = ""

class BaseLLMProvider(ABC):
    """
    Abstract interface for LLM providers.
    """
    @abstractmethod
    async def generate(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 1000
    ) -> LLMResponse:
        """Generate complete response asynchronously"""
        pass

    @abstractmethod
    async def stream(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 1000
    ) -> AsyncIterator[str]:
        """Stream response tokens asynchronously"""
        pass
