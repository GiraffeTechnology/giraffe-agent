from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


class CADRequirementPacketBase(BaseModel):
    project_id: str
    original_buyer_actor_id: str
    main_supplier_actor_id: str | None = None
    file_refs_json: dict[str, Any] = Field(default_factory=dict)
    source_types_json: dict[str, Any] = Field(default_factory=dict)
    part_summary: str | None = None
    material: str | None = None
    quantity: int | None = None
    dimensions_json: dict[str, Any] = Field(default_factory=dict)
    tolerance_requirements_json: dict[str, Any] = Field(default_factory=dict)
    surface_finish_requirements_json: dict[str, Any] = Field(default_factory=dict)
    thread_requirements_json: dict[str, Any] = Field(default_factory=dict)
    heat_treatment_requirements_json: dict[str, Any] = Field(default_factory=dict)
    operation_requirements_json: dict[str, Any] = Field(default_factory=dict)
    qc_requirements_json: dict[str, Any] = Field(default_factory=dict)
    packaging_requirements_json: dict[str, Any] = Field(default_factory=dict)
    delivery_deadline: str | None = None
    missing_information_json: dict[str, Any] = Field(default_factory=dict)
    extraction_confidence_score: float = 0.0


class CADRequirementPacketCreate(CADRequirementPacketBase):
    pass


class CADRequirementPacketRead(CADRequirementPacketBase):
    packet_id: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ShopCapabilityProfileBase(BaseModel):
    actor_id: str
    profile_name: str | None = None
    machines_json: dict[str, Any] = Field(default_factory=dict)
    tooling_inventory_json: dict[str, Any] = Field(default_factory=dict)
    qc_equipment_json: dict[str, Any] = Field(default_factory=dict)
    material_inventory_json: dict[str, Any] = Field(default_factory=dict)
    in_house_processes_json: dict[str, Any] = Field(default_factory=dict)
    outsourced_processes_json: dict[str, Any] = Field(default_factory=dict)
    schedule_summary_json: dict[str, Any] = Field(default_factory=dict)


class ShopCapabilityProfileCreate(ShopCapabilityProfileBase):
    pass


class ShopCapabilityProfileRead(ShopCapabilityProfileBase):
    profile_id: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CADCNCMatchResultBase(BaseModel):
    project_id: str
    actor_id: str
    cad_requirement_packet_id: str
    shop_capability_profile_id: str
    can_make_in_house: bool = False
    recommended_machine_ids_json: dict[str, Any] = Field(default_factory=dict)
    machine_fit_score: float = 0.0
    work_envelope_fit: str = "unknown"
    material_fit: str = "unknown"
    tolerance_fit: str = "unknown"
    surface_finish_fit: str = "unknown"
    tooling_fit: str = "unknown"
    qc_fit: str = "unknown"
    schedule_fit: str = "unknown"
    required_upstream_dependencies_json: dict[str, Any] = Field(default_factory=dict)
    required_subcontract_dependencies_json: dict[str, Any] = Field(default_factory=dict)
    risk_flags_json: dict[str, Any] = Field(default_factory=dict)
    missing_information_json: dict[str, Any] = Field(default_factory=dict)
    confidence_score: float = 0.0
    explanation: str | None = None


class CADCNCMatchResultCreate(CADCNCMatchResultBase):
    pass


class CADCNCMatchResultRead(CADCNCMatchResultBase):
    match_id: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CapabilityFitReportBase(BaseModel):
    project_id: str
    actor_id: str
    cad_cnc_match_id: str
    buyer_facing_summary_en: str | None = None
    buyer_facing_summary_zh: str | None = None
    internal_summary: str | None = None
    can_quote_now: bool = False
    can_make_in_house: bool = False
    recommended_next_actions_json: dict[str, Any] = Field(default_factory=dict)
    required_upstream_inquiries_json: dict[str, Any] = Field(default_factory=dict)
    required_subcontractor_inquiries_json: dict[str, Any] = Field(default_factory=dict)
    risk_flags_json: dict[str, Any] = Field(default_factory=dict)
    confidence_score: float = 0.0


class CapabilityFitReportCreate(CapabilityFitReportBase):
    pass


class CapabilityFitReportRead(CapabilityFitReportBase):
    report_id: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
