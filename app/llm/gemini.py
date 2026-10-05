import asyncio
from typing import List, Dict, AsyncIterator
from app.llm.base import BaseLLMProvider, LLMResponse
from app.config import settings
from app.core.logging import logger
from app.core.exceptions import LLMProviderError

class GeminiProvider(BaseLLMProvider):
    """Google Gemini LLM Provider"""
    def __init__(self, api_key: str = settings.GEMINI_API_KEY, model_name: str = settings.GEMINI_MODEL):
        self.api_key = api_key
        self.model_name = model_name
        self._client = None
        if self.api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self._genai = genai
            except Exception as e:
                logger.error(f"Failed to initialize Gemini: {e}")

    def _prepare_history(self, messages: List[Dict[str, str]], system_prompt: str):
        contents = []
        # Add system prompt as initial directive or in model config
        for m in messages:
            role = "user" if m["role"] == "user" else "model"
            contents.append({"role": role, "parts": [m["content"]]})
        return contents

    async def generate(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 1000
    ) -> LLMResponse:
        if not self.api_key:
            raise LLMProviderError("GEMINI_API_KEY is not configured.")

        try:
            model = self._genai.GenerativeModel(
                model_name=self.model_name,
                system_instruction=system_prompt,
                generation_config={"temperature": temperature, "max_output_tokens": max_tokens}
            )
            # Last message is the current prompt
            last_msg = messages[-1]["content"] if messages else ""
            chat_history = self._prepare_history(messages[:-1], system_prompt)
            
            chat = model.start_chat(history=chat_history)
            try:
                resp = await chat.send_message_async(last_msg)
            except Exception as async_err:
                if "Event loop" in str(async_err) or "closed" in str(async_err).lower():
                    logger.warning(f"Gemini async loop transition detected ({async_err}). Falling back to executor.")
                    self._genai.configure(api_key=self.api_key)
                    loop = asyncio.get_running_loop()
                    resp = await loop.run_in_executor(None, lambda: chat.send_message(last_msg))
                else:
                    raise async_err

            text = resp.text if hasattr(resp, "text") else ""
            return LLMResponse(
                content=text,
                prompt_tokens=len(last_msg) // 4,
                completion_tokens=len(text) // 4,
                total_tokens=(len(last_msg) + len(text)) // 4,
                model=self.model_name
            )
        except Exception as e:
            logger.error(f"Gemini generation error: {e}")
            raise LLMProviderError(f"Gemini API error: {str(e)}")

    async def stream(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 1000
    ) -> AsyncIterator[str]:
        if not self.api_key:
            raise LLMProviderError("GEMINI_API_KEY is not configured.")

        try:
            model = self._genai.GenerativeModel(
                model_name=self.model_name,
                system_instruction=system_prompt,
                generation_config={"temperature": temperature, "max_output_tokens": max_tokens}
            )
            last_msg = messages[-1]["content"] if messages else ""
            chat_history = self._prepare_history(messages[:-1], system_prompt)
            chat = model.start_chat(history=chat_history)

            try:
                response_stream = await chat.send_message_async(last_msg, stream=True)
                async for chunk in response_stream:
                    try:
                        if chunk.text:
                            yield chunk.text
                    except Exception:
                        continue
            except Exception as async_err:
                if "Event loop" in str(async_err) or "closed" in str(async_err).lower():
                    logger.warning(f"Gemini async stream loop transition detected ({async_err}). Falling back to executor.")
                    self._genai.configure(api_key=self.api_key)
                    loop = asyncio.get_running_loop()
                    sync_stream = await loop.run_in_executor(
                        None, lambda: chat.send_message(last_msg, stream=True)
                    )
                    for chunk in sync_stream:
                        if chunk.text:
                            yield chunk.text
                else:
                    raise async_err

        except Exception as e:
            logger.error(f"Gemini streaming error: {e}")
            raise LLMProviderError(f"Gemini stream error: {str(e)}")
