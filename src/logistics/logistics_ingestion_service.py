"""
Logistics ingestion service — core ingestion pipeline from IM messages, API calls, or webhooks.
"""
from __future__ import annotations
import hashlib
import uuid
from datetime import datetime, timezone

from src.logistics.logistics_models import (
    LogisticsShipment, LogisticsEvent, save_shipment, get_shipment,
    save_event, get_events_for_shipment,
)
from src.logistics.logistics_event_normalizer import normalize_raw_status, compute_event_hash
from src.logistics.logistics_message_parser import extract_logistics_info_from_im
from src.logistics.logistics_state_mapper import map_logistics_status_to_order_state
from src.logistics.providers.provider_registry import get_logistics_provider
from src.m_side.m_event_logger import log_m_event


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def ingest_tracking_number(
    project_id: str,
    carrier_name: str | None,
    carrier_code: str | None,
    tracking_number: str,
    source: str,
    actor_id: str | None = None,
    order_id: str | None = None,
) -> LogisticsShipment:
    provider = get_logistics_provider()
    bind_result = provider.create_or_bind_shipment(carrier_code, tracking_number)

    shipment = LogisticsShipment(
        shipment_id=f"SHIP-{uuid.uuid4().hex[:10].upper()}",
        project_id=project_id,
        order_id=order_id,
        provider_name=provider.provider_name,
        provider_shipment_id=bind_result.get("provider_shipment_id"),
        carrier_name=carrier_name,
        carrier_code=carrier_code,
        tracking_number=tracking_number,
        sender_actor_id=actor_id,
        current_status="label_created",
    )
    save_shipment(shipment)
    log_m_event(
        event_type="TRACKING_NUMBER_INGESTED",
        b_workspace_id=project_id,
        supplier_id=actor_id,
        payload={
            "shipment_id": shipment.shipment_id,
            "tracking_number": tracking_number,
            "carrier_code": carrier_code,
            "source": source,
        },
    )
    return shipment


def sync_tracking_from_provider(shipment_id: str) -> list[LogisticsEvent]:
    shipment = get_shipment(shipment_id)
    provider = get_logistics_provider(shipment.provider_name)
    raw_events = provider.fetch_tracking_events(shipment.carrier_code, shipment.tracking_number)
    return _normalize_and_store_events(shipment, raw_events, source="api")


def _normalize_and_store_events(
    shipment: LogisticsShipment,
    raw_events: list[dict],
    source: str = "api",
) -> list[LogisticsEvent]:
    existing = get_events_for_shipment(shipment.shipment_id)
    existing_hashes = {e.event_hash for e in existing}
    stored: list[LogisticsEvent] = []

    latest_status = shipment.current_status
    latest_time = shipment.last_event_at or ""

    for raw in raw_events:
        status_text = raw.get("status_text") or raw.get("status") or ""
        status_code = raw.get("status_code") or ""
        normalized = raw.get("normalized_status") or normalize_raw_status(status_text or status_code)
        event_time = raw.get("event_time")
        location = raw.get("location")
        description = raw.get("description")

        # Use provider_event_id as canonical dedup key when available
        provider_event_id = raw.get("provider_event_id")
        if provider_event_id:
            event_hash = hashlib.sha256(
                f"{shipment.shipment_id}:{provider_event_id}".encode()
            ).hexdigest()[:24]
        else:
            event_hash = compute_event_hash(
                shipment.shipment_id, shipment.provider_name, shipment.tracking_number,
                normalized, event_time, location, description,
            )
        is_dup = event_hash in existing_hashes

        evt = LogisticsEvent(
            logistics_event_id=f"LOGE-{uuid.uuid4().hex[:10].upper()}",
            shipment_id=shipment.shipment_id,
            project_id=shipment.project_id,
            provider_name=shipment.provider_name,
            provider_event_id=raw.get("provider_event_id"),
            carrier_name=shipment.carrier_name,
            tracking_number=shipment.tracking_number,
            event_time=event_time,
            status=status_text,
            raw_status_code=status_code,
            normalized_status=normalized,
            location=location,
            description=description,
            raw_payload=raw,
            source=source,  # type: ignore[arg-type]
            event_hash=event_hash,
            is_duplicate=is_dup,
        )
        save_event(evt)

        if is_dup:
            log_m_event(
                event_type="LOGISTICS_EVENT_DEDUPED",
                b_workspace_id=shipment.project_id,
                payload={"event_hash": event_hash, "normalized_status": normalized},
            )
        else:
            existing_hashes.add(event_hash)
            log_m_event(
                event_type="LOGISTICS_EVENT_INGESTED",
                b_workspace_id=shipment.project_id,
                payload={
                    "logistics_event_id": evt.logistics_event_id,
                    "normalized_status": normalized,
                    "location": location,
                },
            )
            log_m_event(
                event_type="LOGISTICS_STATUS_NORMALIZED",
                b_workspace_id=shipment.project_id,
                payload={"raw": status_text, "normalized": normalized},
            )
            if event_time and event_time > latest_time:
                latest_status = normalized  # type: ignore[assignment]
                latest_time = event_time

        stored.append(evt)

    # Update shipment with latest status
    if latest_status != shipment.current_status:
        shipment.current_status = latest_status  # type: ignore[assignment]
        shipment.last_event_at = latest_time or _utcnow()
        shipment.last_synced_at = _utcnow()
        save_shipment(shipment)

        new_order_state = map_logistics_status_to_order_state(str(latest_status))
        if new_order_state:
            log_m_event(
                event_type="ORDER_STATE_UPDATED_FROM_LOGISTICS",
                b_workspace_id=shipment.project_id,
                payload={
                    "shipment_id": shipment.shipment_id,
                    "normalized_status": latest_status,
                    "new_order_state": new_order_state,
                },
            )

    return stored


def sync_all_active_shipments() -> dict:
    from src.logistics.logistics_models import _SHIPMENT_DIR
    import json
    results = {"synced": 0, "errors": 0}
    _SHIPMENT_DIR.mkdir(parents=True, exist_ok=True)
    for p in _SHIPMENT_DIR.glob("SHIP-*.json"):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            s = LogisticsShipment.model_validate(data)
            if s.current_status not in ("delivered", "exception"):
                sync_tracking_from_provider(s.shipment_id)
                results["synced"] += 1
        except Exception as e:
            results["errors"] += 1
    return results


def ingest_logistics_from_im_message(
    project_id: str,
    raw_message: str,
    actor_id: str,
    order_id: str | None = None,
) -> LogisticsShipment | None:
    extract = extract_logistics_info_from_im(raw_message)
    if not extract.tracking_number:
        return None
    return ingest_tracking_number(
        project_id=project_id,
        carrier_name=extract.carrier_name,
        carrier_code=extract.carrier_code,
        tracking_number=extract.tracking_number,
        source="im_message",
        actor_id=actor_id,
        order_id=order_id,
    )
