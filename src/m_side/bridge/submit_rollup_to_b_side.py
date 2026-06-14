"""
Submit Rollup to B-side — bridges the SupplierResponseRollup into the B-side workspace
as a SupplierResponseRecord consumable by the feasibility engine.
"""

import uuid
from datetime import datetime, timezone
from pydantic import BaseModel

from src.m_side.rollup.supplier_response_rollup import SupplierResponseRollup
from src.b_side.supplier_response_intake import intake_supplier_response
from src.core_schema.b_side_types import SupplierResponseRecord
from src.m_side.m_event_logger import log_m_event


class SubmitResult(BaseModel):
    submit_id: str
    rollup_id: str
    project_id: str
    b_workspace_id: str
    supplier_response_record_id: str
    status: str
    submitted_at: str


def submit_rollup_to_b_side(
    rollup: SupplierResponseRollup,
    b_workspace_id: str,
    supplier_name: str = "Manufacturer M",
) -> SubmitResult:
    """
    Convert a SupplierResponseRollup into a SupplierResponseRecord and attach it
    to the B-side workspace for feasibility engine consumption.
    """
    # Use calculated lead time from Lead Time Path Model if available, else fall back to sum of basis days
    lead_time_days = rollup.calculated_total_lead_time_days
    if lead_time_days is None:
        lead_time_days = None
        for dep_type_key in ("fabric", "logistics", "packaging"):
            entry = rollup.lead_time_basis.get(dep_type_key, {})
            if entry.get("days"):
                lead_time_days = (lead_time_days or 0) + entry["days"]

    # Estimate unit price from price_basis
    unit_price = None
    currency = None
    for dep_type_key, entry in rollup.price_basis.items():
        if entry.get("value") and unit_price is None:
            unit_price = entry["value"]
            currency = entry.get("currency")

    red_flags = rollup.risk_flags.copy()
    if rollup.unresolved_dependencies:
        red_flags.append(f"Unresolved: {', '.join(rollup.unresolved_dependencies)}")

    # Build structured lead time breakdown for B-side consumption
    lead_time_breakdown = {
        "fabric_days": rollup.material_ready_days,
        "material_days": rollup.material_ready_days,
        "production_days": rollup.production_days,
        "qc_days": rollup.qc_days_estimate,
        "packaging_days": rollup.packaging_days_estimate,
        "logistics_days": rollup.logistics_days_estimate,
        "risk_buffer_days": rollup.risk_buffer_days,
        "calculated_total_days": rollup.calculated_total_lead_time_days,
        "supplier_stated_total_days": rollup.supplier_stated_total_lead_time_days,
        "evidence_refs": rollup.lead_time_evidence_refs,
        "components": rollup.lead_time_components,
    }

    response_record = SupplierResponseRecord(
        response_id=f"ROLLUP-RESP-{uuid.uuid4().hex[:8].upper()}",
        rfq_id=b_workspace_id,
        b_workspace_id=b_workspace_id,
        supplier_id=rollup.main_supplier_actor_id,
        supplier_name=supplier_name,
        can_make=rollup.can_accept_order,
        capacity_available=True,
        material_available=bool(rollup.material_basis),
        estimated_lead_time_days=lead_time_days,
        unit_price=unit_price,
        total_price=(unit_price * 100 if unit_price else None),
        currency=currency,
        qc_available=bool(rollup.qc_basis),
        logistics_notes=str(rollup.logistics_basis) if rollup.logistics_basis else None,
        red_flags=red_flags,
        completeness_score=rollup.completeness_score,
        confidence_score=rollup.confidence_score,
        raw_response=rollup.recommended_response_to_buyer_en,
        lead_time_breakdown=lead_time_breakdown,
    )

    intake_supplier_response(b_workspace_id, response_record)

    result = SubmitResult(
        submit_id=f"SUBMIT-{uuid.uuid4().hex[:8].upper()}",
        rollup_id=rollup.rollup_id,
        project_id=rollup.project_id,
        b_workspace_id=b_workspace_id,
        supplier_response_record_id=response_record.response_id,
        status="submitted",
        submitted_at=datetime.now(timezone.utc).isoformat(),
    )

    # Log with project_id as b_workspace_id so project-level event queries find it
    log_m_event(
        event_type="SUPPLIER_RESPONSE_ROLLUP_SUBMITTED_TO_B_SIDE",
        b_workspace_id=rollup.project_id,
        supplier_id=rollup.main_supplier_actor_id,
        payload={
            "submit_id": result.submit_id,
            "rollup_id": rollup.rollup_id,
            "b_workspace_id": b_workspace_id,
            "response_record_id": response_record.response_id,
            "can_accept_order": rollup.can_accept_order,
            "completeness_score": rollup.completeness_score,
            "confidence_score": rollup.confidence_score,
        },
    )

    return result
