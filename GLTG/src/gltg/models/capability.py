"""Capability model -- what a participant can do and at what throughput."""

from __future__ import annotations

from pydantic import BaseModel

from .enums import ApparelNodeType


class Capability(BaseModel):
    """A specific production or service capability of a participant."""

    capability_id: str
    node_type: ApparelNodeType
    description: str | None = None
    capacity_per_day: int | None = None   # units per working day
    min_order_qty: int | None = None
    max_order_qty: int | None = None
    typical_lead_days: float | None = None
    quality_grade: str | None = None       # e.g. "A", "B", "export"
    certifications: list[str] = []         # e.g. ["GOTS", "OEKO-TEX"]
