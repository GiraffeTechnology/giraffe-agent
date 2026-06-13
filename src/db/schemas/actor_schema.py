from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


class ActorBase(BaseModel):
    name: str
    actor_type: str
    default_language: str | None = None
    contact_channels_json: dict[str, Any] = Field(default_factory=dict)
    capabilities_json: dict[str, Any] = Field(default_factory=dict)
    profile_json: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True


class ActorCreate(ActorBase):
    pass


class ActorRead(ActorBase):
    actor_id: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
