"""
Embedded MachinaCheck-like Feature Extractor.
Converts CADRequirementPacket into ManufacturingFeatureSet using deterministic heuristics.
No external API or real CAD parser required.
"""

from __future__ import annotations
import uuid
from typing import Literal
from pydantic import BaseModel, Field

from src.m_side.professional_free.cad_requirement_packet import CADRequirementPacket
from src.m_side.m_event_logger import log_m_event


class ManufacturingFeatureSet(BaseModel):
    feature_set_id: str
    packet_id: str
    required_processes: list[str] = Field(default_factory=list)
    required_machine_types: list[str] = Field(default_factory=list)
    min_axis_requirement: int | None = None
    work_envelope_required: dict = Field(default_factory=dict)
    material_required: str | None = None
    tolerance_class: Literal["standard", "medium", "tight", "unknown"] = "unknown"
    surface_finish_class: Literal["standard", "fine", "mirror", "unknown"] = "unknown"
    thread_or_hole_features: list[dict] = Field(default_factory=list)
    heat_treatment_required: bool = False
    external_process_likely_required: bool = False
    qc_required: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)


def _classify_tolerance(tolerance_req: dict) -> Literal["standard", "medium", "tight", "unknown"]:
    tol_mm = tolerance_req.get("general_mm") or tolerance_req.get("tolerance_mm")
    if tol_mm is None:
        tol_str = str(tolerance_req.get("tolerance", "")).strip("±").strip()
        try:
            tol_mm = float(tol_str)
        except (ValueError, AttributeError):
            return "unknown"
    tol_mm = float(tol_mm)
    if tol_mm >= 0.1:
        return "standard"
    elif tol_mm >= 0.05:
        return "medium"
    else:
        return "tight"


def _classify_surface_finish(sf_req: dict) -> Literal["standard", "fine", "mirror", "unknown"]:
    ra = sf_req.get("ra_um") or sf_req.get("roughness_ra")
    if ra is None:
        sf_text = str(sf_req.get("finish", "")).lower()
        if "mirror" in sf_text:
            return "mirror"
        if "fine" in sf_text or "polished" in sf_text:
            return "fine"
        if "standard" in sf_text or "machined" in sf_text:
            return "standard"
        return "unknown"
    ra = float(ra)
    if ra <= 0.4:
        return "mirror"
    elif ra <= 1.6:
        return "fine"
    else:
        return "standard"


def _requires_5axis(ops: list[str]) -> bool:
    five_axis_keywords = {"5-axis", "5axis", "5_axis", "5 axis", "complex_contour", "simultaneous_5"}
    return any(any(kw in op.lower() for kw in five_axis_keywords) for op in ops)


def _requires_heat_treatment(ht_req: dict, ops: list[str]) -> bool:
    if ht_req:
        required = ht_req.get("required", False)
        if required:
            return True
        if ht_req.get("type"):
            return True
    ht_keywords = {"heat_treat", "anneal", "harden", "temper", "quench", "nitriding", "carburizing"}
    return any(any(kw in op.lower() for kw in ht_keywords) for op in ops)


def extract_manufacturing_features(packet: CADRequirementPacket) -> ManufacturingFeatureSet:
    """
    Extract manufacturing features from a CAD Requirement Packet using deterministic heuristics.
    """
    ops = packet.operation_requirements or []
    dims = packet.dimensions or {}
    tol_req = packet.tolerance_requirements or {}
    sf_req = packet.surface_finish_requirements or {}
    ht_req = packet.heat_treatment_requirements or {}
    qc_req = packet.qc_requirements or {}
    thread_req = packet.thread_requirements or {}

    processes: list[str] = []
    machine_types: list[str] = []
    risk_flags: list[str] = []
    qc_required: list[str] = []
    missing: list[str] = list(packet.missing_information)

    # Derive processes from operation_requirements
    op_lower_set = {op.lower() for op in ops}
    if any(k in op for op in op_lower_set for k in ("mill", "milling", "face", "pocket", "contour")):
        processes.append("cnc_milling")
        machine_types.append("cnc_milling")
    if any(k in op for op in op_lower_set for k in ("turn", "turning", "lathe")):
        processes.append("cnc_turning")
        machine_types.append("cnc_turning")
    if any(k in op for op in op_lower_set for k in ("grind", "grinding")):
        processes.append("grinding")
        machine_types.append("grinding")
    if any(k in op for op in op_lower_set for k in ("edm", "wire_edm", "spark_erosion")):
        processes.append("edm")
        machine_types.append("edm")
    if not processes:
        # Default: infer from material and part summary
        processes.append("cnc_milling")
        machine_types.append("cnc_milling")

    # Axis requirement
    needs_5axis = _requires_5axis(ops)
    min_axis = 5 if needs_5axis else 3

    if needs_5axis:
        machine_types.append("5_axis_machining_center")
        risk_flags.append("5_axis_required")

    # Work envelope
    work_envelope: dict = {}
    if dims:
        length = dims.get("length_mm") or dims.get("x_mm") or dims.get("length")
        width = dims.get("width_mm") or dims.get("y_mm") or dims.get("width")
        height = dims.get("height_mm") or dims.get("z_mm") or dims.get("height")
        if length:
            work_envelope["length_mm"] = float(length)
        if width:
            work_envelope["width_mm"] = float(width)
        if height:
            work_envelope["height_mm"] = float(height)

    # Tolerance
    tol_class = _classify_tolerance(tol_req)
    if tol_class == "tight":
        risk_flags.append("tight_tolerance_requires_qc_validation")
        qc_required.append("cmm_inspection")
        processes.append("precision_finishing")

    # Surface finish
    sf_class = _classify_surface_finish(sf_req)
    external_process = False
    if sf_class == "mirror":
        external_process = True
        processes.append("surface_polishing")
        risk_flags.append("mirror_finish_may_require_external_polishing")
    elif sf_class == "fine":
        processes.append("fine_finishing")

    # Heat treatment
    ht_required = _requires_heat_treatment(ht_req, ops)
    if ht_required:
        external_process = True
        processes.append("heat_treatment")
        risk_flags.append("heat_treatment_required_check_outsource")

    # Thread / hole features
    thread_features: list[dict] = []
    if thread_req:
        thread_features.append({
            "type": thread_req.get("type", "thread"),
            "size": thread_req.get("size"),
            "count": thread_req.get("count"),
        })

    # QC from requirements
    if qc_req:
        qc_types = qc_req.get("types", [])
        if isinstance(qc_types, list):
            qc_required.extend(qc_types)
        elif isinstance(qc_types, str):
            qc_required.append(qc_types)
        if qc_req.get("external_required"):
            risk_flags.append("external_qc_required")
            external_process = True

    # High tolerance class triggers CMM
    if tol_class in ("tight", "medium") and "cmm_inspection" not in qc_required:
        qc_required.append("dimensional_check")

    feature_set = ManufacturingFeatureSet(
        feature_set_id=f"FEAT-{uuid.uuid4().hex[:10].upper()}",
        packet_id=packet.packet_id,
        required_processes=list(dict.fromkeys(processes)),  # dedup preserving order
        required_machine_types=list(dict.fromkeys(machine_types)),
        min_axis_requirement=min_axis,
        work_envelope_required=work_envelope,
        material_required=packet.material,
        tolerance_class=tol_class,
        surface_finish_class=sf_class,
        thread_or_hole_features=thread_features,
        heat_treatment_required=ht_required,
        external_process_likely_required=external_process,
        qc_required=list(dict.fromkeys(qc_required)),
        risk_flags=risk_flags,
        missing_information=missing,
    )

    log_m_event(
        event_type="CAD_FEATURES_EXTRACTED",
        b_workspace_id=packet.project_id,
        supplier_id=packet.main_supplier_actor_id,
        payload={
            "feature_set_id": feature_set.feature_set_id,
            "packet_id": packet.packet_id,
            "tolerance_class": tol_class,
            "min_axis_requirement": min_axis,
            "heat_treatment_required": ht_required,
            "external_process_likely": external_process,
            "risk_flags": risk_flags,
        },
    )

    return feature_set
