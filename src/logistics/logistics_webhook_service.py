"""
Logistics webhook handler — receives push notifications from logistics providers.
Signature verification must not be bypassed in production mode.
"""
from __future__ import annotations
from src.logistics.providers.provider_registry import get_logistics_provider
from src.logistics.logistics_models import get_shipment, get_shipments_for_project, LogisticsEvent
from src.logistics.logistics_ingestion_service import _normalize_and_store_events
from src.m_side.m_event_logger import log_m_event


def handle_logistics_webhook(
    provider_name: str,
    payload: dict,
    headers: dict | None = None,
    project_id: str | None = None,
) -> list[LogisticsEvent]:
    provider = get_logistics_provider(provider_name)
    raw_payload_bytes = str(payload).encode()

    log_m_event(
        event_type="LOGISTICS_PROVIDER_WEBHOOK_RECEIVED",
        b_workspace_id=project_id,
        payload={"provider": provider_name, "payload_keys": list(payload.keys())},
    )

    if headers and not provider.verify_webhook_signature(raw_payload_bytes, headers):
        log_m_event(
            event_type="LOGISTICS_PROVIDER_API_ERROR",
            b_workspace_id=project_id,
            payload={"error": "Webhook signature verification failed"},
        )
        raise ValueError("Webhook signature verification failed")

    log_m_event(
        event_type="LOGISTICS_WEBHOOK_SIGNATURE_VERIFIED",
        b_workspace_id=project_id,
        payload={"provider": provider_name},
    )

    raw_events = provider.parse_webhook_payload(payload, headers)
    if not raw_events:
        return []

    # Find the shipment from tracking number in first event
    tracking_number = raw_events[0].get("tracking_number") if raw_events else None
    if not tracking_number:
        return []

    # Find matching shipment
    all_events: list[LogisticsEvent] = []
    if project_id:
        shipments = get_shipments_for_project(project_id)
        for shipment in shipments:
            if shipment.tracking_number == tracking_number:
                normalized_events = [provider.normalize_event(e) for e in raw_events]
                all_events.extend(_normalize_and_store_events(shipment, normalized_events, source="webhook"))

    return all_events
