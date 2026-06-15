from datetime import datetime, timezone
from fastapi import HTTPException
from sqlalchemy import select
from src.db.models.decision import ApprovalRequest
from src.db.models.audit import AuditLog

VALID_ACTION_TYPES = {
    "RFQ_SEND",
    "ORDER_CONFIRM",
    "EXPEDITE_NOTIFY",
    "SHIPMENT_APPROVE",
    "BUYER_SIGNOFF",
    "PARTICIPANT_REPLACE",
    "QC_ESCALATE",
    "QUOTE_APPROVE",
}


async def create_approval_request(
    db,
    tenant_id,
    action_type: str,
    resource_type: str,
    resource_id,
    proposed_payload: dict,
    affected_participant_id=None,
    evidence: dict = None,
    risk_flags: list = None,
    created_by=None,
) -> ApprovalRequest:
    assert action_type in VALID_ACTION_TYPES, f"Unknown action_type: {action_type}"
    req = ApprovalRequest(
        tenant_id=tenant_id,
        action_type=action_type,
        resource_type=resource_type,
        resource_id=resource_id,
        proposed_payload=proposed_payload,
        affected_participant_id=affected_participant_id,
        evidence=evidence or {},
        risk_flags=risk_flags or [],
        status="PENDING",
        created_by=created_by,
    )
    db.add(req)
    await db.flush()
    return req


async def approve_request(db, approval_id, reviewed_by, review_notes: str = "") -> ApprovalRequest:
    req = await db.get(ApprovalRequest, approval_id)
    if not req:
        raise HTTPException(status_code=404, detail="ApprovalRequest not found")
    req.status = "APPROVED"
    req.reviewed_by = reviewed_by
    req.reviewed_at = datetime.now(timezone.utc)
    req.review_notes = review_notes
    log = AuditLog(
        tenant_id=req.tenant_id,
        user_id=reviewed_by,
        action="APPROVAL_APPROVED",
        resource_type="approval_request",
        resource_id=str(approval_id),
        payload={"review_notes": review_notes},
    )
    db.add(log)
    await db.flush()
    return req


async def reject_request(db, approval_id, reviewed_by, review_notes: str = "") -> ApprovalRequest:
    req = await db.get(ApprovalRequest, approval_id)
    if not req:
        raise HTTPException(status_code=404, detail="ApprovalRequest not found")
    req.status = "REJECTED"
    req.reviewed_by = reviewed_by
    req.reviewed_at = datetime.now(timezone.utc)
    req.review_notes = review_notes
    log = AuditLog(
        tenant_id=req.tenant_id,
        user_id=reviewed_by,
        action="APPROVAL_REJECTED",
        resource_type="approval_request",
        resource_id=str(approval_id),
        payload={"review_notes": review_notes},
    )
    db.add(log)
    await db.flush()
    return req


async def require_approved(db, approval_id) -> ApprovalRequest:
    req = await db.get(ApprovalRequest, approval_id)
    if not req or req.status != "APPROVED":
        raise HTTPException(status_code=403, detail="Action requires prior human approval.")
    return req
