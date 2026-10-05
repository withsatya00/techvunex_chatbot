from app.config import settings
from app.llm.base import BaseLLMProvider
from app.llm.gemini import GeminiProvider
from app.llm.openai import OpenAIProvider
from app.llm.groq import GroqProvider
from app.llm.ollama import OllamaProvider
from app.llm.fallback import IntelligentLocalFallbackProvider
from app.core.logging import logger

def get_llm_provider() -> BaseLLMProvider:
    """
    Factory function to instantiate the configured LLM provider.
    Gracefully falls back to IntelligentLocalFallbackProvider if credentials are missing.
    """
    provider_name = settings.LLM_PROVIDER.lower()

    if provider_name == "gemini":
        if settings.GEMINI_API_KEY:
            logger.info("Instantiating Gemini LLM provider")
            return GeminiProvider()
        else:
            logger.warning("GEMINI_API_KEY not set. Using intelligent local fallback provider.")
            return IntelligentLocalFallbackProvider()

    elif provider_name == "openai":
        if settings.OPENAI_API_KEY:
            logger.info("Instantiating OpenAI LLM provider")
            return OpenAIProvider()
        else:
            logger.warning("OPENAI_API_KEY not set. Using intelligent local fallback provider.")
            return IntelligentLocalFallbackProvider()

    elif provider_name == "groq":
        if settings.GROQ_API_KEY:
            logger.info("Instantiating Groq LLM provider")
            return GroqProvider()
        else:
            logger.warning("GROQ_API_KEY not set. Using intelligent local fallback provider.")
            return IntelligentLocalFallbackProvider()

    elif provider_name == "ollama":
        logger.info("Instantiating Ollama LLM provider")
        return OllamaProvider()

    else:
        logger.warning(f"Unknown LLM provider '{provider_name}'. Defaulting to local fallback provider.")
        return IntelligentLocalFallbackProvider()
