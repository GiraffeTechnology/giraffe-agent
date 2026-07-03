"""
Procurement project and edge models — the spine of the execution graph.
"""
from __future__ import annotations
from typing import Literal
from datetime import datetime, timezone
from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ProcurementProject(BaseModel):
    project_id: str
    original_buyer_actor_id: str
    main_supplier_actor_id: str | None = None
    b_workspace_id: str | None = None
    product_summary: str
    category: str
    quantity: int | None = None
    status: Literal[
        "CREATED",
        "MAIN_SUPPLIER_RECEIVED",
        "UPSTREAM_DEPENDENCY_PLANNED",
        "UPSTREAM_INQUIRIES_SENT",
        "UPSTREAM_RESPONSES_RECEIVED",
        "UPSTREAM_OPTIONS_READY",
        "UPSTREAM_OPTION_APPROVED",
        "SUPPLIER_RESPONSE_ROLLED_UP",
        "SUPPLIER_RESPONSE_SUBMITTED_TO_BUYER",
        "ORDER_CONFIRMED",
        "IN_EXECUTION",
        "CLOSED",
    ] = "CREATED"
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
    metadata: dict = Field(default_factory=dict)


class ProcurementEdge(BaseModel):
    edge_id: str
    project_id: str
    from_actor_id: str
    to_actor_id: str
    edge_type: Literal[
        "BUYER_TO_MAIN_SUPPLIER",
        "MAIN_SUPPLIER_TO_MATERIAL_SUPPLIER",
        "MAIN_SUPPLIER_TO_FABRIC_SUPPLIER",
        "MAIN_SUPPLIER_TO_TRIM_SUPPLIER",
        "MAIN_SUPPLIER_TO_COMPONENT_SUPPLIER",
        "MAIN_SUPPLIER_TO_SUBCONTRACTOR",
        "MAIN_SUPPLIER_TO_PACKAGING_SUPPLIER",
        "MAIN_SUPPLIER_TO_QC_PROVIDER",
        "MAIN_SUPPLIER_TO_LOGISTICS_PROVIDER",
    ]
    parent_edge_id: str | None = None
    inquiry_id: str | None = None
    response_id: str | None = None
    status: Literal[
        "DRAFT", "SENT", "RESPONDED", "OPTIONS_READY", "APPROVED", "ROLLED_UP"
    ] = "DRAFT"
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
