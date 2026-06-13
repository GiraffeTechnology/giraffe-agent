from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


class StructuredRequirementBase(BaseModel):
    project_id: str
    source_actor_id: str
    source_message_id: str | None = None
    raw_input_refs_json: dict[str, Any] = Field(default_factory=dict)
    category: str | None = None
    quantity: int | None = None
    material: str | None = None
    specs_json: dict[str, Any] = Field(default_factory=dict)
    deadline: str | None = None
    destination: str | None = None
    missing_fields_json: dict[str, Any] = Field(default_factory=dict)
    confidence_score: float = 0.0


class StructuredRequirementCreate(StructuredRequirementBase):
    pass


class StructuredRequirementRead(StructuredRequirementBase):
    requirement_id: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
