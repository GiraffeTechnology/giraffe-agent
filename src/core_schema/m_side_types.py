"""
M-side core Pydantic v2 models for Giraffe Agent AI Merchandiser / Supplier Response Agent.
"""

from __future__ import annotations
from datetime import datetime, timezone
from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class SupplierCapability(BaseModel):
    categories: list[str] = Field(default_factory=list)
    materials: list[str] = Field(default_factory=list)
    processes: list[str] = Field(default_factory=list)
    max_quantity_hint: int | None = None
    typical_lead_time_days: int | None = None
    machines_or_lines: list[str] = Field(default_factory=list)
    qc_capabilities: list[str] = Field(default_factory=list)
    export_experience: list[str] = Field(default_factory=list)
    notes: str | None = None


class MSideSupplierProfile(BaseModel):
    supplier_id: str
    supplier_name: str
    contact_name: str | None = None
    channel: str | None = None
    external_user_id: str | None = None
    phone_or_handle: str | None = None
    language_preference: str = "zh"
    region: str | None = None
    capability: SupplierCapability = Field(default_factory=SupplierCapability)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class SupplierInquiryContext(BaseModel):
    m_workspace_id: str
    b_workspace_id: str
    rfq_id: str
    inquiry_id: str
    supplier_id: str
    supplier_name: str
    invitation_token: str
    inquiry_text_zh: str
    inquiry_text_en: str
    required_response_fields: list[str] = Field(default_factory=list)
    nda_required: bool = False
    cap_level: int = 0
    attachments: list[dict] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_utcnow)


class CapacitySignal(BaseModel):
    can_make: bool | None = None
    capacity_available: bool | None = None
    capacity_notes: str | None = None
    earliest_start_date: str | None = None
    production_days: int | None = None
    monthly_capacity_hint: int | None = None
    bottlenecks: list[str] = Field(default_factory=list)


class ScheduleSignal(BaseModel):
    estimated_lead_time_days: int | None = None
    sample_lead_time_days: int | None = None
    mass_production_lead_time_days: int | None = None
    delivery_date_commitment: str | None = None
    schedule_risks: list[str] = Field(default_factory=list)


class MaterialAvailability(BaseModel):
    material_available: bool | None = None
    material_notes: str | None = None
    substitute_materials: list[str] = Field(default_factory=list)
    procurement_days: int | None = None
    moq_constraints: str | None = None


class SupplierQuote(BaseModel):
    currency: str | None = None
    unit_price: float | None = None
    total_price: float | None = None
    tooling_fee: float | None = None
    sample_fee: float | None = None
    packaging_fee: float | None = None
    logistics_fee_estimate: float | None = None
    tax_or_export_notes: str | None = None
    price_valid_until: str | None = None
    quote_notes: str | None = None


class QCCommitment(BaseModel):
    qc_available: bool | None = None
    qc_method: str | None = None
    inspection_standard: str | None = None
    photo_or_video_update_supported: bool = True
    required_buyer_confirmation_points: list[str] = Field(default_factory=list)


class LogisticsCommitment(BaseModel):
    exw_supported: bool | None = None
    fob_supported: bool | None = None
    ddp_supported: bool | None = None
    destination_supported: bool | None = None
    logistics_notes: str | None = None


class SupplierResponsePacket(BaseModel):
    response_id: str
    m_workspace_id: str
    b_workspace_id: str
    rfq_id: str
    inquiry_id: str
    supplier_id: str
    supplier_name: str
    submitted_at: datetime = Field(default_factory=_utcnow)
    raw_supplier_messages: list[str] = Field(default_factory=list)
    capacity_signal: CapacitySignal = Field(default_factory=CapacitySignal)
    schedule_signal: ScheduleSignal = Field(default_factory=ScheduleSignal)
    material_availability: MaterialAvailability = Field(default_factory=MaterialAvailability)
    quote: SupplierQuote = Field(default_factory=SupplierQuote)
    qc_commitment: QCCommitment = Field(default_factory=QCCommitment)
    logistics_commitment: LogisticsCommitment = Field(default_factory=LogisticsCommitment)
    red_flags: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    completeness_score: float = 0.0
    confidence_score: float = 0.0
    supplier_summary_for_buyer: str = ""


class ProductionMilestone(BaseModel):
    milestone_id: str
    name: str
    expected_date: str | None = None
    status: str = "pending"  # pending | in_progress | completed | delayed | blocked
    evidence_required: bool = False
    notes: str | None = None


class OrderExecutionContext(BaseModel):
    order_execution_id: str
    b_workspace_id: str
    m_workspace_id: str
    supplier_id: str
    selected_path_id: str | None = None
    status: str = "order_acknowledgement_pending"
    milestones: list[ProductionMilestone] = Field(default_factory=list)
    merchandiser_plan_id: str | None = None
    merchandiser_task_ids: list[str] = Field(default_factory=list)
    merchandiser_milestone_ids: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class ProductionUpdate(BaseModel):
    update_id: str
    order_execution_id: str
    supplier_id: str
    milestone_id: str | None = None
    status: str = "in_progress"
    message: str
    attachments: list[dict] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_utcnow)


class QCUpdate(BaseModel):
    qc_update_id: str
    order_execution_id: str
    supplier_id: str
    qc_status: str = "pending"  # pending | passed | failed | needs_buyer_confirmation
    message: str
    attachments: list[dict] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_utcnow)


class LogisticsUpdate(BaseModel):
    logistics_update_id: str
    order_execution_id: str
    supplier_id: str
    status: str = "pending"  # pending | ready_for_pickup | handed_over | shipped | delivered
    tracking_number: str | None = None
    carrier: str | None = None
    message: str | None = None
    created_at: datetime = Field(default_factory=_utcnow)


class ExceptionReport(BaseModel):
    exception_id: str
    order_execution_id: str | None = None
    m_workspace_id: str
    supplier_id: str
    severity: str = "medium"  # low | medium | high | blocking
    category: str = "other"  # material | schedule | quality | logistics | cost | other
    message: str
    proposed_options: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_utcnow)


class MSideWorkspace(BaseModel):
    m_workspace_id: str
    b_workspace_id: str
    rfq_id: str
    inquiry_id: str
    supplier_id: str
    supplier_name: str
    status: str = "inquiry_received"
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
    channel_id: str | None = None
    external_user_id: str | None = None
    invitation_token: str | None = None
    inquiry_context: SupplierInquiryContext | None = None
    pending_questions: list[dict] = Field(default_factory=list)
    raw_supplier_messages: list[str] = Field(default_factory=list)
    response_packet: SupplierResponsePacket | None = None
    order_execution: OrderExecutionContext | None = None
    production_updates: list[ProductionUpdate] = Field(default_factory=list)
    qc_updates: list[QCUpdate] = Field(default_factory=list)
    logistics_updates: list[LogisticsUpdate] = Field(default_factory=list)
    exception_reports: list[ExceptionReport] = Field(default_factory=list)
