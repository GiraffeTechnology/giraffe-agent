import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class ApprovalRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    action_type: str
    resource_type: Optional[str]
    resource_id: Optional[uuid.UUID]
    proposed_payload: Optional[dict]
    affected_participant_id: Optional[uuid.UUID]
    evidence: Optional[dict]
    risk_flags: Optional[list]
    status: str
    reviewed_by: Optional[uuid.UUID]
    reviewed_at: Optional[datetime]
    review_notes: Optional[str]
    created_by: Optional[uuid.UUID]
    created_at: datetime


class ReviewRequest(BaseModel):
    review_notes: str = ""
