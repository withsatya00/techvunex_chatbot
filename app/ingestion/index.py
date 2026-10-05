import os
import json
import asyncio
from app.core.database import init_db
from app.rag.pipeline import rag_pipeline
from app.core.logging import logger

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "knowledge_base")
INPUT_FILE = os.path.join(DATA_DIR, "crawled_docs.json")

async def run_index():
    """
    Indexes crawled documents into the database, vector store, and BM25 search.
    """
    logger.info("Initializing database...")
    await init_db()

    if not os.path.exists(INPUT_FILE):
        logger.warning(f"{INPUT_FILE} not found. Running crawler first...")
        from app.ingestion.crawl import run_crawl
        await run_crawl()

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        docs = json.load(f)

    logger.info(f"Indexing {len(docs)} documents into Knowledge Base...")
    result = await rag_pipeline.ingest_documents(docs)

    print("\n================ INDEXING REPORT ================")
    print(f"Status: {result['status']}")
    print(f"Documents Indexed: {result['documents_indexed']}")
    print(f"Chunks Indexed: {result['chunks_indexed']}")
    print(f"Vector Store Size: {len(result['urls'])} documents")
    print("=================================================\n")

if __name__ == "__main__":
    asyncio.run(run_index())
