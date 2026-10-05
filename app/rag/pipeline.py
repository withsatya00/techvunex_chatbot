import os
import json
import hashlib
from typing import List, Dict, Any, Optional
from sqlalchemy import select, delete
from app.core.database import AsyncSessionLocal
from app.models.document import Document, DocumentChunk
from app.rag.crawler import TechvunexCrawler
from app.rag.chunker import StructureAwareChunker
from app.rag.embeddings import embedding_service
from app.rag.vector_store import vector_store
from app.rag.bm25 import bm25_index
from app.rag.retriever import hybrid_retriever
from app.core.logging import logger

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "knowledge_base")
KB_CACHE_FILE = os.path.join(DATA_DIR, "indexed_kb.json")

class RAGPipeline:
    """
    Coordinates crawler, chunker, embeddings, vector store, and retriever.
    """
    def __init__(self):
        self.chunker = StructureAwareChunker()
        self.crawler = TechvunexCrawler()
        self.is_initialized = False

    async def ingest_documents(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Takes raw document dicts, chunks them, computes embeddings,
        saves to database, and indexes in VectorStore + BM25.
        """
        os.makedirs(DATA_DIR, exist_ok=True)
        total_chunks = []
        doc_records = []

        async with AsyncSessionLocal() as session:
            for doc in documents:
                url = doc["url"]
                title = doc["title"]
                content = doc["content"]
                content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
                metadata = doc.get("metadata", {})

                # Check if document already exists
                stmt = select(Document).where(Document.url == url)
                res = await session.execute(stmt)
                existing_doc = res.scalar_one_or_none()

                if existing_doc:
                    # Update content and clean old chunks
                    existing_doc.title = title
                    existing_doc.content = content
                    existing_doc.content_hash = content_hash
                    existing_doc.metadata_info = metadata
                    document_id = existing_doc.id
                    await session.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document_id))
                else:
                    new_doc = Document(
                        url=url,
                        title=title,
                        content=content,
                        content_hash=content_hash,
                        metadata_info=metadata
                    )
                    session.add(new_doc)
                    await session.flush()
                    document_id = new_doc.id

                # Generate structured chunks
                chunks = self.chunker.chunk_document(url, title, content, metadata)
                chunk_texts = [c["content"] for c in chunks]
                embeddings = embedding_service.embed_documents(chunk_texts)

                for idx, (chunk_data, emb) in enumerate(zip(chunks, embeddings)):
                    chunk_obj = DocumentChunk(
                        document_id=document_id,
                        chunk_index=idx,
                        content=chunk_data["content"],
                        embedding=emb,
                        metadata_info=chunk_data["metadata"]
                    )
                    session.add(chunk_obj)
                    await session.flush()

                    total_chunks.append({
                        "id": chunk_obj.id,
                        "document_id": document_id,
                        "chunk_index": idx,
                        "content": chunk_data["content"],
                        "embedding": emb,
                        "metadata": chunk_data["metadata"]
                    })

                doc_records.append(url)

            await session.commit()

        # Update in-memory vector store & BM25 index
        vector_store.clear()
        vector_store.add_chunks(total_chunks)
        bm25_index.index(total_chunks)

        # Cache indexed chunks to JSON for fast cold starts
        try:
            with open(KB_CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(total_chunks, f)
            logger.info(f"Persisted {len(total_chunks)} chunks to {KB_CACHE_FILE}")
        except Exception as e:
            logger.error(f"Failed to cache KB to file: {e}")

        self.is_initialized = True
        return {
            "status": "success",
            "documents_indexed": len(doc_records),
            "chunks_indexed": len(total_chunks),
            "urls": doc_records
        }

    async def load_index(self):
        """Load chunks from DB or JSON cache into vector store and BM25 index."""
        chunks = []
        try:
            async with AsyncSessionLocal() as session:
                stmt = select(DocumentChunk)
                res = await session.execute(stmt)
                db_chunks = res.scalars().all()
                for c in db_chunks:
                    chunks.append({
                        "id": c.id,
                        "document_id": c.document_id,
                        "chunk_index": c.chunk_index,
                        "content": c.content,
                        "embedding": c.embedding,
                        "metadata": c.metadata_info or {}
                    })
        except Exception as e:
            logger.warning(f"Could not load chunks from DB directly: {e}")

        # If DB had no chunks, try JSON cache
        if not chunks and os.path.exists(KB_CACHE_FILE):
            try:
                with open(KB_CACHE_FILE, "r", encoding="utf-8") as f:
                    chunks = json.load(f)
                logger.info(f"Loaded {len(chunks)} chunks from cache file.")
            except Exception as e:
                logger.error(f"Failed to load cache: {e}")

        # If DB and cache had no chunks, automatically ingest crawled_docs.json on first boot
        if not chunks:
            raw_docs_path = os.path.join(DATA_DIR, "crawled_docs.json")
            if os.path.exists(raw_docs_path):
                logger.info("First-boot setup: Ingesting knowledge base from crawled_docs.json...")
                try:
                    with open(raw_docs_path, "r", encoding="utf-8") as f:
                        docs = json.load(f)
                    res = await self.ingest_documents(docs)
                    logger.info(f"Knowledge base auto-ingestion completed: {res['chunks_indexed']} chunks indexed.")
                    return
                except Exception as e:
                    logger.error(f"Failed to auto-ingest crawled_docs.json: {e}")

        if chunks:
            vector_store.clear()
            vector_store.add_chunks(chunks)
            bm25_index.index(chunks)
            self.is_initialized = True
            logger.info(f"RAG Pipeline index successfully loaded with {len(chunks)} chunks.")
        else:
            logger.warning("RAG Pipeline index is empty. Knowledge base ingestion required.")

    def search_context(self, query: str, top_k: int = 4, intent: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve most relevant context chunks for a query with optional intent routing"""
        if not self.is_initialized and os.path.exists(KB_CACHE_FILE):
            try:
                with open(KB_CACHE_FILE, "r", encoding="utf-8") as f:
                    cached_chunks = json.load(f)
                vector_store.clear()
                vector_store.add_chunks(cached_chunks)
                bm25_index.index(cached_chunks)
                self.is_initialized = True
                logger.info(f"Auto-loaded {len(cached_chunks)} chunks into RAG pipeline.")
            except Exception as e:
                logger.warning(f"Could not auto-load KB cache: {e}")
        return hybrid_retriever.retrieve(query, top_k=top_k, intent=intent)

rag_pipeline = RAGPipeline()


