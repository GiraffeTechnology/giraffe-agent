"""ApparelOrderInput -- the primary input to the GLTG engine."""

from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel

from .participant import ParticipantProfile, SupplierMemoryRecord, SupplierResponse
from .reforecast import CalendarConfig, ProgressEvent


class ApparelOrderInput(BaseModel):
    """All information needed to evaluate an apparel order's lead time."""

    order_id: str
    product_type: str
    quantity: int
    requested_delivery_date: date | None = None
    evaluation_date: date | None = None  # explicit start date for graph resolution
    trade_term: str | None = None
    destination: str | None = None
    dynamic_form: dict[str, Any] = {}
    participants: list[ParticipantProfile] = []
    supplier_memory: list[SupplierMemoryRecord] = []
    supplier_responses: list[SupplierResponse] = []
    progress_events: list[ProgressEvent] = []
    calendar: CalendarConfig | None = None
