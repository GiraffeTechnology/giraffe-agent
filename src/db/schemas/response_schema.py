from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


class SupplierResponseBase(BaseModel):
    project_id: str
    edge_id: str
    inquiry_id: str | None = None
    from_actor_id: str
    to_actor_id: str
    can_supply: bool | None = None
    price: float | None = None
    currency: str | None = None
    moq: float | None = None
    available_quantity: float | None = None
    lead_time_days: int | None = None
    earliest_dispatch_date: str | None = None
    capacity_basis_json: dict[str, Any] = Field(default_factory=dict)
    material_basis_json: dict[str, Any] = Field(default_factory=dict)
    subcontract_basis_json: dict[str, Any] = Field(default_factory=dict)
    qc_basis_json: dict[str, Any] = Field(default_factory=dict)
    logistics_basis_json: dict[str, Any] = Field(default_factory=dict)
    risk_flags_json: dict[str, Any] = Field(default_factory=dict)
    raw_message: str | None = None
    parsed_json: dict[str, Any] = Field(default_factory=dict)
    confidence_score: float = 0.0
    completeness_score: float = 0.0


class SupplierResponseCreate(SupplierResponseBase):
    pass


class SupplierResponseRead(SupplierResponseBase):
    response_id: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UpstreamResponseBase(BaseModel):
    project_id: str
    edge_id: str
    upstream_inquiry_id: str
    dependency_id: str
    from_actor_id: str
    can_supply: bool
    matched_specs_json: dict[str, Any] = Field(default_factory=dict)
    price: float | None = None
    currency: str | None = None
    moq: float | None = None
    available_quantity: float | None = None
    lead_time_days: int | None = None
    earliest_dispatch_date: str | None = None
    quality_notes: str | None = None
    substitute_options_json: dict[str, Any] = Field(default_factory=dict)
    risk_flags_json: dict[str, Any] = Field(default_factory=dict)
    confidence_score: float = 0.0
    completeness_score: float = 0.0
    raw_message: str | None = None


class UpstreamResponseCreate(UpstreamResponseBase):
    pass


class UpstreamResponseRead(UpstreamResponseBase):
    upstream_response_id: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UpstreamOptionBase(BaseModel):
    project_id: str
    dependency_id: str
    upstream_actor_id: str
    option_label: str
    price_summary: str | None = None
    lead_time_summary: str | None = None
    risk_summary: str | None = None
    score: float = 0.0
    reason: str | None = None
    response_ids_json: dict[str, Any] = Field(default_factory=dict)
    status: str = "pending"


class UpstreamOptionCreate(UpstreamOptionBase):
    pass


class UpstreamOptionRead(UpstreamOptionBase):
    option_id: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
