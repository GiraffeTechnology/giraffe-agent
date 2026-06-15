import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class SupplierResponseCreate(BaseModel):
    participant_id: uuid.UUID
    raw_response_text: str


class SupplierResponseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    rfq_id: uuid.UUID
    participant_id: uuid.UUID
    raw_response_text: Optional[str]
    received_at: datetime


class SupplierResponsePacketOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    unit_price: Optional[float]
    currency: Optional[str]
    moq: Optional[int]
    total_lead_time_days: Optional[int]
    fabric_lead_time_days: Optional[int]
    production_time_days: Optional[int]
    missing_fields: Optional[list]
    risk_flags: Optional[list]
    ai_generated: bool
    human_confirmed: bool
    created_at: datetime
