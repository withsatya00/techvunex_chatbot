from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.feedback import Feedback
from app.schemas.feedback import FeedbackCreate, FeedbackResponse

router = APIRouter(prefix="/feedback", tags=["Feedback"])

@router.post("", response_model=FeedbackResponse)
async def submit_feedback(fb_in: FeedbackCreate, db: AsyncSession = Depends(get_db)):
    fb = Feedback(
        conversation_id=fb_in.conversation_id,
        message_id=fb_in.message_id,
        rating=fb_in.rating,
        feedback=fb_in.feedback
    )
    db.add(fb)
    await db.commit()
    await db.refresh(fb)
    return fb

@router.get("", response_model=List[FeedbackResponse])
async def list_feedback(limit: int = 50, offset: int = 0, db: AsyncSession = Depends(get_db)):
    stmt = select(Feedback).order_by(Feedback.created_at.desc()).offset(offset).limit(limit)
    res = await db.execute(stmt)
    return res.scalars().all()
