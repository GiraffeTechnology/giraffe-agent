"""
GLTG — Giraffe Lead Time Graph engine.

GLTG is the AIVAN-facing lead-time / feasibility model. It uses the existing
component-based lead-time calculator as its deterministic core, then promotes the
result into a probabilistic, auditable GLTG output with P50/P80/P90 estimates.

Design rules:
- Supplier-stated lead time is evidence, not final truth.
- P80 is the default buyer-deadline feasibility basis.
- GLTG must leave an evidence trail and must never silently degrade.
- If a future external GLTG service is unavailable, callers must mark fallback
  explicitly; this local implementation is the embedded GLTG engine.
"""

from __future__ import annotations

import math

from src.lead_time.lead_time_calculator import calculate_lead_time_path
from src.lead_time.models import LeadTimePath, ProductionCapacity
from src.lead_time.evidence import EVIDENCE_TYPE_AI_CALCULATED, make_evidence_ref

GLTG_MODEL_NAME = "GLTG"
GLTG_MODEL_VERSION = "0.1.0-local"
GLTG_FEASIBILITY_BASIS = "p80"


def _uncertainty_days(path: LeadTimePath) -> int:
    """Return deterministic uncertainty buffer for P90 calculation."""
    confidence_gap = max(0.0, 1.0 - min(path.confidence_score, path.completeness_score))
    confidence_component = math.ceil(path.total_lead_time_days * 0.10 * confidence_gap)
    risk_component = math.ceil(len(path.risk_flags) * 0.5)
    buffer_component = math.ceil(path.risk_buffer_days * 0.5)
    return max(1, confidence_component + risk_component + buffer_component)


def _apply_gltg_envelope(path: LeadTimePath) -> LeadTimePath:
    """Attach GLTG metadata and percentile estimates to a LeadTimePath."""
    uncertainty = _uncertainty_days(path)
    p80 = max(1, int(path.total_lead_time_days))
    p50 = max(1, math.ceil(p80 - max(1, uncertainty / 2)))
    p90 = max(p80, p80 + uncertainty)

    path.model_name = GLTG_MODEL_NAME
    path.model_version = GLTG_MODEL_VERSION
    path.p50_lead_time_days = p50
    path.p80_lead_time_days = p80
    path.p90_lead_time_days = p90
    path.feasibility_basis = GLTG_FEASIBILITY_BASIS
    path.fallback_model_used = False

    if "gltg_embedded_model_used" not in path.risk_flags:
        path.risk_flags.append("gltg_embedded_model_used")

    gltg_evidence = make_evidence_ref(
        EVIDENCE_TYPE_AI_CALCULATED,
        GLTG_MODEL_NAME,
        f"version:{GLTG_MODEL_VERSION};p50:{p50};p80:{p80};p90:{p90};basis:{GLTG_FEASIBILITY_BASIS}",
    )
    if gltg_evidence not in path.evidence_refs:
        path.evidence_refs.append(gltg_evidence)

    if path.deadline_days is not None:
        path.slack_days = path.deadline_days - p80
        path.feasible_before_deadline = path.slack_days >= 0
        if not path.feasible_before_deadline:
            flag = f"gltg_p80_deadline_infeasible:{p80}d_exceeds_{path.deadline_days}d"
            if flag not in path.risk_flags:
                path.risk_flags.append(flag)

    path.risk_score = round(len(path.risk_flags) * 0.1, 2)
    return path


def calculate_gltg_lead_time_path(
    supplier_response_id: str,
    supplier_id: str,
    supplier_name: str,
    project_id: str,
    quantity: int | None = None,
    fabric_days: int | None = None,
    trim_days: int | None = None,
    packaging_material_days: int | None = None,
    subcontract_days: int | None = None,
    qc_days: int | None = None,
    packaging_days: int | None = None,
    logistics_days: int | None = None,
    production_capacity: ProductionCapacity | None = None,
    supplier_stated_total_days: int | None = None,
    risk_flags: list[str] | None = None,
    missing_fields: list[str] | None = None,
    confidence_score: float = 0.5,
    completeness_score: float = 0.5,
    unit_price: float | None = None,
    total_price: float | None = None,
    currency: str | None = None,
    buyer_deadline_days: int | None = None,
    upstream_evidence_refs: list[str] | None = None,
) -> LeadTimePath:
    """Calculate an AIVAN supplier path through embedded GLTG.

    This intentionally mirrors calculate_lead_time_path() so AIVAN can migrate
    from the old deterministic calculator to GLTG without changing its caller
    contract.
    """
    path = calculate_lead_time_path(
        supplier_response_id=supplier_response_id,
        supplier_id=supplier_id,
        supplier_name=supplier_name,
        project_id=project_id,
        quantity=quantity,
        fabric_days=fabric_days,
        trim_days=trim_days,
        packaging_material_days=packaging_material_days,
        subcontract_days=subcontract_days,
        qc_days=qc_days,
        packaging_days=packaging_days,
        logistics_days=logistics_days,
        production_capacity=production_capacity,
        supplier_stated_total_days=supplier_stated_total_days,
        risk_flags=risk_flags,
        missing_fields=missing_fields,
        confidence_score=confidence_score,
        completeness_score=completeness_score,
        unit_price=unit_price,
        total_price=total_price,
        currency=currency,
        buyer_deadline_days=buyer_deadline_days,
        upstream_evidence_refs=upstream_evidence_refs,
    )
    return _apply_gltg_envelope(path)
