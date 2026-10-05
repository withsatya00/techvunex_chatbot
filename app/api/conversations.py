from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.conversation import Conversation
from app.schemas.conversation import ConversationResponse, ConversationDetailResponse
from app.services.conversation_service import conversation_service

router = APIRouter(prefix="/conversations", tags=["Conversations"])

@router.get("", response_model=List[ConversationResponse])
async def list_conversations(limit: int = 50, offset: int = 0, db: AsyncSession = Depends(get_db)):
    convs = await conversation_service.list_conversations(db, limit=limit, offset=offset)
    results = []
    for c in convs:
        results.append(ConversationResponse(
            id=c.id,
            session_id=c.session_id,
            title=c.title or "New Conversation",
            intent=c.intent,
            created_at=c.created_at,
            updated_at=c.updated_at,
            message_count=len(c.messages) if c.messages else 0
        ))
    return results

@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(conversation_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(Conversation).where(Conversation.id == conversation_id)
    res = await db.execute(stmt)
    conv = res.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return conv

@router.delete("/{conversation_id}")
async def delete_conversation(conversation_id: str, db: AsyncSession = Depends(get_db)):
    success = await conversation_service.delete_conversation(db, conversation_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return {"status": "success", "message": "Conversation deleted"}
