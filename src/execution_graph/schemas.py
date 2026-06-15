import uuid
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, ConfigDict


class ExecutionEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    project_id: Optional[uuid.UUID] = None
    order_id: Optional[uuid.UUID] = None
    participant_id: Optional[uuid.UUID] = None
    event_type: str
    payload: dict
    triggered_by_user_id: Optional[uuid.UUID] = None
    occurred_at: datetime
