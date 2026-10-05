import time
import uuid
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from app.config import settings
from app.core.logging import logger
from app.core.database import init_db
from app.core.security import rate_limiter
from app.rag.pipeline import rag_pipeline
from app.rag.embeddings import embedding_service
from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.conversations import router as conv_router
from app.api.leads import router as leads_router
from app.api.feedback import router as feedback_router
from app.api.kb import router as kb_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    await init_db()
    await rag_pipeline.load_index()
    # Pre-warm neural embedding model in thread pool so the very first user message avoids cold start latency
    import asyncio
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, embedding_service._get_st_model)
    logger.info("Knowledge base index and embedding model pre-warmed and ready.")
    yield
    # Shutdown
    logger.info("Shutting down application...")

app = FastAPI(
    title="Techvunex AI Website Assistant & RAG API",
    description="Production-Ready AI Chatbot, Sales Assistant, and Lead Qualification System for Techvunex Innovation.",
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request ID & Observability Middleware
@app.middleware("http")
async def observability_and_ratelimit_middleware(request: Request, call_next):
    req_id = str(uuid.uuid4())
    start_time = time.time()
    
    # Rate Limiting check
    client_ip = request.client.host if request.client else "unknown"
    if not rate_limiter.is_allowed(client_ip):
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"detail": "Rate limit exceeded. Please try again in a minute."}
        )

    # Process request
    response = await call_next(request)
    latency_ms = (time.time() - start_time) * 1000

    response.headers["X-Request-ID"] = req_id
    response.headers["X-Response-Time-MS"] = f"{latency_ms:.2f}"

    # Log non-static requests
    if not request.url.path.startswith("/static"):
        logger.info(
            f"{request.method} {request.url.path} -> {response.status_code} ({latency_ms:.2f}ms)",
            extra={
                "request_id": req_id,
                "client_ip": client_ip,
                "latency_ms": latency_ms,
                "status_code": response.status_code
            }
        )

    return response

# Mount API Routers
api_v1 = FastAPI()
api_v1.include_router(auth_router)
api_v1.include_router(chat_router)
api_v1.include_router(conv_router)
api_v1.include_router(leads_router)
api_v1.include_router(feedback_router)
api_v1.include_router(kb_router)

app.mount("/api/v1", api_v1)

# Health Check
@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "kb_loaded": rag_pipeline.is_initialized,
        "llm_provider": settings.LLM_PROVIDER,
        "environment": settings.ENVIRONMENT
    }

# Mount static files and frontend
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

@app.get("/widget.js", tags=["Frontend Widget"])
async def serve_widget_js():
    widget_path = os.path.join(frontend_dir, "components", "ChatWidget", "widget.js")
    if os.path.exists(widget_path):
        return FileResponse(widget_path, media_type="application/javascript")
    return Response(content="// Widget script pending", media_type="application/javascript")

@app.get("/admin", tags=["Admin Dashboard"])
async def serve_admin():
    admin_index = os.path.join(frontend_dir, "admin", "index.html")
    if os.path.exists(admin_index):
        return FileResponse(admin_index, media_type="text/html")
    return Response(content="<h1>Admin Dashboard</h1>", media_type="text/html")

@app.get("/", tags=["Root"])
async def root():
    demo_page = os.path.join(frontend_dir, "demo.html")
    if os.path.exists(demo_page):
        return FileResponse(demo_page, media_type="text/html")
    return {
        "message": "Welcome to Techvunex AI Assistant API. Visit /docs for API documentation or /admin for Admin Dashboard."
    }
