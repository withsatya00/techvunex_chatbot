from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class LeadCreate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    service: Optional[str] = None
    requirement: Optional[str] = None
    budget: Optional[str] = None
    timeline: Optional[str] = None
    status: Optional[str] = "new"
    source: Optional[str] = "website_chat"
    human_required: Optional[bool] = False

class LeadUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    service: Optional[str] = None
    requirement: Optional[str] = None
    budget: Optional[str] = None
    timeline: Optional[str] = None
    status: Optional[str] = None
    human_required: Optional[bool] = None

class LeadResponse(BaseModel):
    id: str
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    service: Optional[str] = None
    requirement: Optional[str] = None
    budget: Optional[str] = None
    timeline: Optional[str] = None
    status: str
    source: str
    human_required: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
