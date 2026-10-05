from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class FeedbackCreate(BaseModel):
    conversation_id: str
    message_id: Optional[str] = None
    rating: int = Field(..., ge=-1, le=5, description="1 (positive), -1 (negative), or 1-5")
    feedback: Optional[str] = None

class FeedbackResponse(BaseModel):
    id: str
    conversation_id: str
    message_id: Optional[str] = None
    rating: int
    feedback: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
