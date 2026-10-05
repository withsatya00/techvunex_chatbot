import asyncio
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.lead import Lead
from app.models.contact import Contact
from app.schemas.lead import LeadCreate, LeadUpdate
from app.core.logging import logger
from app.services.notification_service import notification_service

class LeadService:
    @staticmethod
    async def create_or_update_lead(
        session: AsyncSession,
        lead_data: Dict[str, Any]
    ) -> Lead:
        email = lead_data.get("email")
        phone = lead_data.get("phone")

        existing_lead = None
        if email:
            stmt = select(Lead).where(Lead.email == email)
            res = await session.execute(stmt)
            existing_lead = res.scalar_one_or_none()
        elif phone:
            stmt = select(Lead).where(Lead.phone == phone)
            res = await session.execute(stmt)
            existing_lead = res.scalar_one_or_none()

        if existing_lead:
            # Update non-null fields
            for key in ["name", "company", "service", "requirement", "budget", "timeline", "status", "human_required"]:
                if lead_data.get(key) is not None:
                    setattr(existing_lead, key, lead_data[key])
            existing_lead.updated_at = datetime.utcnow()
            await session.commit()
            await session.refresh(existing_lead)
            logger.info(f"Updated existing lead: {existing_lead.id}")
            await LeadService._sync_contact_row(session, lead_data)
            LeadService._trigger_notification(existing_lead)
            return existing_lead
        else:
            new_lead = Lead(
                name=lead_data.get("name"),
                email=lead_data.get("email"),
                phone=lead_data.get("phone"),
                company=lead_data.get("company"),
                service=lead_data.get("service"),
                requirement=lead_data.get("requirement"),
                budget=lead_data.get("budget"),
                timeline=lead_data.get("timeline"),
                status=lead_data.get("status", "new"),
                source=lead_data.get("source", "website_chat"),
                human_required=lead_data.get("human_required", False)
            )
            session.add(new_lead)
            await session.commit()
            await session.refresh(new_lead)
            logger.info(f"Created new lead: {new_lead.id}")
            await LeadService._sync_contact_row(session, lead_data)
            LeadService._trigger_notification(new_lead)
            return new_lead

    @staticmethod
    async def _sync_contact_row(session: AsyncSession, lead_data: Dict[str, Any]) -> None:
        """
        Synchronizes captured lead into the main techvunex_db.contacts table,
        matching the exact schema with columns:
        (id, name, email, phone, company, subject, message, createdAt, updatedAt)
        """
        try:
            phone = lead_data.get("phone")
            email = lead_data.get("email")
            name = lead_data.get("name")
            if not phone and not email and not name:
                return

            service = lead_data.get("service") or "General Inquiry"
            budget = lead_data.get("budget")
            requirement = lead_data.get("requirement") or "Customer inquired via AI chatbot"
            company = lead_data.get("company")

            msg_parts = [f"Service: {service}"]
            if requirement:
                msg_parts.append(f"Requirement: {requirement}")
            if budget:
                msg_parts.append(f"Budget: {budget}")
            message_content = " | ".join(msg_parts)

            existing_contact = None
            if phone:
                stmt = select(Contact).where(Contact.phone == phone)
                res = await session.execute(stmt)
                existing_contact = res.scalar_one_or_none()
            if not existing_contact and email:
                stmt = select(Contact).where(Contact.email == email)
                res = await session.execute(stmt)
                existing_contact = res.scalar_one_or_none()

            now = datetime.utcnow()
            if existing_contact:
                if name: existing_contact.name = name
                if email: existing_contact.email = email
                if phone: existing_contact.phone = phone
                if company: existing_contact.company = company
                if service: existing_contact.subject = service
                existing_contact.message = message_content
                existing_contact.updatedAt = now
            else:
                new_contact = Contact(
                    name=name,
                    email=email,
                    phone=phone,
                    company=company,
                    subject=service,
                    message=message_content,
                    createdAt=now,
                    updatedAt=now
                )
                session.add(new_contact)
            await session.commit()
            logger.info("Successfully synced lead to contacts table")
        except Exception as e:
            logger.error(f"Error syncing lead to contacts table: {e}")

    @staticmethod
    def _trigger_notification(lead: Lead) -> None:
        if lead.phone or lead.email:
            lead_dict = {
                "id": str(lead.id),
                "name": lead.name,
                "email": lead.email,
                "phone": lead.phone,
                "company": lead.company,
                "service": lead.service,
                "requirement": lead.requirement,
                "budget": lead.budget,
                "timeline": lead.timeline,
                "status": lead.status,
                "source": lead.source,
                "human_required": lead.human_required,
                "created_at": lead.created_at.strftime("%d %b %Y, %I:%M %p") if lead.created_at else None,
            }
            try:
                asyncio.create_task(notification_service.dispatch_lead_notification(lead_dict))
            except Exception as e:
                logger.error(f"Failed to schedule lead notification task: {e}")

    @staticmethod
    async def list_leads(
        session: AsyncSession,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Lead]:
        stmt = select(Lead).order_by(Lead.updated_at.desc())
        if status:
            stmt = stmt.where(Lead.status == status)
        stmt = stmt.offset(offset).limit(limit)
        res = await session.execute(stmt)
        return res.scalars().all()

    @staticmethod
    async def update_lead_status(
        session: AsyncSession,
        lead_id: str,
        status: str
    ) -> Optional[Lead]:
        stmt = select(Lead).where(Lead.id == lead_id)
        res = await session.execute(stmt)
        lead = res.scalar_one_or_none()
        if lead:
            lead.status = status
            await session.commit()
            await session.refresh(lead)
        return lead

lead_service = LeadService()
