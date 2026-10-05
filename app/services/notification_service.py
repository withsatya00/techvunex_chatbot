import asyncio
import re
import smtplib
import time
import urllib.parse
from email.message import EmailMessage
from typing import Dict, Any, Optional
import httpx

from app.config import settings
from app.core.logging import logger

class NotificationService:
    """
    100% Free Lead Notification Service.
    Supports:
    1. Email alerts via standard Python SMTP (Gmail 500/day free or cPanel/Webmail).
    2. One-click WhatsApp action links embedded in all notifications (₹0 cost).
    3. Direct Telegram bot push notifications (100% free, instant mobile sound alerts).
    4. WhatsApp Cloud API (Meta Official Free Tier: 1,000 conversations/month).
    """

    def __init__(self):
        # Debounce tracking: {lead_identifier: timestamp} to prevent duplicate notifications
        self._last_notified: Dict[str, float] = {}
        self._debounce_window_seconds = 45.0

    def _clean_phone_for_whatsapp(self, phone: Optional[str]) -> str:
        """Extract only digits and ensure country code format for WhatsApp URL."""
        if not phone:
            return ""
        digits = re.sub(r"\D", "", phone)
        # If 10 digits (Indian mobile), prefix 91
        if len(digits) == 10:
            return f"91{digits}"
        return digits

    def _build_whatsapp_link(self, phone: Optional[str], name: Optional[str], service: Optional[str]) -> str:
        """Generate a 1-click WhatsApp deep link with pre-filled professional message."""
        clean_phone = self._clean_phone_for_whatsapp(phone)
        if not clean_phone:
            return ""
        customer_name = name or "there"
        srv = service or "project requirement"
        message_text = f"Hello {customer_name}! Techvunex Innovation team se hum aapki website & {srv} enquiry ke regarding connect kar rahe hain. Would you be available for a brief discussion?"
        encoded = urllib.parse.quote(message_text)
        return f"https://wa.me/{clean_phone}?text={encoded}"

    def _generate_email_html(self, lead_data: Dict[str, Any]) -> str:
        name = lead_data.get("name") or "Website Visitor"
        phone = lead_data.get("phone") or "Not provided"
        email = lead_data.get("email") or "Not provided"
        service = lead_data.get("service") or "General Inquiry"
        company = lead_data.get("company") or "Not specified"
        budget = lead_data.get("budget") or "Not discussed"
        timeline = lead_data.get("timeline") or "Immediate"
        requirement = lead_data.get("requirement") or "Customer enquired via AI chatbot"
        human_req = lead_data.get("human_required", False)
        created_at = lead_data.get("created_at") or time.strftime("%d %b %Y, %I:%M %p IST")

        wa_link = self._build_whatsapp_link(lead_data.get("phone"), lead_data.get("name"), lead_data.get("service"))

        priority_badge = """<span style="background-color: #ef4444; color: #ffffff; padding: 4px 10px; border-radius: 9999px; font-weight: bold; font-size: 12px;">🚨 URGENT: Human Agent Requested</span>""" if human_req else """<span style="background-color: #10b981; color: #ffffff; padding: 4px 10px; border-radius: 9999px; font-weight: bold; font-size: 12px;">✅ Qualified Lead</span>"""

        wa_button = ""
        if wa_link:
            wa_button = f"""
            <a href="{wa_link}" target="_blank" style="display: inline-block; background-color: #25D366; color: #ffffff; text-decoration: none; padding: 12px 24px; border-radius: 8px; font-weight: 600; font-size: 14px; margin-right: 12px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
                💬 Open WhatsApp Chat with Lead
            </a>
            """

        phone_call_button = ""
        if phone != "Not provided":
            phone_call_button = f"""
            <a href="tel:{phone}" style="display: inline-block; background-color: #4f46e5; color: #ffffff; text-decoration: none; padding: 12px 24px; border-radius: 8px; font-weight: 600; font-size: 14px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
                📞 Call Customer ({phone})
            </a>
            """

        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>New Lead Captured - Techvunex Innovation</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f3f4f6; margin: 0; padding: 24px;">
    <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1); border: 1px solid #e5e7eb;">
        <!-- Header -->
        <div style="background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%); padding: 28px 24px; text-align: center;">
            <h1 style="color: #ffffff; margin: 0 0 6px 0; font-size: 22px; font-weight: 700; letter-spacing: -0.5px;">Techvunex Innovation</h1>
            <p style="color: #94a3b8; margin: 0; font-size: 14px;">🚀 AI Assistant Lead Alert</p>
        </div>

        <!-- Body -->
        <div style="padding: 28px 24px;">
            <div style="margin-bottom: 20px; display: flex; align-items: center;">
                {priority_badge}
                <span style="color: #64748b; font-size: 13px; margin-left: auto;">{created_at}</span>
            </div>

            <h2 style="color: #1e293b; font-size: 18px; margin: 0 0 16px 0; border-bottom: 2px solid #f1f5f9; padding-bottom: 8px;">Lead Contact Details</h2>

            <table style="width: 100%; border-collapse: collapse; margin-bottom: 24px;">
                <tr>
                    <td style="padding: 10px 0; color: #64748b; font-size: 14px; width: 35%;">Customer Name:</td>
                    <td style="padding: 10px 0; color: #0f172a; font-size: 15px; font-weight: 600;">{name}</td>
                </tr>
                <tr style="border-top: 1px solid #f8fafc;">
                    <td style="padding: 10px 0; color: #64748b; font-size: 14px;">Phone Number:</td>
                    <td style="padding: 10px 0; color: #0f172a; font-size: 15px; font-weight: 600;"><a href="tel:{phone}" style="color: #4f46e5; text-decoration: none;">{phone}</a></td>
                </tr>
                <tr style="border-top: 1px solid #f8fafc;">
                    <td style="padding: 10px 0; color: #64748b; font-size: 14px;">Email:</td>
                    <td style="padding: 10px 0; color: #0f172a; font-size: 14px;"><a href="mailto:{email}" style="color: #4f46e5; text-decoration: none;">{email}</a></td>
                </tr>
                <tr style="border-top: 1px solid #f8fafc;">
                    <td style="padding: 10px 0; color: #64748b; font-size: 14px;">Company / Business:</td>
                    <td style="padding: 10px 0; color: #0f172a; font-size: 14px;">{company}</td>
                </tr>
                <tr style="border-top: 1px solid #f8fafc;">
                    <td style="padding: 10px 0; color: #64748b; font-size: 14px;">Requested Service:</td>
                    <td style="padding: 10px 0; color: #4338ca; font-size: 14px; font-weight: 600;">{service}</td>
                </tr>
                <tr style="border-top: 1px solid #f8fafc;">
                    <td style="padding: 10px 0; color: #64748b; font-size: 14px;">Stated Budget:</td>
                    <td style="padding: 10px 0; color: #059669; font-size: 14px; font-weight: 600;">{budget}</td>
                </tr>
                <tr style="border-top: 1px solid #f8fafc;">
                    <td style="padding: 10px 0; color: #64748b; font-size: 14px;">Expected Timeline:</td>
                    <td style="padding: 10px 0; color: #0f172a; font-size: 14px;">{timeline}</td>
                </tr>
            </table>

            <h2 style="color: #1e293b; font-size: 16px; margin: 0 0 10px 0;">Customer Requirements / Discussion</h2>
            <div style="background-color: #f8fafc; border-left: 4px solid #4f46e5; padding: 14px 16px; border-radius: 4px; font-size: 14px; color: #334155; line-height: 1.5; margin-bottom: 24px;">
                {requirement}
            </div>

            <!-- Quick Action Buttons -->
            <div style="margin: 28px 0 10px 0; text-align: center;">
                {wa_button}
                {phone_call_button}
            </div>
        </div>

        <!-- Footer -->
        <div style="background-color: #f8fafc; padding: 16px 24px; text-align: center; border-top: 1px solid #e2e8f0; font-size: 12px; color: #94a3b8;">
            Techvunex Innovation • Sector 63, Noida, UP (A Subsidiary of Digital Yug Innovation)<br>
            Official AI Assistant Automation System • Instant Lead Notification
        </div>
    </div>
</body>
</html>
"""

    def _generate_email_plain(self, lead_data: Dict[str, Any]) -> str:
        name = lead_data.get("name") or "Website Visitor"
        phone = lead_data.get("phone") or "Not provided"
        email = lead_data.get("email") or "Not provided"
        service = lead_data.get("service") or "General Inquiry"
        budget = lead_data.get("budget") or "Not discussed"
        req = lead_data.get("requirement") or "Customer enquired via AI chatbot"
        wa_link = self._build_whatsapp_link(lead_data.get("phone"), lead_data.get("name"), lead_data.get("service"))

        return f"""TECHVUNEX INNOVATION - NEW LEAD CAPTURED
============================================
Name: {name}
Phone: {phone}
Email: {email}
Service: {service}
Budget: {budget}
Requirement: {req}
Human Agent Requested: {lead_data.get('human_required', False)}

1-Click WhatsApp Link:
{wa_link}
============================================
"""

    def _sync_send_smtp(self, msg: EmailMessage) -> bool:
        """Send email synchronously using smtplib (to be run via asyncio.to_thread)."""
        try:
            if settings.SMTP_PORT == 465 or not settings.SMTP_USE_TLS:
                server = smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=12)
            else:
                server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=12)
                server.starttls()

            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)

            server.send_message(msg)
            server.quit()
            return True
        except Exception as e:
            logger.error(f"Failed to send lead email notification via SMTP: {e}")
            return False

    async def send_lead_email(self, lead_data: Dict[str, Any]) -> bool:
        """Sends lead alert email asynchronously via Python standard smtplib."""
        if not settings.NOTIFICATION_EMAIL_ENABLED:
            logger.debug("Email notification skipped: NOTIFICATION_EMAIL_ENABLED is False")
            return False

        if not settings.SMTP_USER or not settings.SMTP_PASSWORD or not settings.NOTIFICATION_EMAIL_TO:
            logger.warning("Email notification skipped: Missing SMTP_USER, SMTP_PASSWORD, or NOTIFICATION_EMAIL_TO")
            return False

        try:
            recipients = [r.strip() for r in settings.NOTIFICATION_EMAIL_TO.split(",") if r.strip()]
            if not recipients:
                return False

            lead_name = lead_data.get("name") or "Website Visitor"
            service = lead_data.get("service") or "Inquiry"
            phone = lead_data.get("phone") or "No Phone"

            msg = EmailMessage()
            msg["Subject"] = f"🚀 New Lead: {lead_name} - {service} ({phone})"
            msg["From"] = settings.SMTP_USER
            msg["To"] = ", ".join(recipients)

            plain_content = self._generate_email_plain(lead_data)
            html_content = self._generate_email_html(lead_data)

            msg.set_content(plain_content)
            msg.add_alternative(html_content, subtype="html")

            success = await asyncio.to_thread(self._sync_send_smtp, msg)
            if success:
                logger.info(f"Successfully sent lead notification email to {recipients}")
            return success
        except Exception as e:
            logger.error(f"Error in send_lead_email: {e}")
            return False

    async def send_telegram_alert(self, lead_data: Dict[str, Any]) -> bool:
        """Sends lead notification via Telegram Bot API (100% Free, instant push notification)."""
        if not settings.TELEGRAM_NOTIFICATIONS_ENABLED or not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID:
            return False

        try:
            name = lead_data.get("name") or "Website Visitor"
            phone = lead_data.get("phone") or "Not provided"
            email = lead_data.get("email") or "Not provided"
            service = lead_data.get("service") or "General Inquiry"
            budget = lead_data.get("budget") or "Not specified"
            req = lead_data.get("requirement") or "Captured from website chat"
            wa_link = self._build_whatsapp_link(lead_data.get("phone"), lead_data.get("name"), lead_data.get("service"))

            text = (
                f"🚀 *TECHVUNEX NEW LEAD CAPTURED* 🚀\n\n"
                f"👤 *Name:* {name}\n"
                f"📞 *Phone:* {phone}\n"
                f"📧 *Email:* {email}\n"
                f"💼 *Service:* {service}\n"
                f"💰 *Budget:* {budget}\n"
                f"📝 *Requirement:* {req}\n"
                f"⚡ *Human Agent Needed:* {'YES' if lead_data.get('human_required') else 'No'}\n\n"
            )
            if wa_link:
                text += f"💬 [Click to Chat on WhatsApp]({wa_link})\n"

            telegram_url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
            payload = {
                "chat_id": settings.TELEGRAM_CHAT_ID,
                "text": text,
                "parse_mode": "Markdown",
                "disable_web_page_preview": False
            }

            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(telegram_url, json=payload)
                if res.status_code == 200:
                    logger.info("Successfully sent lead alert to Telegram")
                    return True
                else:
                    logger.error(f"Telegram alert failed with status {res.status_code}: {res.text}")
                    return False
        except Exception as e:
            logger.error(f"Error sending Telegram lead alert: {e}")
            return False

    async def send_whatsapp_alert(self, lead_data: Dict[str, Any]) -> bool:
        """Sends WhatsApp notification via Meta WhatsApp Cloud API (Free tier: 1,000 conversations/month)."""
        if not settings.WHATSAPP_NOTIFICATIONS_ENABLED or not settings.WHATSAPP_API_TOKEN or not settings.WHATSAPP_PHONE_NUMBER_ID or not settings.WHATSAPP_RECIPIENT_PHONE:
            return False

        try:
            name = lead_data.get("name") or "Website Visitor"
            phone = lead_data.get("phone") or "Not provided"
            service = lead_data.get("service") or "General Inquiry"
            budget = lead_data.get("budget") or "Not specified"

            meta_url = f"https://graph.facebook.com/v18.0/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
            headers = {
                "Authorization": f"Bearer {settings.WHATSAPP_API_TOKEN}",
                "Content-Type": "application/json"
            }
            recipient = self._clean_phone_for_whatsapp(settings.WHATSAPP_RECIPIENT_PHONE)
            msg_body = f"🚀 *New Lead on Techvunex AI*\nName: {name}\nPhone: {phone}\nService: {service}\nBudget: {budget}"

            payload = {
                "messaging_product": "whatsapp",
                "to": recipient,
                "type": "text",
                "text": {"preview_url": False, "body": msg_body}
            }

            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(meta_url, headers=headers, json=payload)
                if res.status_code in (200, 201):
                    logger.info(f"Successfully sent WhatsApp alert to {recipient}")
                    return True
                else:
                    logger.error(f"WhatsApp Cloud API alert failed: {res.text}")
                    return False
        except Exception as e:
            logger.error(f"Error sending WhatsApp Cloud API alert: {e}")
            return False

    async def dispatch_lead_notification(self, lead_data: Dict[str, Any]) -> None:
        """
        Dispatches notifications to all enabled channels.
        Includes debouncing to prevent flooding on repeated updates within the same minute.
        """
        phone = lead_data.get("phone")
        email = lead_data.get("email")

        # Only dispatch if at least one contact channel is present
        if not phone and not email:
            logger.debug("Notification skipped: No phone or email captured yet.")
            return

        # Debounce check
        identifier = phone or email or lead_data.get("id", "")
        now = time.time()
        last_time = self._last_notified.get(identifier, 0.0)

        if (now - last_time) < self._debounce_window_seconds:
            logger.debug(f"Notification debounced for identifier {identifier}")
            return

        self._last_notified[identifier] = now

        # Fire notification tasks in background
        tasks = []
        if settings.NOTIFICATION_EMAIL_ENABLED:
            tasks.append(asyncio.create_task(self.send_lead_email(lead_data)))
        if settings.TELEGRAM_NOTIFICATIONS_ENABLED:
            tasks.append(asyncio.create_task(self.send_telegram_alert(lead_data)))
        if settings.WHATSAPP_NOTIFICATIONS_ENABLED:
            tasks.append(asyncio.create_task(self.send_whatsapp_alert(lead_data)))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

notification_service = NotificationService()
