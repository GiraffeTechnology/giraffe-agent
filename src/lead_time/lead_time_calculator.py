"""
Canonical lead time calculator.
Calculates delivery feasibility from path components, not from a single supplier-stated lead_time_days field.
"""
import math
import uuid
from typing import Any

from src.lead_time.models import LeadTimeComponent, LeadTimePath, ProductionCapacity
from src.lead_time.evidence import (
    EVIDENCE_TYPE_SUPPLIER_STATED,
    EVIDENCE_TYPE_AI_CALCULATED,
    EVIDENCE_TYPE_DEFAULT_ASSUMPTION,
    make_evidence_ref,
)


_DEFAULT_QC_DAYS = 2.0
_DEFAULT_PACKAGING_DAYS = 1.0
_DEFAULT_LOGISTICS_DAYS = 7.0
_DEFAULT_BUFFER_DAYS = 2.0
_DEFAULT_DAILY_CAPACITY = 50.0
_DEFAULT_SETUP_DAYS = 1.0


def _risk_buffer(risk_flags: list[str], missing_fields: list[str], confidence: float) -> float:
    """Calculate risk buffer days based on risk signals."""
    buffer = 0.0
    flag_text = " ".join(risk_flags).lower()

    if any(k in flag_text for k in ("substitute", "substitute_material")):
        buffer += 2.0
    if any(k in flag_text for k in ("unconfirmed_logistics", "logistics_tbc", "logistics not")):
        buffer += 2.0
    if any(k in flag_text for k in ("unconfirmed_qc", "qc_tbc", "qc not")):
        buffer += 1.0
    if any(k in flag_text for k in ("revision", "supplier_revision", "pending_revision")):
        buffer += 2.0
    if any(k in flag_text for k in ("compressed", "tight_schedule", "schedule_risk")):
        buffer += 3.0
    if any(k in flag_text for k in ("price_not_confirmed", "price_tbc")):
        buffer += 0.0  # price risk doesn't add lead time
    if any(k in flag_text for k in ("moq", "minimum_order")):
        buffer += 1.0

    # Low confidence adds buffer
    if confidence < 0.4:
        buffer += 3.0
    elif confidence < 0.6:
        buffer += 1.5
    elif confidence < 0.75:
        buffer += 0.5

    # Missing fields add buffer
    if "lead_time_days" in missing_fields or "lead_time" in missing_fields:
        buffer += 3.0
    if "price" in missing_fields or "unit_price" in missing_fields:
        buffer += 0.0
    if len(missing_fields) > 3:
        buffer += 2.0

    return buffer


def calculate_lead_time_path(
    supplier_response_id: str,
    supplier_id: str,
    supplier_name: str,
    project_id: str,
    quantity: int | None = None,
    # Upstream breakdown (from M-side rollup lead_time_basis)
    fabric_days: int | None = None,
    trim_days: int | None = None,
    packaging_material_days: int | None = None,
    subcontract_days: int | None = None,
    qc_days: int | None = None,
    packaging_days: int | None = None,
    logistics_days: int | None = None,
    # Capacity (from manufacturer)
    production_capacity: ProductionCapacity | None = None,
    # Supplier-stated total (for comparison only)
    supplier_stated_total_days: int | None = None,
    # Risk and confidence
    risk_flags: list[str] | None = None,
    missing_fields: list[str] | None = None,
    confidence_score: float = 0.5,
    completeness_score: float = 0.5,
    # Pricing
    unit_price: float | None = None,
    total_price: float | None = None,
    currency: str | None = None,
    # Deadline
    buyer_deadline_days: int | None = None,
    # Evidence refs
    upstream_evidence_refs: list[str] | None = None,
) -> LeadTimePath:
    """
    Calculate lead time from path components, not from supplier-stated total.

    Rules:
    - material, trim, packaging-material, subcontract can run in PARALLEL -> use max()
    - production, QC, packaging, logistics run SEQUENTIALLY -> use sum()
    - supplier-stated lead time is preserved as evidence but not trusted blindly
    - missing fields create risk flags, not sentinel 999 values
    """
    risk_flags = risk_flags or []
    missing_fields = missing_fields or []
    upstream_evidence_refs = upstream_evidence_refs or []
    components: list[LeadTimeComponent] = []
    evidence_refs = list(upstream_evidence_refs)
    path_risk_flags = list(risk_flags)

    # -- 1. Material lead times (run in PARALLEL -> max) ----------------------
    parallel_material_days: list[tuple[str, float, str, str]] = []  # (type, days, dep_type, evidence_ref)

    def _add_material(days: int | None, dep_type: str, source: str) -> None:
        if days is not None:
            ev_ref = make_evidence_ref(EVIDENCE_TYPE_SUPPLIER_STATED, source, f"{dep_type}:{days}d")
            parallel_material_days.append((dep_type, float(days), source, ev_ref))
        else:
            ev_ref = make_evidence_ref(EVIDENCE_TYPE_DEFAULT_ASSUMPTION, source, f"{dep_type}:unknown")
            parallel_material_days.append((dep_type, 3.0, source, ev_ref))
            if f"{dep_type}_lead_time_unknown" not in path_risk_flags:
                path_risk_flags.append(f"{dep_type}_lead_time_unknown")

    # Fabric lead time (most important for apparel)
    if fabric_days is not None:
        _add_material(fabric_days, "material", supplier_response_id)
    # Trim
    if trim_days is not None:
        _add_material(trim_days, "trim", supplier_response_id)
    # Packaging material
    if packaging_material_days is not None:
        _add_material(packaging_material_days, "packaging_material", supplier_response_id)
    # Subcontract
    if subcontract_days is not None:
        _add_material(subcontract_days, "subcontract", supplier_response_id)

    if not parallel_material_days:
        # No upstream breakdown -- use supplier-stated or default
        if supplier_stated_total_days is not None:
            # Rough estimate: assume material is ~40% of total
            est_material = max(3, int(supplier_stated_total_days * 0.4))
            ev_ref = make_evidence_ref(EVIDENCE_TYPE_AI_CALCULATED, supplier_response_id, f"estimated_from_total:{est_material}d")
            parallel_material_days.append(("material", float(est_material), supplier_response_id, ev_ref))
        else:
            ev_ref = make_evidence_ref(EVIDENCE_TYPE_DEFAULT_ASSUMPTION, supplier_response_id, "material:default_3d")
            parallel_material_days.append(("material", 3.0, supplier_response_id, ev_ref))
            path_risk_flags.append("material_lead_time_unknown")

    material_ready_days = max(d for _, d, _, _ in parallel_material_days)

    # Create material components
    mat_start = 0.0
    for dep_type, days, src, ev_ref in parallel_material_days:
        comp = LeadTimeComponent(
            component_id=f"COMP-{uuid.uuid4().hex[:6].upper()}",
            component_type="material" if dep_type in ("material", "fabric") else dep_type if dep_type in ("trim", "subcontract") else "material",
            source_actor_id=src,
            source_response_id=supplier_response_id,
            duration_days=days,
            earliest_start_day=mat_start,
            earliest_finish_day=mat_start + days,
            can_parallelize=True,
            evidence_type=EVIDENCE_TYPE_SUPPLIER_STATED if "default" not in ev_ref else EVIDENCE_TYPE_DEFAULT_ASSUMPTION,
            evidence_ref=ev_ref,
            risk_flags=[f for f in path_risk_flags if dep_type in f],
        )
        components.append(comp)
        if ev_ref not in evidence_refs:
            evidence_refs.append(ev_ref)

    # -- 2. Production days ---------------------------------------------------
    cap = production_capacity or ProductionCapacity(
        actor_id=supplier_id,
        daily_capacity_units=_DEFAULT_DAILY_CAPACITY,
        setup_days=_DEFAULT_SETUP_DAYS,
        queue_days=0.0,
        confidence_score=0.4,
        evidence_ref=make_evidence_ref(EVIDENCE_TYPE_DEFAULT_ASSUMPTION, supplier_id, "default_capacity"),
    )

    qty = quantity or 100
    production_units_days = math.ceil(qty / cap.daily_capacity_units)
    production_total_days = cap.queue_days + cap.setup_days + production_units_days

    prod_ev_ref = cap.evidence_ref or make_evidence_ref(
        EVIDENCE_TYPE_AI_CALCULATED,
        supplier_id,
        f"qty:{qty}/cap:{cap.daily_capacity_units}+setup:{cap.setup_days}+queue:{cap.queue_days}",
    )
    if prod_ev_ref not in evidence_refs:
        evidence_refs.append(prod_ev_ref)

    prod_start = material_ready_days
    prod_comp = LeadTimeComponent(
        component_id=f"COMP-{uuid.uuid4().hex[:6].upper()}",
        component_type="production",
        source_actor_id=supplier_id,
        source_response_id=supplier_response_id,
        duration_days=production_total_days,
        earliest_start_day=prod_start,
        earliest_finish_day=prod_start + production_total_days,
        can_parallelize=False,
        evidence_type=EVIDENCE_TYPE_AI_CALCULATED,
        evidence_ref=prod_ev_ref,
        risk_flags=[],
    )
    components.append(prod_comp)

    # -- 3. Post-production: QC, packaging, logistics (sequential, sum) --------
    post_start = prod_start + production_total_days

    # QC
    actual_qc_days = qc_days if qc_days is not None else _DEFAULT_QC_DAYS
    qc_evidence = EVIDENCE_TYPE_SUPPLIER_STATED if qc_days is not None else EVIDENCE_TYPE_DEFAULT_ASSUMPTION
    qc_ev_ref = make_evidence_ref(qc_evidence, supplier_response_id, f"qc:{actual_qc_days}d")
    if qc_ev_ref not in evidence_refs:
        evidence_refs.append(qc_ev_ref)

    qc_comp = LeadTimeComponent(
        component_id=f"COMP-{uuid.uuid4().hex[:6].upper()}",
        component_type="qc",
        source_actor_id=supplier_id,
        source_response_id=supplier_response_id,
        duration_days=actual_qc_days,
        earliest_start_day=post_start,
        earliest_finish_day=post_start + actual_qc_days,
        can_parallelize=False,
        evidence_type=qc_evidence,
        evidence_ref=qc_ev_ref,
        risk_flags=["qc_duration_assumed"] if qc_days is None else [],
    )
    components.append(qc_comp)

    # Packaging
    actual_pkg_days = packaging_days if packaging_days is not None else _DEFAULT_PACKAGING_DAYS
    pkg_evidence = EVIDENCE_TYPE_SUPPLIER_STATED if packaging_days is not None else EVIDENCE_TYPE_DEFAULT_ASSUMPTION
    pkg_ev_ref = make_evidence_ref(pkg_evidence, supplier_response_id, f"packaging:{actual_pkg_days}d")
    if pkg_ev_ref not in evidence_refs:
        evidence_refs.append(pkg_ev_ref)

    pkg_comp = LeadTimeComponent(
        component_id=f"COMP-{uuid.uuid4().hex[:6].upper()}",
        component_type="packaging",
        source_actor_id=supplier_id,
        source_response_id=supplier_response_id,
        duration_days=actual_pkg_days,
        earliest_start_day=post_start + actual_qc_days,
        earliest_finish_day=post_start + actual_qc_days + actual_pkg_days,
        can_parallelize=False,
        evidence_type=pkg_evidence,
        evidence_ref=pkg_ev_ref,
        risk_flags=[],
    )
    components.append(pkg_comp)

    # Logistics
    actual_lgs_days = logistics_days if logistics_days is not None else _DEFAULT_LOGISTICS_DAYS
    lgs_evidence = EVIDENCE_TYPE_SUPPLIER_STATED if logistics_days is not None else EVIDENCE_TYPE_DEFAULT_ASSUMPTION
    lgs_ev_ref = make_evidence_ref(lgs_evidence, supplier_response_id, f"logistics:{actual_lgs_days}d")
    if lgs_ev_ref not in evidence_refs:
        evidence_refs.append(lgs_ev_ref)

    lgs_comp = LeadTimeComponent(
        component_id=f"COMP-{uuid.uuid4().hex[:6].upper()}",
        component_type="logistics",
        source_actor_id=supplier_id,
        source_response_id=supplier_response_id,
        duration_days=actual_lgs_days,
        earliest_start_day=post_start + actual_qc_days + actual_pkg_days,
        earliest_finish_day=post_start + actual_qc_days + actual_pkg_days + actual_lgs_days,
        can_parallelize=False,
        evidence_type=lgs_evidence,
        evidence_ref=lgs_ev_ref,
        risk_flags=["logistics_duration_assumed"] if logistics_days is None else [],
    )
    components.append(lgs_comp)

    post_production_total = actual_qc_days + actual_pkg_days + actual_lgs_days

    # -- 4. Risk buffer -------------------------------------------------------
    buffer_days = _risk_buffer(path_risk_flags, missing_fields, confidence_score)

    if buffer_days > 0:
        buf_ev_ref = make_evidence_ref(EVIDENCE_TYPE_AI_CALCULATED, supplier_response_id,
                                       f"risk_buffer:{buffer_days}d,flags:{len(path_risk_flags)}")
        if buf_ev_ref not in evidence_refs:
            evidence_refs.append(buf_ev_ref)
        buf_start = post_start + post_production_total
        buf_comp = LeadTimeComponent(
            component_id=f"COMP-{uuid.uuid4().hex[:6].upper()}",
            component_type="buffer",
            source_actor_id=supplier_id,
            source_response_id=supplier_response_id,
            duration_days=buffer_days,
            earliest_start_day=buf_start,
            earliest_finish_day=buf_start + buffer_days,
            can_parallelize=False,
            evidence_type=EVIDENCE_TYPE_AI_CALCULATED,
            evidence_ref=buf_ev_ref,
            risk_flags=path_risk_flags,
        )
        components.append(buf_comp)

    # -- 5. Critical path = sequential sum of all stages ----------------------
    # material_ready -> production -> qc -> packaging -> logistics -> buffer
    critical_path = material_ready_days + production_total_days + post_production_total + buffer_days
    total_lead_time_days = math.ceil(critical_path)

    # -- 6. Compare vs supplier-stated ----------------------------------------
    consistency_note = None
    if supplier_stated_total_days is not None:
        diff = abs(total_lead_time_days - supplier_stated_total_days)
        pct = diff / max(1, supplier_stated_total_days)
        if pct < 0.15:
            consistency_note = f"Calculated {total_lead_time_days}d consistent with supplier-stated {supplier_stated_total_days}d (diff={diff}d)"
            confidence_score = min(1.0, confidence_score + 0.1)
        else:
            consistency_note = (
                f"Calculated {total_lead_time_days}d differs from supplier-stated {supplier_stated_total_days}d "
                f"(diff={diff}d, {pct:.0%}). Using calculated value."
            )
            path_risk_flags.append("supplier_stated_lead_time_inconsistent")

    # -- 7. Deadline check ----------------------------------------------------
    slack_days = None
    feasible = True
    if buyer_deadline_days is not None:
        slack_days = buyer_deadline_days - total_lead_time_days
        feasible = slack_days >= 0
        if not feasible:
            path_risk_flags.append(f"deadline_infeasible:calculated_{total_lead_time_days}d_exceeds_{buyer_deadline_days}d")

    risk_score = round(len(path_risk_flags) * 0.1, 2)

    return LeadTimePath(
        path_id=f"LTP-{uuid.uuid4().hex[:8].upper()}",
        project_id=project_id,
        supplier_id=supplier_id,
        supplier_name=supplier_name,
        quantity=quantity,
        components=components,
        critical_path_days=round(critical_path, 2),
        total_lead_time_days=total_lead_time_days,
        earliest_delivery_day=total_lead_time_days,
        feasible_before_deadline=feasible,
        deadline_days=buyer_deadline_days,
        slack_days=slack_days,
        total_price=total_price,
        unit_price=unit_price,
        currency=currency,
        confidence_score=round(confidence_score, 3),
        completeness_score=round(completeness_score, 3),
        risk_score=risk_score,
        risk_flags=path_risk_flags,
        evidence_refs=evidence_refs,
        material_ready_days=material_ready_days,
        production_days=production_total_days,
        post_production_days=post_production_total,
        risk_buffer_days=buffer_days,
        supplier_stated_lead_time_days=supplier_stated_total_days,
        lead_time_consistency_note=consistency_note,
    )
