import os
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from app.config import settings
from app.core.logging import logger

Base = declarative_base()

def normalize_async_db_url(url: str) -> str:
    """Ensure async driver prefixes are present for SQLAlchemy asyncio."""
    if not url:
        return "sqlite+aiosqlite:///./techvunex.db"
    url = url.strip().strip('"').strip("'")
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://") and not url.startswith("postgresql+"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif url.startswith("mysql://") and not url.startswith("mysql+"):
        url = url.replace("mysql://", "mysql+asyncmy://", 1)
    elif "aiomysql" in url:
        url = url.replace("mysql+aiomysql://", "mysql+asyncmy://", 1)
    # Ensure localhost resolves to IPv4 loopback for reliable docker port forwarding
    if "@localhost:" in url:
        url = url.replace("@localhost:", "@127.0.0.1:")
    return url

# Choose database URL
raw_url = settings.DATABASE_URL
if os.getenv("USE_POSTGRES", "false").lower() == "true" and settings.POSTGRES_URL:
    raw_url = settings.POSTGRES_URL
elif "postgres" in raw_url.lower():
    raw_url = raw_url

db_url = normalize_async_db_url(raw_url)
logger.info(f"Connecting to database with driver: {db_url.split('://')[0]}")

engine_kwargs = {
    "echo": settings.DEBUG,
    "future": True,
}
# Only apply connection pooling settings to server databases (PostgreSQL/MySQL), not SQLite
if not db_url.startswith("sqlite"):
    engine_kwargs.update({
        "pool_recycle": 3600,
        "pool_size": 10,
        "max_overflow": 20,
    })
    # asyncpg on PostgreSQL supports pool_pre_ping cleanly
    if "postgresql" in db_url:
        engine_kwargs["pool_pre_ping"] = True

engine = create_async_engine(db_url, **engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()

async def init_db():
    """Create all tables asynchronously"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables initialized successfully.")
