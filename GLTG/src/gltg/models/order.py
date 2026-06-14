"""ApparelOrderInput — the primary input to the GLTG engine."""

from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel

from .participant import ParticipantProfile, SupplierMemoryRecord, SupplierResponse
from .reforecast import CalendarConfig, ProgressEvent


class ApparelOrderInput(BaseModel):
    """All information needed to evaluate an apparel order's lead time."""

    order_id: str
    product_type: str                         # e.g. "woven shirt", "knit polo"
    quantity: int
    requested_delivery_date: date | None = None
    trade_term: str | None = None             # FOB, CIF, DDP, etc.
    destination: str | None = None            # destination country/port
    dynamic_form: dict[str, Any] = {}         # free-form buyer requirements
    participants: list[ParticipantProfile] = []
    supplier_memory: list[SupplierMemoryRecord] = []
    supplier_responses: list[SupplierResponse] = []
    progress_events: list[ProgressEvent] = []
    calendar: CalendarConfig | None = None
