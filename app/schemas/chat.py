from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class SourceRef(BaseModel):
    source_url: str
    page_title: str
    section: Optional[str] = None
    snippet: Optional[str] = None
    similarity: Optional[float] = None

class ChatRequest(BaseModel):
    session_id: str = Field(..., description="Unique conversation session ID")
    message: str = Field(..., min_length=1, max_length=4000, description="User message text")
    language: Optional[str] = Field("auto", description="Preferred language: auto, en, hi, hinglish")
    user_metadata: Optional[Dict[str, Any]] = None

class ChatResponse(BaseModel):
    conversation_id: str
    session_id: str
    response: str
    sources: List[SourceRef] = []
    intent: str
    entities: Dict[str, Any] = {}
    lead_intent: bool = False
    human_required: bool = False
    latency_ms: float = 0.0
    suggested_actions: List[str] = []
    debug: Optional[Dict[str, Any]] = None


class StreamEvent(BaseModel):
    event: str  # token, sources, lead, handoff, done, error
    data: Any
