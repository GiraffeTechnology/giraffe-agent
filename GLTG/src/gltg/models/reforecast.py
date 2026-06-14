"""Reforecast models — progress events, calendar config, and reforecast results."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel

from .enums import ProgressEventType
from .evidence import EvidenceItem
from .risk import RiskFlag


class ProgressEvent(BaseModel):
    """An external event that changes the state of an in-flight order."""

    event_id: str
    order_id: str
    node_id: str | None = None        # which node is affected (None = order-level)
    event_type: ProgressEventType
    event_date: date
    payload: dict[str, Any] = {}      # event-specific data
    evidence: list[EvidenceItem] = []


class CalendarConfig(BaseModel):
    """Working-day calendar configuration for date arithmetic."""

    use_working_days: bool = True
    working_days_per_week: int = 5
    holiday_dates: list[date] = []
    timezone: str = "UTC"


class ReforecastResult(BaseModel):
    """Result of applying progress events to an existing packet."""

    order_id: str
    reforecast_at: datetime
    previous_commitable_date: date | None = None
    new_commitable_date: date | None = None
    delta_days: int | None = None           # positive = later, negative = earlier
    changed_nodes: list[str] = []
    critical_path_changed: bool = False
    new_risk_flags: list[RiskFlag] = []
    acceleration_options: list[dict] = []   # expedite levers
