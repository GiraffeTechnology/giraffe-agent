"""
CAD Requirement Packet — structured manufacturing requirement from buyer CAD/STEP/BOM input.
"""

from __future__ import annotations
import uuid
from typing import Literal
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from src.m_side.m_event_logger import log_m_event


class CADRequirementPacket(BaseModel):
    packet_id: str
    project_id: str
    original_buyer_actor_id: str
    main_supplier_actor_id: str
    file_refs: list[str] = Field(default_factory=list)
    source_types: list[Literal["cad", "step", "pdf", "bom", "image", "manual"]] = Field(default_factory=list)
    part_summary: str | None = None
    material: str | None = None
    quantity: int | None = None
    dimensions: dict = Field(default_factory=dict)
    tolerance_requirements: dict = Field(default_factory=dict)
    surface_finish_requirements: dict = Field(default_factory=dict)
    thread_requirements: dict = Field(default_factory=dict)
    heat_treatment_requirements: dict = Field(default_factory=dict)
    operation_requirements: list[str] = Field(default_factory=list)
    qc_requirements: dict = Field(default_factory=dict)
    packaging_requirements: dict = Field(default_factory=dict)
    delivery_deadline: str | None = None
    missing_information: list[str] = Field(default_factory=list)
    extraction_confidence_score: float = 0.0
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def create_cad_requirement_packet(
    project_id: str,
    original_buyer_actor_id: str,
    main_supplier_actor_id: str,
    buyer_input: dict,
) -> CADRequirementPacket:
    """
    Create a CAD Requirement Packet from buyer input (fixture metadata or manual entry).
    Uses rule-based extraction. Does not require real CAD parser.
    """
    # Extract fields from buyer_input
    source_types_raw = buyer_input.get("source_types", ["manual"])
    # Validate source_types
    valid_source_types: list[Literal["cad", "step", "pdf", "bom", "image", "manual"]] = []
    allowed = {"cad", "step", "pdf", "bom", "image", "manual"}
    for st in source_types_raw:
        if st in allowed:
            valid_source_types.append(st)  # type: ignore[arg-type]

    missing: list[str] = []
    if not buyer_input.get("material"):
        missing.append("material")
    if not buyer_input.get("dimensions"):
        missing.append("dimensions")
    if not buyer_input.get("tolerance_requirements"):
        missing.append("tolerance_requirements")

    # Confidence based on completeness
    total_fields = 7
    present = sum([
        bool(buyer_input.get("material")),
        bool(buyer_input.get("dimensions")),
        bool(buyer_input.get("tolerance_requirements")),
        bool(buyer_input.get("surface_finish_requirements")),
        bool(buyer_input.get("operation_requirements")),
        bool(buyer_input.get("qc_requirements")),
        bool(buyer_input.get("delivery_deadline")),
    ])
    confidence = round(present / total_fields, 2)

    packet = CADRequirementPacket(
        packet_id=f"CAD-PKT-{uuid.uuid4().hex[:10].upper()}",
        project_id=project_id,
        original_buyer_actor_id=original_buyer_actor_id,
        main_supplier_actor_id=main_supplier_actor_id,
        file_refs=buyer_input.get("file_refs", []),
        source_types=valid_source_types,
        part_summary=buyer_input.get("part_summary"),
        material=buyer_input.get("material"),
        quantity=buyer_input.get("quantity"),
        dimensions=buyer_input.get("dimensions", {}),
        tolerance_requirements=buyer_input.get("tolerance_requirements", {}),
        surface_finish_requirements=buyer_input.get("surface_finish_requirements", {}),
        thread_requirements=buyer_input.get("thread_requirements", {}),
        heat_treatment_requirements=buyer_input.get("heat_treatment_requirements", {}),
        operation_requirements=buyer_input.get("operation_requirements", []),
        qc_requirements=buyer_input.get("qc_requirements", {}),
        packaging_requirements=buyer_input.get("packaging_requirements", {}),
        delivery_deadline=buyer_input.get("delivery_deadline"),
        missing_information=missing,
        extraction_confidence_score=confidence,
    )

    log_m_event(
        event_type="CAD_REQUIREMENT_PACKET_CREATED",
        b_workspace_id=project_id,
        supplier_id=main_supplier_actor_id,
        payload={
            "packet_id": packet.packet_id,
            "source_types": valid_source_types,
            "material": packet.material,
            "extraction_confidence_score": confidence,
            "missing_information": missing,
        },
    )

    return packet
