import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_db, get_current_user
from src.approval_gates.schemas import ApprovalRequestOut, ReviewRequest
from src.approval_gates.service import approve_request, reject_request
from src.db.models.decision import ApprovalRequest

router = APIRouter()


@router.get("/approval-requests", response_model=list[ApprovalRequestOut])
async def list_approval_requests(
    status: Optional[str] = "PENDING",
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = select(ApprovalRequest)
    if status and status.upper() != "ALL":
        query = query.where(ApprovalRequest.status == status.upper())
    result = await db.execute(query.order_by(ApprovalRequest.created_at.desc()))
    return list(result.scalars().all())


@router.get("/approval-requests/{approval_id}", response_model=ApprovalRequestOut)
async def get_approval_request(
    approval_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    req = await db.get(ApprovalRequest, approval_id)
    if not req:
        raise HTTPException(status_code=404, detail="ApprovalRequest not found")
    return req


@router.post("/approval-requests/{approval_id}/approve", response_model=ApprovalRequestOut)
async def approve_approval_request(
    approval_id: uuid.UUID,
    body: ReviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    req = await approve_request(db, approval_id, current_user.id, body.review_notes)
    await db.commit()
    await db.refresh(req)
    return req


@router.post("/approval-requests/{approval_id}/reject", response_model=ApprovalRequestOut)
async def reject_approval_request(
    approval_id: uuid.UUID,
    body: ReviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    req = await reject_request(db, approval_id, current_user.id, body.review_notes)
    await db.commit()
    await db.refresh(req)
    return req
