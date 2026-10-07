import asyncio
import re
import smtplib
import time
import urllib.parse
from email.message import EmailMessage
from typing import Dict, Any, Optional, List
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

    def _normalize_service_name(self, raw_service: Optional[str]) -> str:
        """Normalizes requested service to standard display name matching Techvunex offerings."""
        if not raw_service:
            return "Website Development"
        s = raw_service.strip()
        s_lower = s.lower()
        if "crm" in s_lower or "erp" in s_lower:
            return "CRM & ERP Solutions"
        if "ai" in s_lower or "chatbot" in s_lower:
            return "AI Automation"
        if "mobile" in s_lower or "app" in s_lower:
            return "Mobile App Development"
        if "seo" in s_lower or "smo" in s_lower:
            return "Digital Marketing & SEO"
        if "custom software" in s_lower or "software" in s_lower:
            return "Custom Software Development"
        if "ui" in s_lower or "ux" in s_lower:
            return "UI/UX Design"
        if "cloud" in s_lower:
            return "Cloud Solutions"
        if any(k in s_lower for k in ["website", "web", "ecommerce", "e-commerce", "landing page", "saas", "free"]):
            return "Website Development"
        return s

    def _generate_email_html(self, lead_data: Dict[str, Any]) -> str:
        name = lead_data.get("name") or "Website Visitor"
        phone = lead_data.get("phone") or "Not provided"
        email = lead_data.get("email") or "Not provided"
        raw_service = lead_data.get("service")
        service = self._normalize_service_name(raw_service)
        company = lead_data.get("company") or "Not specified"
        budget = lead_data.get("budget")
        timeline = lead_data.get("timeline")
        raw_requirement = lead_data.get("requirement") or "Customer enquired via AI chatbot"
        human_req = lead_data.get("human_required", False)

        msg_extra = []
        if raw_requirement and raw_requirement != "Customer enquired via AI chatbot":
            msg_extra.append(raw_requirement)
        if budget and budget != "Not discussed":
            msg_extra.append(f"Budget: {budget}")
        if timeline and timeline != "Immediate":
            msg_extra.append(f"Timeline: {timeline}")

        detail_msg = " | ".join(msg_extra) if msg_extra else raw_requirement
        message_display = f"Service: {service} {detail_msg}".strip()

        wa_link = self._build_whatsapp_link(lead_data.get("phone"), lead_data.get("name"), service)

        priority_badge = ""
        if human_req:
            priority_badge = """<div style="margin-bottom: 16px;"><span style="background-color: #ef4444; color: #ffffff; padding: 4px 10px; border-radius: 9999px; font-weight: bold; font-size: 11.5px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">🚨 URGENT: Human Agent Requested</span></div>"""

        wa_button = ""
        if wa_link:
            wa_button = f"""
            <a href="{wa_link}" target="_blank" style="display: inline-block; background-color: #25D366; color: #ffffff; text-decoration: none; padding: 11px 20px; border-radius: 8px; font-weight: 600; font-size: 13.5px; margin: 4px 8px 4px 0; box-shadow: 0 4px 6px -1px rgba(37, 211, 102, 0.25); font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
                💬 Open WhatsApp Chat with Lead
            </a>
            """

        phone_call_button = ""
        if phone != "Not provided" and phone != "No Phone":
            phone_call_button = f"""
            <a href="tel:{phone}" style="display: inline-block; background-color: #6366f1; color: #ffffff; text-decoration: none; padding: 11px 20px; border-radius: 8px; font-weight: 600; font-size: 13.5px; margin: 4px 0; box-shadow: 0 4px 6px -1px rgba(99, 102, 241, 0.25); font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
                📞 Call Customer ({phone})
            </a>
            """

        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Techvunex AI Enquiry</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f1f5f9; margin: 0; padding: 24px;">
    <div style="max-width: 580px; margin: 0 auto; background-color: #ffffff; border-radius: 14px; overflow: hidden; box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.08); border: 1px solid #e2e8f0;">
        <!-- Header Banner (Vibrant Purple matching Techvunex Enquiry form) -->
        <div style="background: linear-gradient(135deg, #7c3aed 0%, #6d28d9 100%); padding: 24px 28px; text-align: left;">
            <h2 style="color: #ffffff; margin: 0 0 6px 0; font-size: 21px; font-weight: 700; letter-spacing: -0.2px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">Techvunex AI Enquiry</h2>
            <p style="color: rgba(255, 255, 255, 0.92); margin: 0; font-size: 13.5px; font-weight: 400; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">A new enquiry has been submitted on Techvunex.</p>
        </div>

        <!-- Body Section -->
        <div style="padding: 26px 28px 22px 28px;">
            {priority_badge}

            <table style="width: 100%; border-collapse: collapse; margin-bottom: 18px;">
                <tr>
                    <td style="padding: 6px 0; color: #0f172a; font-size: 14.5px; line-height: 1.5; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
                        <strong style="color: #0f172a; font-weight: 700;">Name:</strong> {name}
                    </td>
                </tr>
                <tr>
                    <td style="padding: 6px 0; color: #0f172a; font-size: 14.5px; line-height: 1.5; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
                        <strong style="color: #0f172a; font-weight: 700;">Email:</strong> <a href="mailto:{email}" style="color: #4f46e5; text-decoration: none;">{email}</a>
                    </td>
                </tr>
                <tr>
                    <td style="padding: 6px 0; color: #0f172a; font-size: 14.5px; line-height: 1.5; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
                        <strong style="color: #0f172a; font-weight: 700;">Phone:</strong> <a href="tel:{phone}" style="color: #4f46e5; text-decoration: none;">{phone}</a>
                    </td>
                </tr>
                <tr>
                    <td style="padding: 6px 0; color: #0f172a; font-size: 14.5px; line-height: 1.5; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
                        <strong style="color: #0f172a; font-weight: 700;">Company:</strong> {company}
                    </td>
                </tr>
                <tr>
                    <td style="padding: 6px 0; color: #0f172a; font-size: 14.5px; line-height: 1.5; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
                        <strong style="color: #0f172a; font-weight: 700;">Subject:</strong> {service}
                    </td>
                </tr>
            </table>

            <!-- Message Card (Lavender tint matching enquiry template) -->
            <div style="background-color: #f7f6fe; border: 1px solid #ede9fe; border-radius: 10px; padding: 16px 18px; margin-top: 14px; margin-bottom: 22px;">
                <div style="font-size: 14px; font-weight: 700; color: #0f172a; margin-bottom: 6px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">Message</div>
                <div style="font-size: 13.5px; color: #334155; line-height: 1.6; word-break: break-word; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
                    {message_display}
                </div>
            </div>

            <!-- Instant Follow-up Action Buttons -->
            <div style="margin: 18px 0 6px 0; text-align: left;">
                {wa_button}
                {phone_call_button}
            </div>
        </div>

        <!-- Footer -->
        <div style="background-color: #f8fafc; padding: 14px 24px; text-align: center; border-top: 1px solid #e2e8f0; font-size: 12px; color: #94a3b8; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
            Techvunex Innovation • Sector 63, Noida (A Subsidiary of Digital Yug Innovation)<br>
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
        raw_service = lead_data.get("service")
        service = self._normalize_service_name(raw_service)
        company = lead_data.get("company") or "Not specified"
        req = lead_data.get("requirement") or "Customer enquired via AI chatbot"
        wa_link = self._build_whatsapp_link(lead_data.get("phone"), lead_data.get("name"), service)

        return f"""TECHVUNEX AI ENQUIRY (NEW LEAD CAPTURED)
============================================
Name: {name}
Email: {email}
Phone: {phone}
Company: {company}
Subject: {service}

Message:
Service: {service} {req}

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

    async def _send_via_resend(
        self,
        recipients: List[str],
        subject: str,
        html_content: str,
        plain_content: str = "",
        reply_to: str = "info@techvunex.in",
        bcc: Optional[List[str]] = None
    ) -> bool:
        """
        Send email via Resend HTTP REST API over HTTPS Port 443.
        Includes multipart plain text, BCC support, and professional headers to ensure high inbox deliverability.
        """
        if not settings.RESEND_API_KEY:
            return False
        try:
            url = "https://api.resend.com/emails"
            headers = {
                "Authorization": f"Bearer {settings.RESEND_API_KEY}",
                "Content-Type": "application/json",
                "User-Agent": "TechvunexAI/1.0"
            }
            # For onboarding@resend.dev sandbox, Resend routes to account holder email
            target_recipients = recipients
            target_bcc = [b for b in (bcc or []) if b]
            if "onboarding@resend.dev" in settings.RESEND_FROM_EMAIL:
                target_recipients = [r for r in recipients if "techvunex.in" in r.lower()] or ["trainee4@techvunex.in"]
                target_bcc = [b for b in target_bcc if "techvunex.in" in b.lower()]

            from_display = f"Techvunex AI <{settings.RESEND_FROM_EMAIL}>" if "<" not in settings.RESEND_FROM_EMAIL else settings.RESEND_FROM_EMAIL

            payload = {
                "from": from_display,
                "to": target_recipients,
                "reply_to": reply_to,
                "subject": subject,
                "html": html_content
            }
            if plain_content:
                payload["text"] = plain_content
            if target_bcc:
                payload["bcc"] = target_bcc

            async with httpx.AsyncClient(timeout=12.0) as client:
                res = await client.post(url, headers=headers, json=payload)
                if res.status_code in (200, 201):
                    logger.info(f"Successfully sent lead email via Resend HTTP API to {target_recipients} (BCC: {target_bcc}): {res.json().get('id')}")
                    return True
                else:
                    logger.error(f"Resend HTTP API returned error ({res.status_code}): {res.text}")
                    return False
        except Exception as e:
            logger.error(f"Exception sending via Resend API: {e}")
            return False

    async def send_lead_email(self, lead_data: Dict[str, Any]) -> bool:
        """Sends lead alert email asynchronously via Resend HTTP API (Port 443) or SMTP."""
        if not settings.NOTIFICATION_EMAIL_ENABLED:
            logger.debug("Email notification skipped: NOTIFICATION_EMAIL_ENABLED is False")
            return False

        # Strictly require a valid mobile phone number before sending email
        phone = lead_data.get("phone")
        clean_phone = self._clean_phone_for_whatsapp(phone)
        if not clean_phone or len(clean_phone) < 10 or str(phone).strip() in ("Not provided", "No Phone", "None", ""):
            logger.info("Email notification skipped: Valid mobile number is strictly required to send email.")
            return False

        try:
            recipients = [r.strip() for r in settings.NOTIFICATION_EMAIL_TO.split(",") if r.strip()]
            if not recipients:
                recipients = ["trainee4@techvunex.in"]

            clean_service = self._normalize_service_name(lead_data.get("service"))
            subject = f"Techvunex AI: {clean_service}"
            reply_to = lead_data.get("email") or "info@techvunex.in"

            bcc_recipients = [b.strip() for b in settings.NOTIFICATION_EMAIL_BCC.split(",") if b.strip()]

            plain_content = self._generate_email_plain(lead_data)
            html_content = self._generate_email_html(lead_data)

            # 1. Primary: Resend HTTP REST API (HTTPS Port 443 - Never blocked on Render Free Tier!)
            if settings.RESEND_API_KEY:
                resend_ok = await self._send_via_resend(
                    recipients,
                    subject,
                    html_content,
                    plain_content=plain_content,
                    reply_to=reply_to,
                    bcc=bcc_recipients
                )
                if resend_ok:
                    return True

            # 2. Fallback: Standard SMTP
            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                msg = EmailMessage()
                msg["Subject"] = subject
                msg["From"] = f"Techvunex AI <{settings.SMTP_USER}>" if "<" not in settings.SMTP_USER else settings.SMTP_USER
                msg["To"] = ", ".join(recipients)
                if bcc_recipients:
                    msg["Bcc"] = ", ".join(bcc_recipients)
                msg.set_content(plain_content)
                msg.add_alternative(html_content, subtype="html")

                success = await asyncio.to_thread(self._sync_send_smtp, msg)
                if success:
                    logger.info(f"Successfully sent lead notification email via SMTP to {recipients} (BCC: {bcc_recipients})")
                return success

            return False
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

        # Only dispatch if at least one contact channel is present or human agent requested
        if not phone and not email and not lead_data.get("human_required"):
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
        clean_phone = self._clean_phone_for_whatsapp(phone)
        has_mobile = bool(clean_phone and len(clean_phone) >= 10 and str(phone).strip() not in ("Not provided", "No Phone", "None", ""))
        if settings.NOTIFICATION_EMAIL_ENABLED and has_mobile:
            tasks.append(asyncio.create_task(self.send_lead_email(lead_data)))
        if settings.TELEGRAM_NOTIFICATIONS_ENABLED:
            tasks.append(asyncio.create_task(self.send_telegram_alert(lead_data)))
        if settings.WHATSAPP_NOTIFICATIONS_ENABLED:
            tasks.append(asyncio.create_task(self.send_whatsapp_alert(lead_data)))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

notification_service = NotificationService()
