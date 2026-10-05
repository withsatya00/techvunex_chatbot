import pytest
import pytest_asyncio
from httpx import AsyncClient
from app.main import app
from app.core.database import init_db
from app.rag.pipeline import rag_pipeline
from app.config import settings

@pytest.fixture(scope="session", autouse=True)
def anyio_backend():
    return "asyncio"

@pytest_asyncio.fixture(scope="module", autouse=True)
async def setup_test_system():
    await init_db()
    await rag_pipeline.load_index()

@pytest.mark.asyncio
async def test_health_endpoint():
    async with AsyncClient(app=app, base_url="http://test") as client:
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert "Techvunex" in data["app"]

@pytest.mark.asyncio
async def test_chat_endpoint():
    async with AsyncClient(app=app, base_url="http://test") as client:
        payload = {
            "session_id": "test_session_101",
            "message": "Do you provide CRM & ERP development?"
        }
        resp = await client.post("/api/v1/chat", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert "response" in data
        assert len(data["sources"]) > 0
        assert data["session_id"] == "test_session_101"

@pytest.mark.asyncio
async def test_auth_login():
    async with AsyncClient(app=app, base_url="http://test") as client:
        payload = {
            "username": settings.ADMIN_USERNAME,
            "password": settings.ADMIN_PASSWORD
        }
        resp = await client.post("/api/v1/auth/login", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

@pytest.mark.asyncio
async def test_leads_lifecycle():
    async with AsyncClient(app=app, base_url="http://test") as client:
        lead_payload = {
            "name": "Priya Sharma",
            "email": "priya@techcorp.in",
            "phone": "+919876543210",
            "company": "Tech Corp",
            "service": "AI Automation",
            "requirement": "Build RAG chatbot for customer support"
        }
        # Create lead
        create_resp = await client.post("/api/v1/leads", json=lead_payload)
        assert create_resp.status_code == 200
        lead_data = create_resp.json()
        assert lead_data["name"] == "Priya Sharma"
        lead_id = lead_data["id"]

        # List leads
        list_resp = await client.get("/api/v1/leads")
        assert list_resp.status_code == 200
        leads = list_resp.json()
        assert any(l["id"] == lead_id for l in leads)

@pytest.mark.asyncio
async def test_feedback_endpoint():
    async with AsyncClient(app=app, base_url="http://test") as client:
        fb_payload = {
            "conversation_id": "test_session_101",
            "rating": 1,
            "feedback": "Super fast and accurate!"
        }
        resp = await client.post("/api/v1/feedback", json=fb_payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["rating"] == 1

@pytest.mark.asyncio
async def test_kb_documents():
    async with AsyncClient(app=app, base_url="http://test") as client:
        resp = await client.get("/api/v1/kb/documents")
        assert resp.status_code == 200
        docs = resp.json()
        assert len(docs) > 0
