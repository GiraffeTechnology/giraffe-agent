import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class RFQCreate(BaseModel):
    form_version_id: uuid.UUID
    recipient_participant_ids: list[uuid.UUID]


class RFQOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    status: str
    rfq_content: Optional[dict]
    ai_generated: bool
    human_approved_by: Optional[uuid.UUID]
    human_approved_at: Optional[datetime]
    sent_at: Optional[datetime]
    expires_at: Optional[datetime]
    created_at: datetime


class RFQSendRequest(BaseModel):
    approval_id: uuid.UUID
