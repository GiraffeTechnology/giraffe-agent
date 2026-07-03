"""
RoleContext — describes the contextual role of an actor within a project edge.
The same actor can hold multiple roles in one project.
"""
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel


class RoleContext(BaseModel):
    project_id: str
    actor_id: str
    counterparty_actor_id: str | None = None
    edge_id: str | None = None
    role: Literal[
        "ORIGINAL_BUYER",
        "MAIN_M_SIDE",
        "UPSTREAM_B_SIDE",
        "UPSTREAM_M_SIDE",
        "QC_SIDE",
        "LOGISTICS_SIDE",
        "UNKNOWN",
    ]
    role_reason: str
    can_create_upstream_inquiry: bool = False
    can_approve_upstream_option: bool = False
    can_submit_response_to_buyer: bool = False
