"""
Supplier Response Rollup — merges approved upstream dependency options
into a structured buyer-facing response for Manufacturer M.
"""

import uuid
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from src.m_side.upstream.approval_gate import ApprovalResult
from src.m_side.upstream.option_engine import UpstreamOption
from src.m_side.m_event_logger import log_m_event


class ApprovedDependencyOption(BaseModel):
    dependency_id: str
    dependency_type: str
    upstream_actor_id: str
    option_label: str
    price_summary: str
    lead_time_summary: str
    risk_summary: str
    approved_by: str
    approval_mode: str


class SupplierResponseRollup(BaseModel):
    rollup_id: str
    project_id: str
    main_supplier_actor_id: str
    can_accept_order: bool
    main_capacity_summary: str
    approved_upstream_options: list[ApprovedDependencyOption] = Field(default_factory=list)
    material_basis: dict = Field(default_factory=dict)
    trim_basis: dict = Field(default_factory=dict)
    subcontract_basis: dict = Field(default_factory=dict)
    qc_basis: dict = Field(default_factory=dict)
    packaging_basis: dict = Field(default_factory=dict)
    logistics_basis: dict = Field(default_factory=dict)
    price_basis: dict = Field(default_factory=dict)
    lead_time_basis: dict = Field(default_factory=dict)
    unresolved_dependencies: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    completeness_score: float = 0.0
    confidence_score: float = 0.0
    recommended_response_to_buyer_en: str = ""
    recommended_response_to_buyer_zh: str = ""
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    # CAD-CNC matching evidence (Phase 4)
    cad_requirement_packet_id: str | None = None
    cad_cnc_match_id: str | None = None
    capability_fit_report_id: str | None = None
    cnc_parameter_match_summary: dict = Field(default_factory=dict)
    can_make_in_house: bool | None = None
    recommended_machine_ids: list[str] = Field(default_factory=list)
    capability_gaps: list[str] = Field(default_factory=list)
    upstream_dependency_basis: dict = Field(default_factory=dict)
    # NEW: structured lead time components for B-side consumption
    calculated_total_lead_time_days: int | None = None
    lead_time_components: list[dict] = Field(default_factory=list)
    lead_time_evidence_refs: list[str] = Field(default_factory=list)
    lead_time_risk_flags: list[str] = Field(default_factory=list)
    material_ready_days: int | None = None
    production_days: int | None = None
    qc_days_estimate: int | None = None
    packaging_days_estimate: int | None = None
    logistics_days_estimate: int | None = None
    risk_buffer_days: int | None = None
    supplier_stated_total_lead_time_days: int | None = None


def _extract_lead_days(lead_summary: str) -> int | None:
    import re
    m = re.search(r"(\d+)", lead_summary)
    return int(m.group(1)) if m else None


def _extract_price_value(price_summary: str) -> tuple[float | None, str | None]:
    import re
    m = re.search(r"(USD|CNY|RMB)\s*([\d.]+)", price_summary, re.IGNORECASE)
    if m:
        return float(m.group(2)), m.group(1).upper()
    m = re.search(r"([\d.]+)", price_summary)
    if m:
        return float(m.group(1)), None
    return None, None


def generate_supplier_response_rollup(
    project_id: str,
    main_supplier_actor_id: str,
    approval_results: list[ApprovalResult],
    product_summary: str,
    quantity: int | None = None,
    main_capacity_available: bool = True,
    main_capacity_note: str = "Internal capacity confirmed.",
    unresolved_dependency_types: list[str] | None = None,
    # CAD-CNC matching evidence (Phase 4, all optional)
    cad_requirement_packet_id: str | None = None,
    cad_cnc_match_id: str | None = None,
    capability_fit_report_id: str | None = None,
    cnc_parameter_match_summary: dict | None = None,
    can_make_in_house: bool | None = None,
    recommended_machine_ids: list[str] | None = None,
    capability_gaps: list[str] | None = None,
    upstream_dependency_basis: dict | None = None,
) -> SupplierResponseRollup:
    """
    Generate the final supplier response rollup from all approved upstream options.
    """
    approved_options: list[ApprovedDependencyOption] = []
    material_basis: dict = {}
    trim_basis: dict = {}
    subcontract_basis: dict = {}
    qc_basis: dict = {}
    packaging_basis: dict = {}
    logistics_basis: dict = {}
    price_basis: dict = {}
    lead_time_basis: dict = {}
    all_risk_flags: list[str] = []

    max_lead_time = 0

    for result in approval_results:
        opt = result.approved_option
        dep_type = opt.dependency_type

        ado = ApprovedDependencyOption(
            dependency_id=opt.dependency_id,
            dependency_type=dep_type,
            upstream_actor_id=opt.upstream_actor_id,
            option_label=opt.option_label,
            price_summary=opt.price_summary,
            lead_time_summary=opt.lead_time_summary,
            risk_summary=opt.risk_summary,
            approved_by=result.approved_by,
            approval_mode=result.mode,
        )
        approved_options.append(ado)

        lead_days = _extract_lead_days(opt.lead_time_summary)
        price_val, currency = _extract_price_value(opt.price_summary)

        basis_entry = {
            "supplier": opt.upstream_actor_id,
            "option": opt.option_label,
            "price": opt.price_summary,
            "lead_time": opt.lead_time_summary,
            "risk": opt.risk_summary,
        }

        if dep_type == "fabric":
            material_basis = basis_entry
        elif dep_type in {"trim", "raw_material"}:
            trim_basis = basis_entry
        elif dep_type in {"subcontract_process", "surface_treatment", "heat_treatment", "component"}:
            subcontract_basis = basis_entry
        elif dep_type == "qc_testing":
            qc_basis = basis_entry
        elif dep_type == "packaging":
            packaging_basis = basis_entry
        elif dep_type == "logistics":
            logistics_basis = basis_entry

        if price_val is not None:
            price_basis[dep_type] = {"value": price_val, "currency": currency, "summary": opt.price_summary}
        if lead_days is not None:
            lead_time_basis[dep_type] = {"days": lead_days, "summary": opt.lead_time_summary}
            if lead_days > max_lead_time:
                max_lead_time = lead_days

        if opt.risk_summary and opt.risk_summary.lower() != "no significant risks":
            all_risk_flags.append(f"{dep_type}: {opt.risk_summary}")

    unresolved = unresolved_dependency_types or []
    if unresolved:
        all_risk_flags.append(f"Unresolved dependencies: {', '.join(unresolved)}")

    can_accept = main_capacity_available and len(unresolved) == 0

    # Production lead time estimate: fabric lead + sewing + QC + logistics buffer
    fabric_lead = lead_time_basis.get("fabric", {}).get("days", 0)
    logistics_lead = lead_time_basis.get("logistics", {}).get("days", 0)
    sewing_days = max(7, (quantity or 100) // 20)  # rough estimate
    total_lead = fabric_lead + sewing_days + logistics_lead + 3  # 3 days buffer
    lead_summary = f"{total_lead} days (fabric {fabric_lead}d + sewing ~{sewing_days}d + logistics {logistics_lead}d + 3d buffer)"

    completeness_score = round(
        0.3 * (1 if material_basis else 0)
        + 0.15 * (1 if trim_basis else 0)
        + 0.1 * (1 if packaging_basis else 0)
        + 0.15 * (1 if qc_basis else 0)
        + 0.15 * (1 if logistics_basis else 0)
        + 0.15 * (1 if can_accept else 0),
        2,
    )
    confidence_score = round(
        max(0.0, completeness_score - len(all_risk_flags) * 0.05),
        2,
    )

    qty_str = f"{quantity} pcs" if quantity else "the requested quantity"
    fabric_supplier = material_basis.get("supplier", "confirmed supplier")
    trim_supplier = trim_basis.get("supplier", "confirmed supplier")
    fabric_lead_str = material_basis.get("lead_time", "TBC")
    fabric_price_str = material_basis.get("price", "TBC")

    response_en = (
        f"We can support the {qty_str} order for {product_summary} "
        f"based on approved upstream options.\n\n"
        f"Fabric: {fabric_supplier} — {fabric_price_str}, dispatch in {fabric_lead_str}.\n"
        f"Trims: {trim_supplier or 'confirmed'}.\n"
        f"Packaging: {'confirmed' if packaging_basis else 'standard packaging'}.\n"
        f"QC: {'pre-shipment inspection confirmed' if qc_basis else 'standard QC'}.\n"
        f"Logistics: {logistics_basis.get('lead_time', 'TBC')}.\n\n"
        f"Estimated total lead time: {lead_summary}.\n"
    )
    if all_risk_flags:
        response_en += f"\nKey risks requiring buyer confirmation:\n"
        for flag in all_risk_flags:
            response_en += f"  - {flag}\n"
    if not can_accept:
        response_en += f"\nNote: Some dependencies remain unresolved: {', '.join(unresolved)}.\n"
    response_en += "\nWe recommend confirming color and fabric option before final order acknowledgement."

    response_zh = (
        f"我们可以支持{qty_str}的订单（{product_summary}），基于以下已审批的上游选项：\n\n"
        f"面料：{fabric_supplier} — {fabric_price_str}，发货周期：{fabric_lead_str}。\n"
        f"辅料：{trim_supplier or '已确认'}。\n"
        f"包装：{'已确认' if packaging_basis else '标准包装'}。\n"
        f"质检：{'出货前检验已确认' if qc_basis else '标准质检'}。\n"
        f"物流：{logistics_basis.get('lead_time', '待确认')}。\n\n"
        f"预计总交货周期：{lead_summary}。\n"
    )
    if all_risk_flags:
        response_zh += "\n需买家确认的主要风险：\n"
        for flag in all_risk_flags:
            response_zh += f"  - {flag}\n"
    response_zh += "\n建议在正式确认订单前先确认颜色和面料选项。"

    # Build buyer-facing response; if CAD-CNC evidence available, prepend capability basis
    if cad_cnc_match_id and cnc_parameter_match_summary:
        match_score = cnc_parameter_match_summary.get("machine_fit_score", 0)
        in_house = cnc_parameter_match_summary.get("can_make_in_house", can_make_in_house)
        cap_line_en = (
            f"CAD-to-CNC matching basis: machine fit score {match_score:.0%}, "
            f"{'can produce in-house' if in_house else 'requires upstream/subcontract support'}. "
        )
        cap_line_zh = (
            f"CAD与CNC能力匹配依据：机器匹配度{match_score:.0%}，"
            f"{'可内部生产' if in_house else '需要外协/外购支持'}。"
        )
        response_en = cap_line_en + response_en
        response_zh = cap_line_zh + response_zh

    rollup_id = f"ROLLUP-{uuid.uuid4().hex[:10].upper()}"

    # Calculate lead time via the standalone GLTG API
    from src.integrations.gltg_leadtime import estimate_lead_time_path
    from src.lead_time.models import ProductionCapacity

    lt_fabric_days = lead_time_basis.get("fabric", {}).get("days")
    lt_trim_days = lead_time_basis.get("trim", {}).get("days") or lead_time_basis.get("raw_material", {}).get("days")
    lt_packaging_days = lead_time_basis.get("packaging", {}).get("days")
    lt_logistics_days = lead_time_basis.get("logistics", {}).get("days")
    lt_qc_days = lead_time_basis.get("qc_testing", {}).get("days")
    lt_subcontract_days = (
        lead_time_basis.get("subcontract_process", {}).get("days")
        or lead_time_basis.get("surface_treatment", {}).get("days")
        or lead_time_basis.get("heat_treatment", {}).get("days")
        or lead_time_basis.get("component", {}).get("days")
    )

    cap = ProductionCapacity(
        actor_id=main_supplier_actor_id,
        daily_capacity_units=max(1, (quantity or 100) // 2),
        setup_days=1.0,
        queue_days=0.0,
        confidence_score=0.7 if main_capacity_available else 0.3,
    )

    lt_path = estimate_lead_time_path(
        supplier_response_id=f"ROLLUP-{rollup_id}",
        supplier_id=main_supplier_actor_id,
        supplier_name=main_capacity_note,
        project_id=project_id,
        quantity=quantity,
        fabric_days=lt_fabric_days,
        trim_days=lt_trim_days,
        packaging_material_days=None,
        subcontract_days=lt_subcontract_days,
        qc_days=lt_qc_days,
        packaging_days=lt_packaging_days,
        logistics_days=lt_logistics_days,
        production_capacity=cap,
        risk_flags=all_risk_flags,
        confidence_score=confidence_score,
        completeness_score=completeness_score,
    )

    # Extract QC-only duration from the QC component (not post_production_days which is qc+pkg+lgs)
    _qc_comp_days = next(
        (int(c.duration_days) for c in lt_path.components if c.component_type == "qc"), None
    )
    _qc_days_estimate = lt_qc_days if lt_qc_days is not None else _qc_comp_days

    rollup = SupplierResponseRollup(
        rollup_id=rollup_id,
        project_id=project_id,
        main_supplier_actor_id=main_supplier_actor_id,
        can_accept_order=can_accept,
        main_capacity_summary=main_capacity_note,
        approved_upstream_options=approved_options,
        material_basis=material_basis,
        trim_basis=trim_basis,
        subcontract_basis=subcontract_basis,
        qc_basis=qc_basis,
        packaging_basis=packaging_basis,
        logistics_basis=logistics_basis,
        price_basis=price_basis,
        lead_time_basis=lead_time_basis,
        unresolved_dependencies=unresolved,
        risk_flags=all_risk_flags,
        completeness_score=completeness_score,
        confidence_score=confidence_score,
        recommended_response_to_buyer_en=response_en,
        recommended_response_to_buyer_zh=response_zh,
        cad_requirement_packet_id=cad_requirement_packet_id,
        cad_cnc_match_id=cad_cnc_match_id,
        capability_fit_report_id=capability_fit_report_id,
        cnc_parameter_match_summary=cnc_parameter_match_summary or {},
        can_make_in_house=can_make_in_house,
        recommended_machine_ids=recommended_machine_ids or [],
        capability_gaps=capability_gaps or [],
        upstream_dependency_basis=upstream_dependency_basis or {},
        # Lead time path model results
        calculated_total_lead_time_days=lt_path.total_lead_time_days,
        lead_time_components=[c.model_dump() for c in lt_path.components],
        lead_time_evidence_refs=lt_path.evidence_refs,
        lead_time_risk_flags=lt_path.risk_flags,
        material_ready_days=int(lt_path.material_ready_days),
        production_days=int(lt_path.production_days),
        qc_days_estimate=_qc_days_estimate,
        packaging_days_estimate=lt_packaging_days,
        logistics_days_estimate=lt_logistics_days,
        risk_buffer_days=int(lt_path.risk_buffer_days),
        supplier_stated_total_lead_time_days=None,
    )

    log_m_event(
        event_type="SUPPLIER_RESPONSE_ROLLUP_GENERATED",
        b_workspace_id=project_id,
        supplier_id=main_supplier_actor_id,
        payload={
            "rollup_id": rollup.rollup_id,
            "can_accept_order": can_accept,
            "approved_option_count": len(approved_options),
            "unresolved_count": len(unresolved),
            "completeness_score": completeness_score,
            "confidence_score": confidence_score,
        },
    )

    return rollup
