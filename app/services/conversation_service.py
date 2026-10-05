from typing import Optional, List, Dict, Any
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.conversation import Conversation
from app.models.message import Message

class ConversationService:
    @staticmethod
    async def get_or_create_conversation(session: AsyncSession, session_id: str, title: str = "New Conversation") -> Conversation:
        stmt = select(Conversation).where(Conversation.session_id == session_id)
        res = await session.execute(stmt)
        conv = res.scalar_one_or_none()
        if not conv:
            conv = Conversation(session_id=session_id, title=title)
            session.add(conv)
            await session.commit()
            await session.refresh(conv)
        return conv

    @staticmethod
    async def add_message(
        session: AsyncSession,
        conversation_id: str,
        role: str,
        content: str,
        sources: List[Dict[str, Any]] = None,
        token_usage: Dict[str, Any] = None
    ) -> Message:
        msg = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            sources=sources or [],
            token_usage=token_usage or {}
        )
        session.add(msg)
        await session.commit()
        return msg

    @staticmethod
    async def add_messages(
        session: AsyncSession,
        conversation_id: str,
        messages_data: List[Dict[str, Any]]
    ) -> List[Message]:
        """Add multiple messages in a single database transaction for lower latency"""
        created = []
        for m in messages_data:
            msg = Message(
                conversation_id=conversation_id,
                role=m["role"],
                content=m["content"],
                sources=m.get("sources") or [],
                token_usage=m.get("token_usage") or {}
            )
            session.add(msg)
            created.append(msg)
        await session.commit()
        return created

    @staticmethod
    async def get_conversation_history(session: AsyncSession, conversation_id: str, limit: int = 10) -> List[Dict[str, str]]:
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        res = await session.execute(stmt)
        messages = res.scalars().all()
        # Return chronological order
        return [{"role": m.role, "content": m.content} for m in reversed(messages)]

    @staticmethod
    async def list_conversations(session: AsyncSession, limit: int = 50, offset: int = 0) -> List[Conversation]:
        stmt = (
            select(Conversation)
            .order_by(Conversation.updated_at.desc())
            .offset(offset)
            .limit(limit)
        )
        res = await session.execute(stmt)
        return res.scalars().all()

    @staticmethod
    async def delete_conversation(session: AsyncSession, conversation_id: str) -> bool:
        stmt = delete(Conversation).where(Conversation.id == conversation_id)
        res = await session.execute(stmt)
        await session.commit()
        return res.rowcount > 0

conversation_service = ConversationService()
