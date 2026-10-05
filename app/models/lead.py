import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Boolean
from app.core.database import Base

class Lead(Base):
    __tablename__ = "leads"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=True)
    email = Column(String(150), index=True, nullable=True)
    phone = Column(String(30), nullable=True)
    company = Column(String(150), nullable=True)
    service = Column(String(100), nullable=True)
    requirement = Column(Text, nullable=True)
    budget = Column(String(100), nullable=True)
    timeline = Column(String(100), nullable=True)
    status = Column(String(30), default="new", index=True)  # new, contacted, qualified, converted, closed, human_required
    source = Column(String(50), default="website_chat")
    human_required = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
