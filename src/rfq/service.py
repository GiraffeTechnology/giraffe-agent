import uuid
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.rfq import RFQ, RFQRecipient
from src.db.models.dynamic_form import DynamicOrderFormVersion
from src.db.models.participant import Participant
from src.rfq.state_machine import transition
from src.approval_gates.service import create_approval_request, require_approved
from src.ai_buyer.rfq_drafter import draft_rfq_content
from src.execution_graph.writer import emit_event
from src.execution_graph.event_types import (
    RFQ_DRAFTED, RFQ_APPROVAL_REQUESTED, RFQ_APPROVED, RFQ_SENT
)


async def create_rfq(
    db: AsyncSession,
    project_id: uuid.UUID,
    form_version_id: uuid.UUID,
    recipient_participant_ids: list[uuid.UUID],
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
) -> tuple[RFQ, uuid.UUID]:
    """
    Creates RFQ in PENDING_APPROVAL state with an ApprovalRequest.
    Returns (rfq, approval_request_id).
    CRITICAL: Does NOT set status=SENT or notify participants.
    """
    # Load form version for context
    form_version = await db.get(DynamicOrderFormVersion, form_version_id)
    form_fields = form_version.fields if form_version else {}

    # Load recipient participants for context
    recipients_data: list[dict] = []
    for pid in recipient_participant_ids:
        p = await db.get(Participant, pid)
        if p:
            recipients_data.append({"id": str(p.id), "name": p.name})

    # Draft RFQ content via LLM
    rfq_content = await draft_rfq_content(form_fields, recipients_data)

    # Create RFQ in DRAFT then transition to PENDING_APPROVAL
    rfq = RFQ(
        project_id=project_id,
        form_version_id=form_version_id,
        status="DRAFT",
        rfq_content=rfq_content,
        ai_generated=True,
    )
    db.add(rfq)
    await db.flush()

    # Create recipient records
    for pid in recipient_participant_ids:
        recipient = RFQRecipient(
            rfq_id=rfq.id,
            participant_id=pid,
            status="PENDING",
        )
        db.add(recipient)

    # Create ApprovalRequest before transitioning
    approval = await create_approval_request(
        db=db,
        tenant_id=tenant_id,
        action_type="RFQ_SEND",
        resource_type="rfq",
        resource_id=rfq.id,
        proposed_payload={
            "rfq_id": str(rfq.id),
            "recipient_participant_ids": [str(p) for p in recipient_participant_ids],
            "rfq_subject": rfq_content.get("rfq_subject", ""),
        },
        created_by=user_id,
    )

    # Transition DRAFT → PENDING_APPROVAL
    rfq.status = transition(rfq.status, "PENDING_APPROVAL")
    await db.flush()

    await emit_event(
        db=db,
        event_type=RFQ_DRAFTED,
        payload={"rfq_id": str(rfq.id), "project_id": str(project_id)},
        tenant_id=tenant_id,
        project_id=project_id,
        triggered_by_user_id=user_id,
    )
    await emit_event(
        db=db,
        event_type=RFQ_APPROVAL_REQUESTED,
        payload={"rfq_id": str(rfq.id), "approval_request_id": str(approval.id)},
        tenant_id=tenant_id,
        project_id=project_id,
        triggered_by_user_id=user_id,
    )

    return rfq, approval.id


async def send_rfq(
    db: AsyncSession,
    rfq_id: uuid.UUID,
    approval_id: uuid.UUID,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
) -> RFQ:
    """
    Only callable after ApprovalRequest is APPROVED.
    Transitions RFQ APPROVED_TO_SEND → SENT.
    """
    # Guard: must be approved
    await require_approved(db, approval_id)

    rfq = await db.get(RFQ, rfq_id)
    if not rfq:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="RFQ not found")

    # Transition PENDING_APPROVAL → APPROVED_TO_SEND → SENT
    if rfq.status == "PENDING_APPROVAL":
        rfq.status = transition(rfq.status, "APPROVED_TO_SEND")
    rfq.status = transition(rfq.status, "SENT")
    rfq.sent_at = datetime.now(timezone.utc)
    rfq.human_approved_by = user_id

    # Update recipient sent_at timestamps
    recipients_result = await db.execute(
        select(RFQRecipient).where(RFQRecipient.rfq_id == rfq_id)
    )
    for recipient in recipients_result.scalars().all():
        recipient.sent_at = rfq.sent_at
        recipient.status = "SENT"

    await db.flush()

    project_id = rfq.project_id
    await emit_event(
        db=db,
        event_type=RFQ_APPROVED,
        payload={"rfq_id": str(rfq.id), "approval_id": str(approval_id)},
        tenant_id=tenant_id,
        project_id=project_id,
        triggered_by_user_id=user_id,
    )
    await emit_event(
        db=db,
        event_type=RFQ_SENT,
        payload={"rfq_id": str(rfq.id), "sent_at": rfq.sent_at.isoformat()},
        tenant_id=tenant_id,
        project_id=project_id,
        triggered_by_user_id=user_id,
    )

    return rfq


async def get_rfq(db: AsyncSession, rfq_id: uuid.UUID) -> RFQ | None:
    return await db.get(RFQ, rfq_id)
