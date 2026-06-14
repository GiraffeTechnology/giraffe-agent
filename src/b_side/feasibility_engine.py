"""
B-side delivery feasibility engine — uses canonical Lead Time Path Model.

Ranks available supplier responses by lead time, price, confidence, and risk.

Supplier count rules:
- Works with 1 supplier, 2, 3, or more than 3 suppliers.
- Comparison is optional, not mandatory.
- No minimum supplier count is required.
- If only one supplier replies, a single delivery path is returned.
- If more than 3 suppliers reply, returns all ranked paths (caller may cap at 3 for display).
- If no supplier has replied, returns an empty paths list (does not fail).
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


def _score_response(resp: SupplierResponseRecord) -> float:
    """
    Composite supplier score used for ranking available supplier options.
    Higher is better.
    Score = confidence_score / (1 + lead_time_days/30) / (1 + len(red_flags)*0.1)
    """
    lead_time = resp.estimated_lead_time_days or 999
    red_flag_count = len(resp.red_flags)
    confidence = resp.confidence_score or 0.5
    score = confidence / (1 + lead_time / 30.0) / (1 + red_flag_count * 0.1)
    return round(score, 4)


def _build_path(resp: SupplierResponseRecord, rfq_id: str, rank: int) -> DeliveryPath:
    return DeliveryPath(
        path_id=f"PATH-{uuid.uuid4().hex[:8].upper()}",
        rfq_id=rfq_id,
        supplier_id=resp.supplier_id,
        supplier_name=resp.supplier_name,
        lead_time_days=resp.estimated_lead_time_days,
        unit_price=resp.unit_price,
        currency=resp.currency,
        total_price=resp.total_price,
        risk_score=round(len(resp.red_flags) * 0.1, 2),
        confidence_score=resp.confidence_score,
        notes="; ".join(resp.red_flags) if resp.red_flags else None,
        rank=rank,
    )


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


def run_feasibility_simulation(b_workspace_id: str, max_recommended: int = 0) -> FeasibilityReport:
    """
    Run delivery feasibility simulation using the canonical Lead Time Path Model.

    Returns FeasibilityReport with ranked delivery paths (available supplier options).
    Persists the report to the workspace.

    Args:
        b_workspace_id: The B-side workspace ID.
        max_recommended: If > 0, caps the returned paths to this number (e.g. 3 for display).
                         Default 0 means return all available ranked paths.

    Supplier count behavior:
        - 0 suppliers: returns empty paths list, status remains feasibility_complete.
        - 1 supplier:  returns single_supplier_option_ready status, one ranked path.
        - 2-3 suppliers: returns available_supplier_options_ready, ranked paths.
        - >3 suppliers: returns ranked_delivery_paths_ready, all paths ranked;
                        if max_recommended > 0, caps at max_recommended.
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

    if max_recommended and max_recommended > 0:
        labeled_paths = labeled_paths[:max_recommended]

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


def get_feasibility_status(paths: list[DeliveryPath]) -> str:
    """Return a status label based on the number of available supplier options."""
    n = len(paths)
    if n == 0:
        return "no_supplier_response_yet"
    if n == 1:
        return "single_supplier_option_ready"
    if n <= 3:
        return "available_supplier_options_ready"
    return "ranked_delivery_paths_ready"
