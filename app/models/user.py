import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime
from app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=True)
    email = Column(String(150), unique=True, index=True, nullable=True)
    phone = Column(String(30), nullable=True)
    company = Column(String(150), nullable=True)
    role = Column(String(20), default="visitor")  # visitor, admin
    password_hash = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
