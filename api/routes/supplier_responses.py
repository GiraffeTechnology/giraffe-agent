import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_db, get_current_user
from src.supplier_responses.schemas import (
    SupplierResponseCreate, SupplierResponseOut, SupplierResponsePacketOut
)
from src.supplier_responses.service import (
    record_supplier_response, list_responses_for_rfq, manually_normalize
)
from src.db.models.rfq import SupplierResponsePacket

router = APIRouter()


@router.post("/rfqs/{rfq_id}/responses", status_code=status.HTTP_201_CREATED)
async def create_supplier_response(
    rfq_id: uuid.UUID,
    body: SupplierResponseCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    response, packet = await record_supplier_response(
        db=db,
        rfq_id=rfq_id,
        participant_id=body.participant_id,
        raw_text=body.raw_response_text,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
    )
    await db.commit()
    await db.refresh(response)
    await db.refresh(packet)
    return {
        "response": SupplierResponseOut.model_validate(response),
        "packet": SupplierResponsePacketOut.model_validate(packet),
    }


@router.get("/rfqs/{rfq_id}/responses")
async def list_rfq_responses(
    rfq_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    responses = await list_responses_for_rfq(db, rfq_id)
    result = []
    for r in responses:
        pkt_result = await db.execute(
            select(SupplierResponsePacket).where(
                SupplierResponsePacket.supplier_response_id == r.id
            )
        )
        packet = pkt_result.scalar_one_or_none()
        entry = {"response": SupplierResponseOut.model_validate(r)}
        if packet:
            entry["packet"] = SupplierResponsePacketOut.model_validate(packet)
        result.append(entry)
    return result


@router.post(
    "/supplier-responses/{response_id}/normalize",
    response_model=SupplierResponsePacketOut,
)
async def renormalize_response(
    response_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    packet = await manually_normalize(db, response_id, current_user.id)
    await db.commit()
    await db.refresh(packet)
    return packet
