import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class DecisionOptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    option_index: int
    supplier_combination: Optional[dict]
    unit_price: Optional[float]
    total_price: Optional[float]
    currency: Optional[str]
    lead_time_breakdown: Optional[dict]
    calculated_total_lead_time_days: Optional[int]
    supplier_stated_lead_time_days: Optional[int]
    risk_flags: Optional[list]
    missing_fields: Optional[list]
    recommendation_reason: Optional[str]
    evidence: Optional[dict]


class DecisionPacketOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    generated_at: datetime
    options: list[DecisionOptionOut] = []
    recommended_option_id: Optional[uuid.UUID]
    comparison_summary: Optional[str]
    risk_summary: Optional[str]
    missing_field_summary: Optional[str]
    human_approval_status: str
    created_at: datetime


class ApproveOptionRequest(BaseModel):
    option_id: uuid.UUID
    approval_id: uuid.UUID
    review_notes: Optional[str] = ""
