from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


class ProcurementEdgeBase(BaseModel):
    project_id: str
    from_actor_id: str
    to_actor_id: str
    edge_type: str
    parent_edge_id: str | None = None
    inquiry_id: str | None = None
    response_id: str | None = None
    status: str = "DRAFT"
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class ProcurementEdgeCreate(ProcurementEdgeBase):
    pass


class ProcurementEdgeRead(ProcurementEdgeBase):
    edge_id: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RoleContextBase(BaseModel):
    project_id: str
    edge_id: str | None = None
    actor_id: str
    counterparty_actor_id: str | None = None
    role: str
    role_reason: str
    permissions_json: dict[str, Any] = Field(default_factory=dict)
    can_create_upstream_inquiry: bool = False
    can_approve_upstream_option: bool = False
    can_submit_response_to_buyer: bool = False
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class RoleContextCreate(RoleContextBase):
    pass


class RoleContextRead(RoleContextBase):
    role_context_id: str
    created_at: datetime

    model_config = {"from_attributes": True}
