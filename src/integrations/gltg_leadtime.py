"""Client-backed lead-time adapter.

Replaces the former in-tree lead-time engine. ``estimate_lead_time_path`` builds a
GLTG API request from supplier component days, calls the standalone GLTG service
via the thin HTTP client, and maps the response into the canonical
``LeadTimePath`` DTO used by the B-side / M-side.

No lead-time math happens here -- the GLTG service owns it. On GLTG failure this
raises ``GLTGUnavailableError`` rather than silently substituting a local
calculation.
"""

from __future__ import annotations

import uuid

from src.integrations.gltg_client import GLTGClient
from src.lead_time.evidence import EVIDENCE_TYPE_AI_CALCULATED, make_evidence_ref
from src.lead_time.models import LeadTimeComponent, LeadTimePath


class GLTGUnavailableError(RuntimeError):
    """Raised when the GLTG service cannot be reached or returns an error."""


def _f(v) -> float:
    return float(v or 0)


def estimate_lead_time_path(
    *,
    supplier_response_id: str,
    supplier_id: str,
    supplier_name: str,
    project_id: str,
    quantity: int | None = None,
    fabric_days=None,
    trim_days=None,
    packaging_material_days=None,
    subcontract_days=None,
    qc_days=None,
    packaging_days=None,
    logistics_days=None,
    supplier_stated_total_days=None,
    production_capacity=None,
    risk_flags: list[str] | None = None,
    missing_fields: list[str] | None = None,
    confidence_score: float = 0.5,
    completeness_score: float = 0.5,
    unit_price=None,
    total_price=None,
    currency=None,
    buyer_deadline_days: int | None = None,
    upstream_evidence_refs: list[str] | None = None,
    client: GLTGClient | None = None,
) -> LeadTimePath:
    risk_flags = list(risk_flags or [])
    upstream_evidence_refs = list(upstream_evidence_refs or [])

    # Subcontract / surface-treatment is sourcing-side prep and extends material readiness.
    material_ready = _f(fabric_days) + _f(trim_days) + _f(packaging_material_days) + _f(subcontract_days)
    production = 0.0  # GLTG derives production from quantity + capacity
    qc = _f(qc_days)
    logistics = _f(logistics_days) + _f(packaging_days)

    # Respect a supplier-stated total when no component breakdown is available.
    if material_ready + production + qc + logistics == 0 and supplier_stated_total_days:
        production = _f(supplier_stated_total_days)

    capacity = None
    if production_capacity is not None:
        capacity = int(getattr(production_capacity, "daily_capacity_units", 0)) or None

    order = {"product_type": "apparel", "quantity": quantity or 0, "deadline_days": buyer_deadline_days}
    supplier = {
        "supplier_id": supplier_id,
        "name": supplier_name,
        "capacity_per_day": capacity,
        "material_ready_days": material_ready,
        "production_days": production,
        "qc_days": qc,
        "logistics_days": logistics,
        "confidence": confidence_score,
    }

    api = (client or GLTGClient()).estimate_lead_time(order=order, suppliers=[supplier], constraints={})
    if not api.ok or api.data is None:
        raise GLTGUnavailableError(api.error or "GLTG returned no data")
    data = api.data

    p50 = int(data["p50_days"]) if data.get("p50_days") is not None else None
    p80 = int(data["p80_days"]) if data.get("p80_days") is not None else None
    p90 = int(data["p90_days"]) if data.get("p90_days") is not None else None
    # P80 is the canonical feasibility basis for giraffe-agent: the "calculated"
    # lead time and deadline check use P80, not the optimistic median.
    total = int(p80 if p80 is not None else round(data["estimated_lead_time_days"] or 0))
    trace = (data.get("calculation_trace") or [{}])[0]
    prod_days = _f(trace.get("capacity_adjusted_production_days"))
    qc_trace = _f(trace.get("qc_days"))
    logi_trace = _f(trace.get("logistics_days"))
    mat_trace = _f(trace.get("material_ready_days"))
    buffer = float(max((p80 or total) - (p50 or total), 0))

    ev = make_evidence_ref(EVIDENCE_TYPE_AI_CALCULATED, source_id=supplier_response_id, note="gltg-api")
    components = [
        LeadTimeComponent(component_id=f"{supplier_response_id}-material", component_type="material",
                          duration_days=mat_trace, evidence_type=EVIDENCE_TYPE_AI_CALCULATED, evidence_ref=ev),
        LeadTimeComponent(component_id=f"{supplier_response_id}-production", component_type="production",
                          duration_days=prod_days, evidence_type=EVIDENCE_TYPE_AI_CALCULATED, evidence_ref=ev),
        LeadTimeComponent(component_id=f"{supplier_response_id}-qc", component_type="qc",
                          duration_days=qc_trace, evidence_type=EVIDENCE_TYPE_AI_CALCULATED, evidence_ref=ev),
        LeadTimeComponent(component_id=f"{supplier_response_id}-logistics", component_type="logistics",
                          duration_days=logi_trace, evidence_type=EVIDENCE_TYPE_AI_CALCULATED, evidence_ref=ev),
    ]

    # Feasibility on the P80 basis (the giraffe-agent contract).
    feasible = (total <= buyer_deadline_days) if buyer_deadline_days is not None else True
    slack = (buyer_deadline_days - total) if buyer_deadline_days is not None else None

    all_risk_flags = list(risk_flags)
    for w in data.get("warnings", []):
        code = w.get("code")
        if code and code not in all_risk_flags:
            all_risk_flags.append(code)

    return LeadTimePath(
        path_id=f"PATH-{uuid.uuid4().hex[:8].upper()}",
        project_id=project_id,
        supplier_id=supplier_id,
        supplier_name=supplier_name,
        quantity=quantity,
        components=components,
        critical_path_days=float(total),
        total_lead_time_days=total,
        earliest_delivery_day=total,
        feasible_before_deadline=feasible,
        deadline_days=buyer_deadline_days,
        slack_days=slack,
        total_price=total_price,
        unit_price=unit_price,
        currency=currency,
        confidence_score=confidence_score,
        completeness_score=completeness_score,
        risk_score=round(len(all_risk_flags) * 0.1, 2),
        risk_flags=all_risk_flags,
        evidence_refs=upstream_evidence_refs or [ev],
        model_name="GLTG",
        model_version="v1",
        p50_lead_time_days=p50,
        p80_lead_time_days=p80,
        p90_lead_time_days=p90,
        feasibility_basis="p80",
        fallback_model_used=False,
        material_ready_days=mat_trace,
        production_days=prod_days,
        post_production_days=qc_trace + logi_trace,
        risk_buffer_days=buffer,
        supplier_stated_lead_time_days=supplier_stated_total_days,
        lead_time_consistency_note=None,
    )
