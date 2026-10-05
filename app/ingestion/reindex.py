import asyncio
from app.ingestion.crawl import run_crawl
from app.ingestion.index import run_index
from app.core.logging import logger

async def run_reindex():
    """
    Performs full re-crawling and re-indexing of the Techvunex knowledge base.
    """
    logger.info("Executing full knowledge base re-indexing pipeline...")
    await run_crawl()
    await run_index()
    logger.info("Re-indexing completed successfully.")

if __name__ == "__main__":
    asyncio.run(run_reindex())
