"""
Logistics event status normalizer — maps provider-specific statuses to canonical values.
Canonical: label_created | picked_up | in_transit | customs | out_for_delivery | delivered | exception | unknown
"""
from __future__ import annotations
import hashlib
import json

_NORMALIZATION_MAP: list[tuple[list[str], str]] = [
    (["label_created", "label created", "已创建面单", "已下单"], "label_created"),
    (["已揽收", "揽收", "picked up", "picked_up", "collected", "pick up"], "picked_up"),
    (["运输中", "in transit", "in_transit", "transit", "on the way", "shipped", "in delivery"], "in_transit"),
    (["清关中", "清关", "customs clearance", "customs", "cleared customs", "customs_clearance"], "customs"),
    (["派送中", "out for delivery", "out_for_delivery", "on delivery", "delivery attempted"], "out_for_delivery"),
    (["已签收", "签收", "delivered", "delivery successful", "completed"], "delivered"),
    (["异常", "exception", "delivery exception", "delivery_exception", "failed", "undeliverable", "returned"], "exception"),
]


def normalize_raw_status(raw_status: str) -> str:
    s = raw_status.strip().lower()
    for patterns, canonical in _NORMALIZATION_MAP:
        for p in patterns:
            if p.lower() in s or s in p.lower():
                return canonical
    return "unknown"


def compute_event_hash(
    shipment_id: str,
    provider_name: str | None,
    tracking_number: str,
    normalized_status: str,
    event_time: str | None,
    location: str | None,
    description: str | None,
) -> str:
    payload = json.dumps([
        shipment_id, provider_name or "", tracking_number, normalized_status,
        event_time or "", location or "", (description or "")[:80],
    ], sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()[:24]
