from typing import Optional
from pydantic import BaseModel, Field

class SupplierReply(BaseModel):
    project_id: str
    supplier_id: str = ""
    candidate_id: str = ""
    raw_text: str
    channel: str = ""
    unit_price: Optional[float] = None
    currency: str = "USD"
    moq: Optional[int] = None
    capacity_per_day: Optional[int] = None
    capacity_per_month: Optional[int] = None
    lead_time_days: Optional[int] = None
    material_availability: str = ""
    qc_commitment: str = ""
    logistics_note: str = ""
    incoterms: str = ""
    payment_terms: str = ""
    risks: list[str] = Field(default_factory=list)
    missing_info: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    raw_payload: dict = Field(default_factory=dict)
    received_at: str = ""
