from fastapi import HTTPException, status

class ChatbotException(Exception):
    """Base exception for Techvunex Chatbot"""
    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.message = message
        self.status_code = status_code

class LLMProviderError(ChatbotException):
    """Raised when an LLM provider fails"""
    def __init__(self, message: str = "LLM provider invocation failed"):
        super().__init__(message, status_code=502)

class RetrievalError(ChatbotException):
    """Raised when vector or hybrid retrieval fails"""
    def __init__(self, message: str = "Retrieval error"):
        super().__init__(message, status_code=500)

class IngestionError(ChatbotException):
    """Raised during website crawling or indexing"""
    def __init__(self, message: str = "Knowledge base ingestion failed"):
        super().__init__(message, status_code=500)

class PromptInjectionError(ChatbotException):
    """Raised when a prompt injection attempt is detected"""
    def __init__(self, message: str = "Malicious or unauthorized prompt pattern detected."):
        super().__init__(message, status_code=400)

class AuthenticationError(ChatbotException):
    """Raised on invalid credentials or expired token"""
    def __init__(self, message: str = "Invalid credentials"):
        super().__init__(message, status_code=401)
