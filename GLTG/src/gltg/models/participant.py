"""Participant and supplier models."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from .enums import ApparelNodeType, ParticipantType
from .capability import Capability

if TYPE_CHECKING:
    pass


class ParticipantProfile(BaseModel):
    """A supply-chain participant (factory, supplier, logistics provider, etc.)."""

    participant_id: str
    name: str
    participant_type: ParticipantType
    capabilities: list[Capability] = []
    location: str | None = None
    capacity_per_day: int | None = None    # units per working day (aggregate)
    moq: int | None = None                 # minimum order quantity
    available_from: date | None = None
    reliability_score: float | None = None   # 0.0–1.0
    quality_score: float | None = None       # 0.0–1.0
    on_time_delivery_rate: float | None = None  # 0.0–1.0
    metadata: dict[str, Any] = {}

    def can_handle(self, node_type: ApparelNodeType) -> bool:
        """Return True if any capability covers node_type."""
        return any(c.node_type == node_type for c in self.capabilities)

    def get_capability(self, node_type: ApparelNodeType) -> Capability | None:
        """Return the first matching capability, or None."""
        for c in self.capabilities:
            if c.node_type == node_type:
                return c
        return None


class SupplierMemoryRecord(BaseModel):
    """A historical performance record for a participant on a specific task."""

    record_id: str
    participant_id: str
    node_type: ApparelNodeType | None = None
    order_quantity: int | None = None
    stated_days: float | None = None   # what supplier said
    actual_days: float | None = None   # what actually happened
    on_time: bool | None = None
    quality_pass: bool | None = None
    notes: str | None = None
    recorded_at: date | None = None


class SupplierResponse(BaseModel):
    """A formal quote or confirmation from a supplier for a specific node."""

    response_id: str
    participant_id: str
    node_type: ApparelNodeType | None = None
    confirmed_days: float | None = None
    earliest_start: date | None = None
    price_indication: float | None = None
    currency: str = "USD"
    conditions: str | None = None
    confirmed_at: date | None = None
    expires_at: date | None = None
