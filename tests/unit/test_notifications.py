import pytest
from unittest.mock import patch, MagicMock
from app.services.notification_service import notification_service
from app.config import settings

def test_clean_phone_for_whatsapp():
    assert notification_service._clean_phone_for_whatsapp("9129432906") == "919129432906"
    assert notification_service._clean_phone_for_whatsapp("+91 91294 32906") == "919129432906"
    assert notification_service._clean_phone_for_whatsapp("919129432906") == "919129432906"
    assert notification_service._clean_phone_for_whatsapp("") == ""
    assert notification_service._clean_phone_for_whatsapp(None) == ""

def test_build_whatsapp_link():
    link = notification_service._build_whatsapp_link("9129432906", "Shivam", "Website Development")
    assert "https://wa.me/919129432906" in link
    assert "Shivam" in link
    assert "Website%20Development" in link

def test_generate_email_content():
    lead_data = {
        "name": "Shivam",
        "phone": "9129432906",
        "email": "shivam@example.com",
        "company": "Shivam Enterprises",
        "service": "Website Development",
        "requirement": "I need a fast ecommerce store with online payments",
        "budget": "₹50,000",
        "timeline": "1 month",
        "human_required": True
    }
    
    html = notification_service._generate_email_html(lead_data)
    assert "Shivam" in html
    assert "9129432906" in html
    assert "shivam@example.com" in html
    assert "URGENT: Human Agent Requested" in html
    assert "https://wa.me/919129432906" in html

    plain = notification_service._generate_email_plain(lead_data)
    assert "TECHVUNEX INNOVATION - NEW LEAD CAPTURED" in plain
    assert "9129432906" in plain

@pytest.mark.asyncio
async def test_dispatch_lead_notification_skips_when_no_contact():
    # If no phone or email, should do nothing
    with patch.object(notification_service, "send_lead_email") as mock_email:
        await notification_service.dispatch_lead_notification({"name": "Anonymous", "requirement": "Hello"})
        mock_email.assert_not_called()

@pytest.mark.asyncio
async def test_send_lead_email_graceful_when_disabled():
    with patch.object(settings, "NOTIFICATION_EMAIL_ENABLED", False):
        result = await notification_service.send_lead_email({"phone": "9129432906", "name": "Test"})
        assert result is False
