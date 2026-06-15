"""
B-side core Pydantic v2 models for Giraffe Agent AI Buyer.
"""

from datetime import datetime, timezone
from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class BuyerRequirement(BaseModel):
    rfq_id: str
    b_workspace_id: str
    raw_text: str
    category: str | None = None
    quantity: int | None = None
    material: str | None = None
    specs_json: dict = Field(default_factory=dict)
    deadline: str | None = None
    destination: str | None = None
    missing_fields: list[str] = Field(default_factory=list)
    confidence_score: float = 0.0
    created_at: datetime = Field(default_factory=_utcnow)


class SupplierInquiryDraft(BaseModel):
    rfq_id: str
    b_workspace_id: str
    inquiry_id: str
    supplier_ids: list[str] = Field(default_factory=list)
    message_text_en: str = ""
    message_text_zh: str = ""
    required_fields: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_utcnow)


class SupplierResponseRecord(BaseModel):
    response_id: str
    rfq_id: str
    b_workspace_id: str
    supplier_id: str
    supplier_name: str
    can_make: bool | None = None
    capacity_available: bool | None = None
    material_available: bool | None = None
    estimated_lead_time_days: int | None = None  # kept for backward compat; treated as supplier_stated evidence only
    unit_price: float | None = None
    total_price: float | None = None
    currency: str | None = None
    qc_available: bool | None = None
    logistics_notes: str | None = None
    red_flags: list[str] = Field(default_factory=list)
    completeness_score: float = 0.0
    confidence_score: float = 0.0
    raw_response: str = ""
    submitted_at: datetime = Field(default_factory=_utcnow)
    # Lead time breakdown (populated by M-side rollup bridge)
    lead_time_breakdown: dict = Field(default_factory=dict)


class DeliveryPath(BaseModel):
    path_id: str
    rfq_id: str
    supplier_id: str
    supplier_name: str
    lead_time_days: int | None = None  # kept for compat (= calculated_lead_time_days)
    unit_price: float | None = None
    currency: str | None = None
    total_price: float | None = None
    risk_score: float = 0.0
    confidence_score: float = 0.0
    notes: str | None = None
    rank: int = 0
    # Lead time path model fields (new)
    calculated_lead_time_days: int | None = None
    supplier_stated_lead_time_days: int | None = None
    lead_time_components: list[dict] = Field(default_factory=list)
    critical_path_summary: str | None = None
    slack_days: int | None = None
    deadline_feasible: bool | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    lead_time_risk_flags: list[str] = Field(default_factory=list)
    label: str | None = None
    # GLTG provenance fields — AIVAN must expose these on all buyer-facing paths
    lead_time_model: str | None = None
    p50_lead_time_days: int | None = None
    p80_lead_time_days: int | None = None
    p90_lead_time_days: int | None = None
    feasibility_basis: str | None = None
    fallback_model_used: bool | None = None


class FeasibilityReport(BaseModel):
    rfq_id: str
    b_workspace_id: str
    paths: list[DeliveryPath] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=_utcnow)
    selected_path_id: str | None = None


class BWWorkspace(BaseModel):
    b_workspace_id: str
    rfq_id: str
    raw_requirement: str = ""
    buyer_requirement: BuyerRequirement | None = None
    supplier_inquiry_draft: SupplierInquiryDraft | None = None
    supplier_responses: list[SupplierResponseRecord] = Field(default_factory=list)
    feasibility_report: FeasibilityReport | None = None
    status: str = "created"
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
