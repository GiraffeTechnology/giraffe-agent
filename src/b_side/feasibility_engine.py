"""
B-side delivery feasibility engine — uses canonical Lead Time Path Model.
"""
import uuid
from datetime import datetime, timezone

from src.core_schema.b_side_types import (
    BWWorkspace,
    DeliveryPath,
    FeasibilityReport,
    SupplierResponseRecord,
)
from src.b_side.workspace import get_b_workspace, save_b_workspace
from src.lead_time.models import LeadTimePath, ProductionCapacity
from src.lead_time.lead_time_calculator import calculate_lead_time_path
from src.lead_time.path_ranker import assign_labels


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _response_to_path_input(resp: SupplierResponseRecord) -> dict:
    """Extract lead time inputs from a SupplierResponseRecord."""
    breakdown = resp.lead_time_breakdown or {}

    return {
        "response_id": resp.response_id,
        "supplier_id": resp.supplier_id,
        "supplier_name": resp.supplier_name,
        "can_make": resp.can_make,
        "fabric_days": breakdown.get("fabric_days") or breakdown.get("material_days"),
        "trim_days": breakdown.get("trim_days"),
        "packaging_material_days": breakdown.get("packaging_material_days"),
        "subcontract_days": breakdown.get("subcontract_days"),
        "qc_days": breakdown.get("qc_days"),
        "packaging_days": breakdown.get("packaging_days"),
        "logistics_days": breakdown.get("logistics_days"),
        "supplier_stated_total_days": resp.estimated_lead_time_days,
        "risk_flags": list(resp.red_flags),
        "missing_fields": [],
        "confidence_score": resp.confidence_score or 0.5,
        "completeness_score": resp.completeness_score or 0.5,
        "unit_price": resp.unit_price,
        "total_price": resp.total_price,
        "currency": resp.currency,
        "evidence_refs": list(breakdown.get("evidence_refs", [])),
    }


def _path_to_delivery_path(lt_path: LeadTimePath, rfq_id: str) -> DeliveryPath:
    """Convert LeadTimePath to DeliveryPath (B-side schema)."""
    critical_summary_parts = []
    if lt_path.material_ready_days > 0:
        critical_summary_parts.append(f"material_ready={lt_path.material_ready_days:.0f}d")
    if lt_path.production_days > 0:
        critical_summary_parts.append(f"production={lt_path.production_days:.0f}d")
    if lt_path.post_production_days > 0:
        critical_summary_parts.append(f"post_prod={lt_path.post_production_days:.0f}d")
    if lt_path.risk_buffer_days > 0:
        critical_summary_parts.append(f"buffer={lt_path.risk_buffer_days:.0f}d")
    critical_summary = " + ".join(critical_summary_parts) + f" = {lt_path.total_lead_time_days}d"

    notes_parts = []
    if lt_path.lead_time_consistency_note:
        notes_parts.append(lt_path.lead_time_consistency_note)
    if lt_path.risk_flags:
        notes_parts.append(f"Risks: {'; '.join(lt_path.risk_flags[:3])}")

    return DeliveryPath(
        path_id=lt_path.path_id,
        rfq_id=rfq_id,
        supplier_id=lt_path.supplier_id,
        supplier_name=lt_path.supplier_name,
        lead_time_days=lt_path.total_lead_time_days,
        unit_price=lt_path.unit_price,
        currency=lt_path.currency,
        total_price=lt_path.total_price,
        risk_score=lt_path.risk_score,
        confidence_score=lt_path.confidence_score,
        notes="; ".join(notes_parts) if notes_parts else None,
        rank=lt_path.rank,
        calculated_lead_time_days=lt_path.total_lead_time_days,
        supplier_stated_lead_time_days=lt_path.supplier_stated_lead_time_days,
        lead_time_components=[c.model_dump() for c in lt_path.components],
        critical_path_summary=critical_summary,
        slack_days=lt_path.slack_days,
        deadline_feasible=lt_path.feasible_before_deadline,
        evidence_refs=lt_path.evidence_refs,
        lead_time_risk_flags=lt_path.risk_flags,
        label=lt_path.label,
    )


def run_feasibility_simulation(b_workspace_id: str) -> FeasibilityReport:
    """
    Run delivery feasibility simulation using the canonical Lead Time Path Model.
    Replaces simple lead_time_days ranking with full path component calculation.
    """
    workspace = get_b_workspace(b_workspace_id)
    req = workspace.buyer_requirement
    rfq_id = req.rfq_id if req else workspace.rfq_id

    # Extract deadline if available
    buyer_deadline_days = None
    if req and req.deadline:
        # deadline is stored as string; try to extract days from specs_json
        buyer_deadline_days = req.specs_json.get("deadline_days")

    quantity = req.quantity if req else None

    eligible = [r for r in workspace.supplier_responses if r.can_make is True]

    lt_paths: list[LeadTimePath] = []
    for resp in eligible:
        inputs = _response_to_path_input(resp)
        lt_path = calculate_lead_time_path(
            supplier_response_id=inputs["response_id"],
            supplier_id=inputs["supplier_id"],
            supplier_name=inputs["supplier_name"],
            project_id=b_workspace_id,
            quantity=quantity,
            fabric_days=inputs.get("fabric_days"),
            trim_days=inputs.get("trim_days"),
            packaging_material_days=inputs.get("packaging_material_days"),
            subcontract_days=inputs.get("subcontract_days"),
            qc_days=inputs.get("qc_days"),
            packaging_days=inputs.get("packaging_days"),
            logistics_days=inputs.get("logistics_days"),
            supplier_stated_total_days=inputs.get("supplier_stated_total_days"),
            risk_flags=inputs.get("risk_flags", []),
            missing_fields=inputs.get("missing_fields", []),
            confidence_score=inputs.get("confidence_score", 0.5),
            completeness_score=inputs.get("completeness_score", 0.5),
            unit_price=inputs.get("unit_price"),
            total_price=inputs.get("total_price"),
            currency=inputs.get("currency"),
            buyer_deadline_days=buyer_deadline_days,
            upstream_evidence_refs=inputs.get("evidence_refs", []),
        )
        lt_paths.append(lt_path)

    # Assign labels and rank
    labeled_paths = assign_labels(lt_paths) if lt_paths else []

    paths: list[DeliveryPath] = [
        _path_to_delivery_path(lp, rfq_id) for lp in labeled_paths
    ]

    report = FeasibilityReport(
        rfq_id=rfq_id,
        b_workspace_id=b_workspace_id,
        paths=paths,
        generated_at=_utcnow(),
        selected_path_id=paths[0].path_id if paths else None,
    )

    workspace.feasibility_report = report
    workspace.status = "feasibility_complete"
    save_b_workspace(workspace)

    return report
