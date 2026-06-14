"""
B-side delivery feasibility simulation engine.
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


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


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


def run_feasibility_simulation(b_workspace_id: str, max_recommended: int = 0) -> FeasibilityReport:
    """
    Run delivery feasibility simulation for all available supplier responses with can_make=True.

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

    # Only consider suppliers who can make the item
    eligible = [r for r in workspace.supplier_responses if r.can_make is True]

    # Sort by composite score descending (rank all available supplier options)
    scored = sorted(eligible, key=_score_response, reverse=True)

    # Apply cap only for display purposes, never as a hard requirement
    display_paths = scored
    if max_recommended and max_recommended > 0:
        display_paths = scored[:max_recommended]

    paths: list[DeliveryPath] = []
    for rank, resp in enumerate(display_paths, start=1):
        path = _build_path(resp, rfq_id, rank)
        paths.append(path)

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
