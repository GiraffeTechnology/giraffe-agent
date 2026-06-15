import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.order import Order, OrderLine
from src.db.models.decision import DecisionPacket, DecisionOption
from src.db.models.dynamic_form import DynamicOrderForm, DynamicOrderFormVersion
from src.db.models.production import Milestone
from src.orders.state_machine import transition
from src.milestones.constants import ORDERED_MILESTONES
from src.execution_graph.writer import emit_event
from src.execution_graph.event_types import ORDER_CREATED, ORDER_CONFIRMED, BUYER_SIGNED_OFF


def _generate_order_number(seq: int) -> str:
    year = datetime.now(timezone.utc).year
    return f"ORD-{year}-{seq:04d}"


async def _next_order_seq(db: AsyncSession) -> int:
    result = await db.execute(select(func.count()).select_from(Order))
    return (result.scalar() or 0) + 1


def _planned_date(base: datetime, days: int | None) -> datetime | None:
    if days is None:
        return None
    return base + timedelta(days=days)


async def create_order_from_approved_option(
    db: AsyncSession,
    project_id: uuid.UUID,
    packet_id: uuid.UUID,
    option_id: uuid.UUID,
    approval_id: uuid.UUID,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Order:
    """
    Pre-condition: DecisionPacket approved + ApprovalRequest (QUOTE_APPROVE) approved.
    Creates order, locks form, and generates 12 milestones.
    """
    from src.approval_gates.service import require_approved
    await require_approved(db, approval_id)

    packet = await db.get(DecisionPacket, packet_id)
    if not packet or packet.human_approval_status != "APPROVED":
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="DecisionPacket is not approved.")

    option = await db.get(DecisionOption, option_id)
    if not option:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="DecisionOption not found.")

    # Find current form version
    form_result = await db.execute(
        select(DynamicOrderForm).where(DynamicOrderForm.project_id == project_id)
    )
    form = form_result.scalar_one_or_none()
    form_version_id = None
    form_fields = {}
    if form:
        ver_result = await db.execute(
            select(DynamicOrderFormVersion)
            .where(
                DynamicOrderFormVersion.form_id == form.id,
                DynamicOrderFormVersion.version_number == form.current_version,
            )
        )
        version = ver_result.scalar_one_or_none()
        if version:
            form_version_id = version.id
            form_fields = version.fields or {}

    seq = await _next_order_seq(db)
    order = Order(
        project_id=project_id,
        approved_option_id=option_id,
        locked_form_version_id=form_version_id,
        status="DRAFT_FROM_APPROVED_QUOTE",
        order_number=_generate_order_number(seq),
    )
    db.add(order)
    await db.flush()

    # Create order line from form fields
    product_type = form_fields.get("product_type", "Apparel")
    quantity = form_fields.get("quantity") or 1
    line = OrderLine(
        order_id=order.id,
        line_number=1,
        description=str(product_type),
        quantity=int(quantity),
        unit="pcs",
        unit_price=option.unit_price,
        currency=option.currency,
        attributes={"form_fields_snapshot": form_fields},
    )
    db.add(line)

    # Lock the dynamic form
    if form:
        form.is_locked = True

    # Create 12 milestones
    base = datetime.now(timezone.utc)
    lt = option.lead_time_breakdown or {}
    seq_days = lt.get("sequential_days", {})
    par_days = lt.get("parallel_breakdown", {})

    fabric_lt = par_days.get("fabric_lead_time_days")
    production_lt = seq_days.get("production_time_days")
    qc_lt = seq_days.get("qc_time_days")
    logistics_lt = seq_days.get("logistics_time_days")

    milestone_dates = {
        "SAMPLE_CONFIRMATION": _planned_date(base, 7),
        "FABRIC_BOOKING": _planned_date(base, fabric_lt),
        "TRIM_BOOKING": _planned_date(base, par_days.get("trim_lead_time_days")),
        "CUTTING": _planned_date(base, (fabric_lt or 0) + 3) if fabric_lt else None,
        "SEWING": None,
        "WASHING_OR_FINISHING": None,
        "INLINE_QC": None,
        "FINAL_QC": None,
        "PACKING": None,
        "LOGISTICS_HANDOVER": None,
        "SHIPMENT": None,
        "BUYER_SIGN_OFF": None,
    }

    # Sequential after CUTTING
    cutting_days = (fabric_lt or 0) + 3 if fabric_lt else None
    if cutting_days is not None and production_lt is not None:
        sewing_days = cutting_days + production_lt
        milestone_dates["SEWING"] = _planned_date(base, sewing_days)
        milestone_dates["WASHING_OR_FINISHING"] = _planned_date(base, sewing_days + 2)
        milestone_dates["INLINE_QC"] = _planned_date(base, sewing_days + 3)
        if qc_lt is not None:
            final_qc_days = sewing_days + qc_lt
            milestone_dates["FINAL_QC"] = _planned_date(base, final_qc_days)
            milestone_dates["PACKING"] = _planned_date(base, final_qc_days + 2)
            milestone_dates["LOGISTICS_HANDOVER"] = _planned_date(base, final_qc_days + 3)
            if logistics_lt is not None:
                shipment_days = final_qc_days + logistics_lt
                milestone_dates["SHIPMENT"] = _planned_date(base, shipment_days)
                milestone_dates["BUYER_SIGN_OFF"] = _planned_date(base, shipment_days + 7)

    for mtype in ORDERED_MILESTONES:
        planned = milestone_dates.get(mtype)
        notes = None if planned else "Planned date not set — lead time missing"
        ms = Milestone(
            order_id=order.id,
            milestone_type=mtype,
            planned_date=planned,
            status="PENDING",
            notes=notes,
        )
        db.add(ms)

    await db.flush()

    await emit_event(
        db=db,
        event_type=ORDER_CREATED,
        payload={
            "order_id": str(order.id),
            "order_number": order.order_number,
            "project_id": str(project_id),
        },
        tenant_id=tenant_id,
        project_id=project_id,
        order_id=order.id,
        triggered_by_user_id=user_id,
    )

    return order


async def confirm_order(
    db: AsyncSession,
    order_id: uuid.UUID,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Order:
    order = await db.get(Order, order_id)
    if not order:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Order not found")

    order.status = transition(order.status, "PENDING_BUYER_CONFIRMATION")
    order.status = transition(order.status, "CONFIRMED")
    order.confirmed_at = datetime.now(timezone.utc)
    await db.flush()

    await emit_event(
        db=db,
        event_type=ORDER_CONFIRMED,
        payload={"order_id": str(order_id), "order_number": order.order_number},
        tenant_id=tenant_id,
        project_id=order.project_id,
        order_id=order_id,
        triggered_by_user_id=user_id,
    )

    order.status = transition(order.status, "IN_PRODUCTION")
    await db.flush()

    return order


async def buyer_sign_off(
    db: AsyncSession,
    order_id: uuid.UUID,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Order:
    order = await db.get(Order, order_id)
    if not order:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status != "DELIVERED":
        from fastapi import HTTPException
        raise HTTPException(
            status_code=409,
            detail=f"Cannot sign off order in status {order.status}. Must be DELIVERED.",
        )

    order.status = transition(order.status, "BUYER_SIGNED_OFF")
    order.buyer_signed_off_at = datetime.now(timezone.utc)
    await db.flush()

    await emit_event(
        db=db,
        event_type=BUYER_SIGNED_OFF,
        payload={"order_id": str(order_id)},
        tenant_id=tenant_id,
        project_id=order.project_id,
        order_id=order_id,
        triggered_by_user_id=user_id,
    )

    # Stub: supplier memory update handled in Iter 6
    return order
