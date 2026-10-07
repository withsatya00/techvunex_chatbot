import pytest
import pytest_asyncio
from httpx import AsyncClient
from app.main import app
from app.core.database import init_db
from app.rag.pipeline import rag_pipeline

@pytest_asyncio.fixture(scope="module", autouse=True)
async def setup_flow():
    await init_db()
    await rag_pipeline.load_index()

@pytest.mark.asyncio
async def test_multi_turn_chat_and_lead():
    session_id = "multi_turn_test_202"
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Turn 1: Inquire about website service
        r1 = await client.post("/api/v1/chat", json={
            "session_id": session_id,
            "message": "I want to build a website for my retail company."
        })
        assert r1.status_code == 200
        d1 = r1.json()
        assert "response" in d1
        assert d1["lead_intent"] is True

        # Turn 2: Provide contact and requirement details
        r2 = await client.post("/api/v1/chat", json={
            "session_id": session_id,
            "message": "My name is Rajesh from Smart Retail. Phone is 9876543210 and email rajesh@smartretail.in. Budget is 3 lakh."
        })
        assert r2.status_code == 200
        d2 = r2.json()
        assert "response" in d2

        # Verify lead created in DB
        leads_resp = await client.get("/api/v1/leads")
        assert leads_resp.status_code == 200
        leads = leads_resp.json()
        matching_lead = next((l for l in leads if l.get("email") == "rajesh@smartretail.in"), None)
        assert matching_lead is not None
        assert matching_lead["name"] == "Rajesh"
        assert matching_lead["status"] == "qualified"

@pytest.mark.asyncio
async def test_streaming_chat_flow():
    session_id = "streaming_test_303"
    async with AsyncClient(app=app, base_url="http://test") as client:
        resp = await client.post("/api/v1/chat/stream", json={
            "session_id": session_id,
            "message": "Where is your office located?"
        })
        assert resp.status_code == 200
        body = resp.text
        assert "data: " in body
        assert "[DONE]" in body

@pytest.mark.asyncio
async def test_connect_with_team_preserves_name_and_phone():
    session_id = "handoff_flow_test_404"
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Turn 1: User provides name and phone
        r1 = await client.post("/api/v1/chat", json={
            "session_id": session_id,
            "message": "Hi, my name is Suman and my phone number is 9129453456. I need website development."
        })
        assert r1.status_code == 200

        # Turn 2: User requests to connect with team
        r2 = await client.post("/api/v1/chat", json={
            "session_id": session_id,
            "message": "Connect with Team"
        })
        assert r2.status_code == 200
        d2 = r2.json()
        # Verify official company phone number is in response
        assert "7834979979" in d2["response"]

        # Verify lead created in DB has name 'Suman' instead of 'Website Visitor'
        leads_resp = await client.get("/api/v1/leads")
        assert leads_resp.status_code == 200
        leads = leads_resp.json()
        matching_lead = next((l for l in leads if l.get("phone") == "9129453456"), None)
        assert matching_lead is not None
        assert matching_lead["name"] == "Suman"
        assert matching_lead["human_required"] is True
