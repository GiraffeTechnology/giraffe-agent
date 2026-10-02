# Unicode escapes preserve the original multilingual parser vocabulary.
# This source representation does not translate the accepted input values.
"""
Logistics event status normalizer — maps provider-specific statuses to canonical values.
Canonical: label_created | picked_up | in_transit | customs | out_for_delivery | delivered | exception | unknown
"""
from __future__ import annotations
import hashlib
import json

_NORMALIZATION_MAP: list[tuple[list[str], str]] = [
    (["label_created", "label created", '\u5df2\u521b\u5efa\u9762\u5355', '\u5df2\u4e0b\u5355'], "label_created"),
    (['\u5df2\u63fd\u6536', '\u63fd\u6536', "picked up", "picked_up", "collected", "pick up"], "picked_up"),
    (['\u8fd0\u8f93\u4e2d', "in transit", "in_transit", "transit", "on the way", "shipped", "in delivery"], "in_transit"),
    (['\u6e05\u5173\u4e2d', '\u6e05\u5173', "customs clearance", "customs", "cleared customs", "customs_clearance"], "customs"),
    (['\u6d3e\u9001\u4e2d', "out for delivery", "out_for_delivery", "on delivery", "delivery attempted"], "out_for_delivery"),
    (['\u5df2\u7b7e\u6536', '\u7b7e\u6536', "delivered", "delivery successful", "completed"], "delivered"),
    (['\u5f02\u5e38', "exception", "delivery exception", "delivery_exception", "failed", "undeliverable", "returned"], "exception"),
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
