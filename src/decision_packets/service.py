import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.decision import DecisionPacket, DecisionOption, ApprovalRequest
from src.db.models.rfq import RFQ, SupplierResponse, SupplierResponsePacket
from src.db.models.dynamic_form import DynamicOrderForm, DynamicOrderFormVersion
from src.lead_time.calculator import calculate_path_lead_time
from src.risk_flags.detector import detect_decision_risk_flags, generate_comparison_summary
from src.approval_gates.service import create_approval_request, require_approved
from src.execution_graph.writer import emit_event
from src.execution_graph.event_types import (
    DECISION_PACKET_GENERATED, QUOTE_APPROVAL_REQUESTED, QUOTE_APPROVED
)


async def _load_current_form_fields(db: AsyncSession, project_id: uuid.UUID) -> dict:
    result = await db.execute(
        select(DynamicOrderForm).where(DynamicOrderForm.project_id == project_id)
    )
    form = result.scalar_one_or_none()
    if not form:
        return {}
    ver_result = await db.execute(
        select(DynamicOrderFormVersion)
        .where(
            DynamicOrderFormVersion.form_id == form.id,
            DynamicOrderFormVersion.version_number == form.current_version,
        )
    )
    version = ver_result.scalar_one_or_none()
    return version.fields if version else {}


async def _load_current_form_version_id(
    db: AsyncSession, project_id: uuid.UUID
) -> uuid.UUID | None:
    result = await db.execute(
        select(DynamicOrderForm).where(DynamicOrderForm.project_id == project_id)
    )
    form = result.scalar_one_or_none()
    if not form:
        return None
    ver_result = await db.execute(
        select(DynamicOrderFormVersion)
        .where(
            DynamicOrderFormVersion.form_id == form.id,
            DynamicOrderFormVersion.version_number == form.current_version,
        )
    )
    version = ver_result.scalar_one_or_none()
    return version.id if version else None


async def generate_decision_packet(
    db: AsyncSession,
    project_id: uuid.UUID,
    rfq_id: uuid.UUID,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
) -> tuple["DecisionPacket", uuid.UUID]:
    """
    Build up to 3 decision options from RFQ supplier responses.
    Returns (DecisionPacket, approval_request_id).
    """
    # Load all SupplierResponsePackets for this RFQ
    responses_result = await db.execute(
        select(SupplierResponse).where(SupplierResponse.rfq_id == rfq_id)
    )
    responses = list(responses_result.scalars().all())

    if not responses:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Insufficient supplier responses")

    # Load packets
    packets_data: list[dict] = []
    for r in responses:
        pkt_result = await db.execute(
            select(SupplierResponsePacket).where(
                SupplierResponsePacket.supplier_response_id == r.id
            )
        )
        pkt = pkt_result.scalar_one_or_none()
        if pkt:
            packets_data.append({
                "response_id": str(r.id),
                "participant_id": str(r.participant_id),
                "unit_price": pkt.unit_price,
                "currency": pkt.currency,
                "moq": pkt.moq,
                "fabric_lead_time_days": pkt.fabric_lead_time_days,
                "trim_lead_time_days": pkt.trim_lead_time_days,
                "production_time_days": pkt.production_time_days,
                "qc_time_days": pkt.qc_time_days,
                "packaging_time_days": pkt.packaging_time_days,
                "logistics_time_days": pkt.logistics_time_days,
                "total_lead_time_days": pkt.total_lead_time_days,
                "capacity_available": pkt.capacity_available,
                "payment_terms": pkt.payment_terms,
                "trade_terms": pkt.trade_terms,
                "valid_until": pkt.valid_until.isoformat() if pkt.valid_until else None,
                "supplier_notes": pkt.supplier_notes,
                "missing_fields": pkt.missing_fields or [],
                "risk_flags": list(pkt.risk_flags or []),
            })

    if not packets_data:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Insufficient supplier responses")

    form_fields = await _load_current_form_fields(db, project_id)
    quantity = form_fields.get("quantity") or 1

    # Build up to 3 options: best overall / fastest / lowest price
    # Deduplicate: if fewer responses, fewer options
    option_configs = []

    # Option 1: first/best overall response
    option_configs.append(("Best overall match", packets_data[0]))

    if len(packets_data) >= 2:
        # Option 2: fastest lead time
        sorted_by_lt = sorted(
            packets_data,
            key=lambda p: p.get("total_lead_time_days") or 9999,
        )
        option_configs.append(("Fastest lead time", sorted_by_lt[0]))

    if len(packets_data) >= 3:
        # Option 3: lowest price
        sorted_by_price = sorted(
            [p for p in packets_data if p.get("unit_price") is not None],
            key=lambda p: p["unit_price"],
        )
        if sorted_by_price:
            option_configs.append(("Lowest price", sorted_by_price[0]))

    # Create DecisionPacket
    packet = DecisionPacket(
        project_id=project_id,
        human_approval_status="PENDING",
    )
    db.add(packet)
    await db.flush()

    created_options: list[DecisionOption] = []
    options_for_summary: list[dict] = []

    for idx, (reason, pkt_data) in enumerate(option_configs):
        lt_result = calculate_path_lead_time([pkt_data])
        unit_price = pkt_data.get("unit_price")
        total_price = (unit_price * quantity) if unit_price is not None else None

        option_for_risk = {
            "calculated_total_lead_time_days": lt_result["calculated_total_lead_time_days"],
            "supplier_stated_lead_time_days": pkt_data.get("total_lead_time_days"),
            "unit_price": unit_price,
            "capacity_available": pkt_data.get("capacity_available"),
            "valid_until": pkt_data.get("valid_until"),
            "missing_fields": lt_result["missing_fields"],
            "risk_flags": pkt_data.get("risk_flags", []),
            "option_index": idx + 1,
        }
        risk_flags = detect_decision_risk_flags(option_for_risk, form_fields)

        option = DecisionOption(
            packet_id=packet.id,
            option_index=idx + 1,
            supplier_combination={"primary": pkt_data["participant_id"]},
            unit_price=unit_price,
            total_price=total_price,
            currency=pkt_data.get("currency"),
            lead_time_breakdown=lt_result,
            calculated_total_lead_time_days=lt_result["calculated_total_lead_time_days"],
            supplier_stated_lead_time_days=pkt_data.get("total_lead_time_days"),
            risk_flags=risk_flags,
            missing_fields=lt_result["missing_fields"],
            recommendation_reason=reason,
            evidence={"source_response_id": pkt_data["response_id"]},
        )
        db.add(option)
        created_options.append(option)
        options_for_summary.append({**option_for_risk, "recommendation_reason": reason})

    await db.flush()

    # Set recommended option (first = best overall)
    if created_options:
        packet.recommended_option_id = created_options[0].id

    # Generate summaries
    summary_dicts = [
        {
            "option_index": o.option_index,
            "unit_price": o.unit_price,
            "currency": o.currency,
            "calculated_total_lead_time_days": o.calculated_total_lead_time_days,
            "risk_flags": o.risk_flags or [],
        }
        for o in created_options
    ]
    packet.comparison_summary = generate_comparison_summary(summary_dicts)
    packet.risk_summary = "; ".join(
        f"Option {o.option_index}: {', '.join(o.risk_flags)}"
        for o in created_options if o.risk_flags
    ) or "No major risks identified."
    packet.missing_field_summary = "; ".join(
        f"Option {o.option_index}: {', '.join(o.missing_fields)}"
        for o in created_options if o.missing_fields
    ) or "No missing fields."

    # Create ApprovalRequest for QUOTE_APPROVE
    approval = await create_approval_request(
        db=db,
        tenant_id=tenant_id,
        action_type="QUOTE_APPROVE",
        resource_type="decision_packet",
        resource_id=packet.id,
        proposed_payload={"packet_id": str(packet.id), "project_id": str(project_id)},
        created_by=user_id,
    )
    await db.flush()

    await emit_event(
        db=db,
        event_type=DECISION_PACKET_GENERATED,
        payload={"packet_id": str(packet.id), "options_count": len(created_options)},
        tenant_id=tenant_id,
        project_id=project_id,
        triggered_by_user_id=user_id,
    )
    await emit_event(
        db=db,
        event_type=QUOTE_APPROVAL_REQUESTED,
        payload={"packet_id": str(packet.id), "approval_id": str(approval.id)},
        tenant_id=tenant_id,
        project_id=project_id,
        triggered_by_user_id=user_id,
    )

    return packet, approval.id


async def approve_decision_option(
    db: AsyncSession,
    packet_id: uuid.UUID,
    option_id: uuid.UUID,
    approval_id: uuid.UUID,
    reviewed_by: uuid.UUID,
    review_notes: str,
    tenant_id: uuid.UUID,
) -> DecisionPacket:
    # Guard: must be approved
    await require_approved(db, approval_id)

    packet = await db.get(DecisionPacket, packet_id)
    if not packet:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="DecisionPacket not found")

    packet.recommended_option_id = option_id
    packet.human_approval_status = "APPROVED"
    await db.flush()

    await emit_event(
        db=db,
        event_type=QUOTE_APPROVED,
        payload={"packet_id": str(packet_id), "option_id": str(option_id)},
        tenant_id=tenant_id,
        project_id=packet.project_id,
        triggered_by_user_id=reviewed_by,
    )
    return packet


async def get_latest_decision_packet(
    db: AsyncSession, project_id: uuid.UUID
) -> DecisionPacket | None:
    result = await db.execute(
        select(DecisionPacket)
        .where(DecisionPacket.project_id == project_id)
        .order_by(DecisionPacket.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_options_for_packet(
    db: AsyncSession, packet_id: uuid.UUID
) -> list[DecisionOption]:
    result = await db.execute(
        select(DecisionOption)
        .where(DecisionOption.packet_id == packet_id)
        .order_by(DecisionOption.option_index)
    )
    return list(result.scalars().all())
