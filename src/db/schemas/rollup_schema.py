from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


class SupplierResponseRollupBase(BaseModel):
    project_id: str
    main_supplier_actor_id: str
    can_accept_order: bool | None = None
    main_capacity_summary: str | None = None
    approved_upstream_options_json: dict[str, Any] = Field(default_factory=dict)
    material_basis_json: dict[str, Any] = Field(default_factory=dict)
    trim_basis_json: dict[str, Any] = Field(default_factory=dict)
    subcontract_basis_json: dict[str, Any] = Field(default_factory=dict)
    qc_basis_json: dict[str, Any] = Field(default_factory=dict)
    packaging_basis_json: dict[str, Any] = Field(default_factory=dict)
    logistics_basis_json: dict[str, Any] = Field(default_factory=dict)
    price_basis_json: dict[str, Any] = Field(default_factory=dict)
    lead_time_basis_json: dict[str, Any] = Field(default_factory=dict)
    unresolved_dependencies_json: dict[str, Any] = Field(default_factory=dict)
    risk_flags_json: dict[str, Any] = Field(default_factory=dict)
    completeness_score: float = 0.0
    confidence_score: float = 0.0
    recommended_response_to_buyer_en: str | None = None
    recommended_response_to_buyer_zh: str | None = None
    cad_requirement_packet_id: str | None = None
    cad_cnc_match_id: str | None = None
    capability_fit_report_id: str | None = None
    cnc_parameter_match_summary_json: dict[str, Any] = Field(default_factory=dict)
    can_make_in_house: bool | None = None
    recommended_machine_ids_json: dict[str, Any] = Field(default_factory=dict)
    capability_gaps_json: dict[str, Any] = Field(default_factory=dict)
    upstream_dependency_basis_json: dict[str, Any] = Field(default_factory=dict)


class SupplierResponseRollupCreate(SupplierResponseRollupBase):
    pass


class SupplierResponseRollupRead(SupplierResponseRollupBase):
    rollup_id: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
