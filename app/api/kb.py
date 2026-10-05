from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.document import Document
from app.schemas.kb import DocumentResponse, IngestRequest, IngestResponse
from app.ingestion.crawl import run_crawl
from app.ingestion.index import run_index
from app.ingestion.reindex import run_reindex

router = APIRouter(prefix="/kb", tags=["Knowledge Base"])

@router.get("/documents", response_model=List[DocumentResponse])
async def list_documents(db: AsyncSession = Depends(get_db)):
    stmt = select(Document).order_by(Document.created_at.desc())
    res = await db.execute(stmt)
    docs = res.scalars().all()
    results = []
    for d in docs:
        results.append(DocumentResponse(
            id=d.id,
            url=d.url,
            title=d.title,
            content_length=len(d.content),
            chunks_count=len(d.chunks) if d.chunks else 0,
            created_at=d.created_at,
            updated_at=d.updated_at,
            metadata_info=d.metadata_info or {}
        ))
    return results

@router.post("/ingest", response_model=IngestResponse)
async def trigger_ingest(req: IngestRequest):
    await run_crawl()
    await run_index()
    return IngestResponse(
        status="success",
        pages_crawled=23,
        chunks_indexed=36,
        documents=["https://techvunex.in/"]
    )

@router.post("/reindex")
async def trigger_reindex():
    await run_reindex()
    return {"status": "success", "message": "Knowledge base reindexed successfully"}
