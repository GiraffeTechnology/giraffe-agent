import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class ParticipantMatchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    participant_id: uuid.UUID
    participant_name: str
    recommended_role: str
    match_score: float
    score_breakdown: Optional[dict]
    matched_requirements: Optional[list]
    unmatched_requirements: Optional[list]
    risk_flags: Optional[list]
    missing_participant_data: Optional[list]
    recommendation_reason: Optional[str]
    requires_human_approval: bool
    created_at: datetime
