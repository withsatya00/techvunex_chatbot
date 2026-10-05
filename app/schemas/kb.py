from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class DocumentChunkResponse(BaseModel):
    id: str
    chunk_index: int
    content: str
    metadata_info: Dict[str, Any] = {}

    model_config = ConfigDict(from_attributes=True)

class DocumentResponse(BaseModel):
    id: str
    url: str
    title: str
    content_length: int
    chunks_count: int
    created_at: datetime
    updated_at: datetime
    metadata_info: Dict[str, Any] = {}

    model_config = ConfigDict(from_attributes=True)

class IngestRequest(BaseModel):
    base_url: Optional[str] = "https://techvunex.in/"
    max_pages: Optional[int] = 50

class IngestResponse(BaseModel):
    status: str
    pages_crawled: int
    chunks_indexed: int
    documents: List[str] = []
