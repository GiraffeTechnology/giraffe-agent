"""
Neutral actor model — an actor's role is contextual, not fixed.
"""
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field


class ContactChannel(BaseModel):
    channel_type: str  # wechat | whatsapp | openclaw | email | web
    handle: str | None = None
    external_user_id: str | None = None


class Actor(BaseModel):
    actor_id: str
    name: str
    actor_type: Literal[
        "buyer",
        "manufacturer",
        "trading_company",
        "material_supplier",
        "fabric_supplier",
        "trim_supplier",
        "component_supplier",
        "subcontractor",
        "qc_provider",
        "packaging_supplier",
        "logistics_provider",
        "unknown",
    ]
    contact_channels: list[ContactChannel] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)
    default_language: str = "zh"
    metadata: dict = Field(default_factory=dict)
