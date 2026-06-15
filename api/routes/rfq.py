import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_db, get_current_user
from src.rfq.schemas import RFQCreate, RFQOut, RFQSendRequest
from src.rfq.service import create_rfq, send_rfq, get_rfq

router = APIRouter()


@router.post("/projects/{project_id}/rfqs", status_code=status.HTTP_201_CREATED)
async def create_rfq_route(
    project_id: uuid.UUID,
    body: RFQCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    rfq, approval_request_id = await create_rfq(
        db=db,
        project_id=project_id,
        form_version_id=body.form_version_id,
        recipient_participant_ids=body.recipient_participant_ids,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
    )
    await db.commit()
    await db.refresh(rfq)
    return {
        "rfq": RFQOut.model_validate(rfq),
        "approval_request_id": str(approval_request_id),
    }


@router.post("/rfqs/{rfq_id}/send", response_model=RFQOut)
async def send_rfq_route(
    rfq_id: uuid.UUID,
    body: RFQSendRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    rfq = await send_rfq(
        db=db,
        rfq_id=rfq_id,
        approval_id=body.approval_id,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
    )
    await db.commit()
    await db.refresh(rfq)
    return rfq


@router.get("/rfqs/{rfq_id}", response_model=RFQOut)
async def get_rfq_route(
    rfq_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    rfq = await get_rfq(db, rfq_id)
    if not rfq:
        raise HTTPException(status_code=404, detail="RFQ not found")
    return rfq
