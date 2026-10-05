from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.schemas.lead import LeadCreate, LeadUpdate, LeadResponse
from app.services.lead_service import lead_service

router = APIRouter(prefix="/leads", tags=["Leads"])

@router.post("", response_model=LeadResponse)
async def create_lead(lead_in: LeadCreate, db: AsyncSession = Depends(get_db)):
    lead = await lead_service.create_or_update_lead(db, lead_in.dict(exclude_unset=True))
    return lead

@router.get("", response_model=List[LeadResponse])
async def list_leads(
    status_filter: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    leads = await lead_service.list_leads(db, status=status_filter, limit=limit, offset=offset)
    return leads

@router.patch("/{lead_id}", response_model=LeadResponse)
async def update_lead(lead_id: str, lead_update: LeadUpdate, db: AsyncSession = Depends(get_db)):
    lead = await lead_service.update_lead_status(db, lead_id, lead_update.status)
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    return lead
