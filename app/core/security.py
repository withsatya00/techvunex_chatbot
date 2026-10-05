import time
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import jwt, JWTError
from passlib.context import CryptContext
from app.config import settings
from app.core.exceptions import AuthenticationError, PromptInjectionError
from app.core.logging import logger

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Prompt injection detection patterns
PROMPT_INJECTION_PATTERNS = [
    r"(?i)ignore\s+(all\s+)?(previous|prior|above)\s+instructions",
    r"(?i)system\s+prompt",
    r"(?i)reveal\s+(your\s+)?(instructions|prompt|api\s*key|secret)",
    r"(?i)repeat\s+the\s+words\s+above",
    r"(?i)you\s+are\s+now\s+in\s+developer\s+mode",
    r"(?i)jailbreak",
    r"(?i)do\s+anything\s+now",
    r"(?i)dan\s+mode",
    r"(?i)output\s+initial\s+prompt",
    r"(?i)show\s+me\s+your\s+rules",
    r"(?i)override\s+(all\s+)?safety",
    r"(?i)bypass\s+restrictions",
    r"(?i)database\s+credentials",
    r"(?i)select\s+.*\s+from\s+users",
]

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError:
        raise AuthenticationError("Could not validate credentials or token expired")

def sanitize_and_check_injection(text: str) -> str:
    """
    Check for prompt injection attacks and sanitize user inputs.
    Returns cleaned text or raises PromptInjectionError.
    """
    if not text:
        return ""
    
    # Strip null bytes and control chars
    clean_text = text.replace("\x00", "").strip()
    
    # Enforce maximum text length
    if len(clean_text) > 4000:
        clean_text = clean_text[:4000]

    for pattern in PROMPT_INJECTION_PATTERNS:
        if re.search(pattern, clean_text):
            logger.warning("Prompt injection detected", extra={"pattern": pattern, "snippet": clean_text[:80]})
            raise PromptInjectionError("Your message contains unauthorized command or prompt injection instructions.")

    return clean_text

class InMemoryRateLimiter:
    """Simple sliding-window rate limiter for development and fallback"""
    def __init__(self, requests_per_minute: int = 60):
        self.limit = requests_per_minute
        self.requests: Dict[str, list] = {}

    def is_allowed(self, client_id: str) -> bool:
        now = time.time()
        window_start = now - 60
        reqs = self.requests.get(client_id, [])
        # filter out older requests
        reqs = [t for t in reqs if t > window_start]
        if len(reqs) >= self.limit:
            return False
        reqs.append(now)
        self.requests[client_id] = reqs
        return True

rate_limiter = InMemoryRateLimiter(settings.RATE_LIMIT_PER_MINUTE)
