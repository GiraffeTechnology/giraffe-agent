"""
Logistics shipment and event models — persisted as JSON under data/logistics/.
"""
from __future__ import annotations
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

_SHIPMENT_DIR = Path("data/logistics/shipments")
_EVENTS_DIR = Path("data/logistics/events")


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class LogisticsShipment(BaseModel):
    shipment_id: str
    project_id: str
    order_id: str | None = None
    provider_name: str | None = None
    provider_shipment_id: str | None = None
    carrier_name: str | None = None
    carrier_code: str | None = None
    tracking_number: str
    sender_actor_id: str | None = None
    receiver_actor_id: str | None = None
    origin: str | None = None
    destination: str | None = None
    current_status: Literal[
        "label_created", "picked_up", "in_transit", "customs",
        "out_for_delivery", "delivered", "exception", "unknown",
    ] = "unknown"
    estimated_delivery_date: str | None = None
    actual_delivery_date: str | None = None
    last_event_at: str | None = None
    last_synced_at: str | None = None
    sync_status: str | None = None
    sync_error: str | None = None
    polling_enabled: bool = False
    webhook_enabled: bool = False
    created_at: str = Field(default_factory=_utcnow)
    updated_at: str = Field(default_factory=_utcnow)


class LogisticsEvent(BaseModel):
    logistics_event_id: str
    shipment_id: str
    project_id: str
    provider_name: str | None = None
    provider_event_id: str | None = None
    carrier_name: str | None = None
    tracking_number: str
    event_time: str | None = None
    status: str
    raw_status_code: str | None = None
    normalized_status: str
    location: str | None = None
    description: str | None = None
    raw_payload: dict = Field(default_factory=dict)
    source: Literal["api", "webhook", "im_message", "uploaded_receipt", "mock", "manual"]
    event_hash: str
    is_duplicate: bool = False
    created_at: str = Field(default_factory=_utcnow)


def save_shipment(shipment: LogisticsShipment) -> LogisticsShipment:
    _SHIPMENT_DIR.mkdir(parents=True, exist_ok=True)
    shipment.updated_at = _utcnow()
    path = _SHIPMENT_DIR / f"{shipment.shipment_id}.json"
    path.write_text(shipment.model_dump_json(indent=2), encoding="utf-8")
    return shipment


def get_shipment(shipment_id: str) -> LogisticsShipment:
    path = _SHIPMENT_DIR / f"{shipment_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"Shipment not found: {shipment_id}")
    return LogisticsShipment.model_validate(json.loads(path.read_text(encoding="utf-8")))


def save_event(event: LogisticsEvent) -> LogisticsEvent:
    _EVENTS_DIR.mkdir(parents=True, exist_ok=True)
    path = _EVENTS_DIR / f"{event.logistics_event_id}.json"
    path.write_text(event.model_dump_json(indent=2), encoding="utf-8")
    return event


def get_events_for_shipment(shipment_id: str) -> list[LogisticsEvent]:
    _EVENTS_DIR.mkdir(parents=True, exist_ok=True)
    result = []
    for p in _EVENTS_DIR.glob("LOGE-*.json"):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            e = LogisticsEvent.model_validate(data)
            if e.shipment_id == shipment_id:
                result.append(e)
        except Exception:
            pass
    return sorted(result, key=lambda x: x.event_time or "")


def get_shipments_for_project(project_id: str) -> list[LogisticsShipment]:
    _SHIPMENT_DIR.mkdir(parents=True, exist_ok=True)
    result = []
    for p in _SHIPMENT_DIR.glob("SHIP-*.json"):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            s = LogisticsShipment.model_validate(data)
            if s.project_id == project_id:
                result.append(s)
        except Exception:
            pass
    return result
