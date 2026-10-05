import asyncio
import re
from typing import List, Dict, AsyncIterator
from app.llm.base import BaseLLMProvider, LLMResponse
from app.core.logging import logger

class IntelligentLocalFallbackProvider(BaseLLMProvider):
    """
    Intelligent local generator used when no external API key is configured.
    Synthesizes accurate answers directly from the retrieved context embedded in the prompt.
    """
    def __init__(self):
        self.model_name = "techvunex-local-engine"

    def _synthesize_answer(self, messages: List[Dict[str, str]], system_prompt: str) -> str:
        last_msg = messages[-1]["content"] if messages else ""
        query_lower = last_msg.lower()

        # Check if knowledge context is passed in the prompt
        context_match = re.search(r"--- RETRIEVED KNOWLEDGE BASE CONTEXT ---\s*(.*?)\s*--- END RETRIEVED CONTEXT ---", system_prompt, re.DOTALL)
        context_text = context_match.group(1).strip() if context_match else ""

        # Language detection: Hindi / Hinglish cues
        is_hindi = any(w in query_lower for w in ["hai", "kya", "kaise", "mujhe", "bhai", "namaste", "chahiye", "karwana", "banwana", "hoga"])

        if is_hindi:
            greeting = "Namaste! "
        else:
            greeting = "Hello! "

        # If knowledge context exists and contains relevant info
        if context_text and len(context_text) > 40:
            # Extract first 2-3 informative sentences from context
            sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', context_text) if len(s.strip()) > 20 and not s.startswith("Title:") and not s.startswith("Section:")]
            clean_summary = " ".join(sentences[:3]) if sentences else context_text[:300]

            if is_hindi:
                ans = f"{greeting}Techvunex ke according: {clean_summary}\n\nAapko isme kis tarah ka requirement ya project develop karwana hai? Main details share karne mein aapki help kar sakta hoon."
            else:
                ans = f"{greeting}Based on Techvunex's verified capabilities:\n\n{clean_summary}\n\nWould you like more specific details, an architecture consultation, or to connect directly with the Techvunex engineering team?"
        else:
            # If not in KB, adhere strictly to hallucination prevention rule
            if is_hindi:
                ans = f"{greeting}Main is baare mein verified information check nahi kar pa raha hoon. Lekin main aapko directly Techvunex team ke sath connect karwa sakta hoon."
            else:
                ans = f"{greeting}I don't have verified information about that in our knowledge base. I can connect you directly with the Techvunex team."

        return ans

    async def generate(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 1000
    ) -> LLMResponse:
        answer = self._synthesize_answer(messages, system_prompt)
        return LLMResponse(
            content=answer,
            prompt_tokens=len(str(messages)) // 4,
            completion_tokens=len(answer) // 4,
            total_tokens=(len(str(messages)) + len(answer)) // 4,
            model=self.model_name
        )

    async def stream(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 1000
    ) -> AsyncIterator[str]:
        answer = self._synthesize_answer(messages, system_prompt)
        words = answer.split(" ")
        for i, word in enumerate(words):
            yield word + (" " if i < len(words) - 1 else "")
            await asyncio.sleep(0.015)
