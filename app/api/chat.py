from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import chat_service
from app.core.exceptions import PromptInjectionError, LLMProviderError

router = APIRouter(prefix="/chat", tags=["Chat"])

@router.post("", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest, db: AsyncSession = Depends(get_db)):
    """
    Standard synchronous chat endpoint.
    Retrieves context, qualifies leads, checks human handoff, and returns structured answer.
    """
    try:
        response = await chat_service.process_chat(
            session=db,
            session_id=req.session_id,
            user_message=req.message,
            language_preference=req.language or "auto"
        )
        return response
    except PromptInjectionError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except LLMProviderError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.post("/stream")
async def chat_stream_endpoint(req: ChatRequest, db: AsyncSession = Depends(get_db)):
    """
    Server-Sent Events (SSE) streaming chat endpoint.
    Streams tokens in real-time followed by metadata and sources.
    """
    try:
        generator = chat_service.stream_chat(
            session=db,
            session_id=req.session_id,
            user_message=req.message,
            language_preference=req.language or "auto"
        )
        return StreamingResponse(
            generator,
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
    except PromptInjectionError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
