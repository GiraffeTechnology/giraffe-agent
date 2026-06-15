import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    status: str
    order_number: Optional[str]
    approved_option_id: Optional[uuid.UUID]
    locked_form_version_id: Optional[uuid.UUID]
    buyer_participant_id: Optional[uuid.UUID]
    confirmed_at: Optional[datetime]
    buyer_signed_off_at: Optional[datetime]
    created_at: datetime


class CreateOrderRequest(BaseModel):
    packet_id: uuid.UUID
    option_id: uuid.UUID
    approval_id: uuid.UUID
