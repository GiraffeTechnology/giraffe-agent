import uuid
from datetime import datetime
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.rfq import RFQ, RFQRecipient, SupplierResponse, SupplierResponsePacket
from src.rfq.state_machine import transition
from src.supplier_responses.normalizer import normalize_supplier_response
from src.execution_graph.writer import emit_event
from src.execution_graph.event_types import (
    SUPPLIER_RESPONSE_RECEIVED, SUPPLIER_RESPONSE_NORMALIZED
)


async def _update_rfq_status_from_responses(
    db: AsyncSession, rfq: RFQ
) -> None:
    """Update RFQ to RECEIVED or PARTIAL_RESPONSE based on response count."""
    total_result = await db.execute(
        select(func.count()).where(RFQRecipient.rfq_id == rfq.id)
    )
    total = total_result.scalar() or 0

    responded_result = await db.execute(
        select(func.count()).where(
            SupplierResponse.rfq_id == rfq.id
        )
    )
    responded = responded_result.scalar() or 0

    if rfq.status == "SENT":
        if responded >= total:
            rfq.status = transition(rfq.status, "RECEIVED")
        else:
            rfq.status = transition(rfq.status, "PARTIAL_RESPONSE")
    elif rfq.status in ("RECEIVED", "PARTIAL_RESPONSE"):
        if responded >= total:
            rfq.status = transition(rfq.status, "COMPLETE_RESPONSE")


async def record_supplier_response(
    db: AsyncSession,
    rfq_id: uuid.UUID,
    participant_id: uuid.UUID,
    raw_text: str,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
) -> tuple[SupplierResponse, SupplierResponsePacket]:
    rfq = await db.get(RFQ, rfq_id)
    if not rfq:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="RFQ not found")

    # Create raw response record
    response = SupplierResponse(
        rfq_id=rfq_id,
        participant_id=participant_id,
        raw_response_text=raw_text,
    )
    db.add(response)
    await db.flush()

    # Update RFQRecipient
    recip_result = await db.execute(
        select(RFQRecipient).where(
            RFQRecipient.rfq_id == rfq_id,
            RFQRecipient.participant_id == participant_id,
        )
    )
    recipient = recip_result.scalar_one_or_none()
    if recipient:
        recipient.responded_at = datetime.utcnow()
        recipient.status = "RESPONDED"

    project_id = rfq.project_id

    await emit_event(
        db=db,
        event_type=SUPPLIER_RESPONSE_RECEIVED,
        payload={"rfq_id": str(rfq_id), "participant_id": str(participant_id)},
        tenant_id=tenant_id,
        project_id=project_id,
        participant_id=participant_id,
        triggered_by_user_id=user_id,
    )

    # Normalize via LLM
    normalized = await normalize_supplier_response(raw_text, rfq.rfq_content or {})

    def _safe_int(val) -> int | None:
        try:
            return int(val) if val is not None else None
        except (ValueError, TypeError):
            return None

    def _safe_float(val) -> float | None:
        try:
            return float(val) if val is not None else None
        except (ValueError, TypeError):
            return None

    packet = SupplierResponsePacket(
        supplier_response_id=response.id,
        unit_price=_safe_float(normalized.get("unit_price")),
        currency=normalized.get("currency"),
        moq=_safe_int(normalized.get("moq")),
        sample_time_days=_safe_int(normalized.get("sample_time_days")),
        fabric_lead_time_days=_safe_int(normalized.get("fabric_lead_time_days")),
        trim_lead_time_days=_safe_int(normalized.get("trim_lead_time_days")),
        production_time_days=_safe_int(normalized.get("production_time_days")),
        qc_time_days=_safe_int(normalized.get("qc_time_days")),
        packaging_time_days=_safe_int(normalized.get("packaging_time_days")),
        logistics_time_days=_safe_int(normalized.get("logistics_time_days")),
        total_lead_time_days=_safe_int(normalized.get("total_lead_time_days")),
        payment_terms=normalized.get("payment_terms"),
        trade_terms=normalized.get("trade_terms"),
        capacity_available=_safe_int(normalized.get("capacity_available")),
        supplier_notes=normalized.get("supplier_notes"),
        missing_fields=normalized.get("missing_fields", []),
        risk_flags=normalized.get("risk_flags", []),
        evidence_source=normalized.get("evidence_source", {}),
        ai_generated=True,
        human_confirmed=False,
    )
    db.add(packet)

    # Update RFQ status based on response count
    await _update_rfq_status_from_responses(db, rfq)
    await db.flush()

    await emit_event(
        db=db,
        event_type=SUPPLIER_RESPONSE_NORMALIZED,
        payload={
            "response_id": str(response.id),
            "missing_fields": normalized.get("missing_fields", []),
            "risk_flags": normalized.get("risk_flags", []),
        },
        tenant_id=tenant_id,
        project_id=project_id,
        participant_id=participant_id,
        triggered_by_user_id=user_id,
    )

    return response, packet


async def list_responses_for_rfq(
    db: AsyncSession, rfq_id: uuid.UUID
) -> list[SupplierResponse]:
    result = await db.execute(
        select(SupplierResponse).where(SupplierResponse.rfq_id == rfq_id)
    )
    return list(result.scalars().all())


async def manually_normalize(
    db: AsyncSession, response_id: uuid.UUID, user_id: uuid.UUID
) -> SupplierResponsePacket:
    response = await db.get(SupplierResponse, response_id)
    if not response:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="SupplierResponse not found")

    rfq = await db.get(RFQ, response.rfq_id)
    rfq_content = rfq.rfq_content if rfq else {}

    normalized = await normalize_supplier_response(response.raw_response_text or "", rfq_content)

    # Find existing packet
    pkt_result = await db.execute(
        select(SupplierResponsePacket).where(
            SupplierResponsePacket.supplier_response_id == response_id
        )
    )
    packet = pkt_result.scalar_one_or_none()

    def _safe_int(val) -> int | None:
        try:
            return int(val) if val is not None else None
        except (ValueError, TypeError):
            return None

    def _safe_float(val) -> float | None:
        try:
            return float(val) if val is not None else None
        except (ValueError, TypeError):
            return None

    if not packet:
        packet = SupplierResponsePacket(supplier_response_id=response_id)
        db.add(packet)

    packet.unit_price = _safe_float(normalized.get("unit_price"))
    packet.currency = normalized.get("currency")
    packet.moq = _safe_int(normalized.get("moq"))
    packet.total_lead_time_days = _safe_int(normalized.get("total_lead_time_days"))
    packet.missing_fields = normalized.get("missing_fields", [])
    packet.risk_flags = normalized.get("risk_flags", [])
    packet.ai_generated = True
    await db.flush()
    return packet
