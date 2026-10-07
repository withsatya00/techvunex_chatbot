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
    assert "<title>Techvunex AI Enquiry</title>" in html
    assert "Techvunex AI Enquiry</h2>" in html

    plain = notification_service._generate_email_plain(lead_data)
    assert "TECHVUNEX AI ENQUIRY" in plain
    assert "9129432906" in plain

def test_normalize_service_name():
    assert notification_service._normalize_service_name("website") == "Website Development"
    assert notification_service._normalize_service_name("crm") == "CRM & ERP Solutions"
    assert notification_service._normalize_service_name("erp") == "CRM & ERP Solutions"
    assert notification_service._normalize_service_name("ai chatbot") == "AI Automation"
    assert notification_service._normalize_service_name("mobile app") == "Mobile App Development"
    assert notification_service._normalize_service_name(None) == "Website Development"

@pytest.mark.asyncio
async def test_lead_email_subject_and_bcc():
    with patch.object(notification_service, "_send_via_resend") as mock_resend:
        mock_resend.return_value = True
        with patch.object(settings, "NOTIFICATION_EMAIL_BCC", "boss@techvunex.com, info@techvunex.in"):
            lead_data = {
                "name": "Arjun Kumar",
                "phone": "919198517600",
                "email": "trainee2@techvunex.in",
                "service": "Website Development"
            }
            res = await notification_service.send_lead_email(lead_data)
            assert res is True
            mock_resend.assert_called_once()
            call_args = mock_resend.call_args
            subject = call_args[0][1]
            bcc = call_args[1]["bcc"]
            assert subject == "Techvunex AI: Website Development"
            assert "boss@techvunex.com" in bcc
            assert "info@techvunex.in" in bcc

@pytest.mark.asyncio
async def test_dispatch_lead_notification_skips_when_no_contact():
    # If no phone or email, should do nothing
    with patch.object(notification_service, "send_lead_email") as mock_email:
        await notification_service.dispatch_lead_notification({"name": "Anonymous", "requirement": "Hello"})
        mock_email.assert_not_called()

@pytest.mark.asyncio
async def test_lead_email_skips_without_mobile_number():
    with patch.object(notification_service, "_send_via_resend") as mock_resend:
        # Without mobile number, send_lead_email must return False and not send
        res = await notification_service.send_lead_email({
            "name": "Suman",
            "email": "suman@example.com",
            "service": "Website Development"
        })
        assert res is False
        mock_resend.assert_not_called()

@pytest.mark.asyncio
async def test_send_lead_email_graceful_when_disabled():
    with patch.object(settings, "NOTIFICATION_EMAIL_ENABLED", False):
        result = await notification_service.send_lead_email({"phone": "9129432906", "name": "Test"})
        assert result is False
