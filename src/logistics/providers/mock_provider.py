"""
Mock logistics provider — returns fixture-shaped tracking events for local MVP testing.
Used when LOGISTICS_PROVIDER=mock.
"""
from datetime import datetime, timezone, timedelta

from src.logistics.providers.base_provider import LogisticsProviderBase


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _offset(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


class MockProvider(LogisticsProviderBase):
    provider_name = "mock"

    def create_or_bind_shipment(self, carrier_code, tracking_number, metadata=None) -> dict:
        return {
            "provider_shipment_id": f"MOCK-{tracking_number}",
            "carrier_code": carrier_code,
            "tracking_number": tracking_number,
            "status": "label_created",
        }

    def fetch_tracking_events(self, carrier_code, tracking_number) -> list[dict]:
        return [
            {
                "provider_event_id": f"EVT-001-{tracking_number}",
                "tracking_number": tracking_number,
                "carrier_code": carrier_code,
                "event_time": _offset(3),
                "status_code": "LABEL_CREATED",
                "status_text": "label created",
                "location": "Shenzhen warehouse",
                "description": "Shipping label created",
            },
            {
                "provider_event_id": f"EVT-002-{tracking_number}",
                "tracking_number": tracking_number,
                "carrier_code": carrier_code,
                "event_time": _offset(2),
                "status_code": "PICKED_UP",
                "status_text": "Picked up",
                "location": "Shenzhen sorting center",
                "description": "Parcel picked up",
            },
            {
                "provider_event_id": f"EVT-003-{tracking_number}",
                "tracking_number": tracking_number,
                "carrier_code": carrier_code,
                "event_time": _offset(1),
                "status_code": "IN_TRANSIT",
                "status_text": "In transit",
                "location": "Guangzhou transit hub",
                "description": "Departed Shenzhen sorting center",
            },
            {
                "provider_event_id": f"EVT-004-{tracking_number}",
                "tracking_number": tracking_number,
                "carrier_code": carrier_code,
                "event_time": _utcnow(),
                "status_code": "DELIVERED",
                "status_text": "Delivered",
                "location": "Destination",
                "description": "Delivered successfully",
            },
        ]

    def parse_webhook_payload(self, payload, headers=None) -> list[dict]:
        events = payload.get("events", [])
        if not events and "tracking_number" in payload:
            events = [payload]
        return events

    def verify_webhook_signature(self, payload: bytes, headers: dict) -> bool:
        return True

    def normalize_event(self, raw_event: dict) -> dict:
        return raw_event
