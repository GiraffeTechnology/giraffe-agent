from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


class ProjectBase(BaseModel):
    original_buyer_actor_id: str
    main_supplier_actor_id: str | None = None
    category: str | None = None
    product_summary: str | None = None
    quantity: int | None = None
    status: str = "CREATED"
    product_tier: str = "free"
    created_by_channel: str | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class ProjectCreate(ProjectBase):
    pass


class ProjectRead(ProjectBase):
    project_id: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProjectStatusUpdate(BaseModel):
    status: str
