"""Versioned rule packet registry for the B/M-side execution flow.

Each rule packet defines the normative rules for one phase of the procurement
lifecycle.  Rules are versioned, hashed, and immutable once active.  The system
fails closed when:

  - A rule packet is missing
  - A hash does not match the stored content
  - A deprecated rule is used in an active flow
  - An unknown rule version is requested

Usage (standalone — no DB required)::

    from rule_packet_registry import RulePacketRegistry, verify_rule_hash

    registry = RulePacketRegistry()
    packet = registry.get("supplier_response_normalization", version="1.0")
    assert verify_rule_hash(packet)
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Hashing helpers
# ---------------------------------------------------------------------------


def _canonical_json(obj: Any) -> str:
    """Deterministic JSON serialization (sorted keys, no extra whitespace)."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def compute_rule_hash(rule_content_json: dict) -> str:
    """Return a stable SHA-256 hex digest of *rule_content_json*."""
    canonical = _canonical_json(rule_content_json)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def verify_rule_hash(packet: dict) -> bool:
    """Return True if the packet's ``rule_hash`` matches its content."""
    expected = compute_rule_hash(packet["rule_content_json"])
    return packet["rule_hash"] == expected


# ---------------------------------------------------------------------------
# Rule packet definitions
# ---------------------------------------------------------------------------


def _make_packet(
    packet_type: str,
    version: str,
    rule_content_json: dict,
    status: str = "active",
) -> dict:
    content_hash = compute_rule_hash(rule_content_json)
    return {
        "rule_packet_id": str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{packet_type}:{version}")),
        "rule_packet_type": packet_type,
        "version": version,
        "effective_at": "2026-06-13T00:00:00Z",
        "rule_hash": content_hash,
        "source_file": "rule_packet_registry.py",
        "created_by": "system",
        "status": status,
        "rule_content_json": rule_content_json,
    }


# Seven rule packet definitions — one per procurement lifecycle phase.

_RULE_PACKETS: List[dict] = [

    _make_packet(
        "buyer_requirement",
        "1.0",
        {
            "required_fields": ["category", "quantity"],
            "recommended_fields": ["material", "deadline", "destination"],
            "disallow_invented_fields": True,
            "missing_fields_must_be_flagged": True,
            "confidence_threshold_for_structuring": 0.7,
            "rules": [
                "Never infer a deadline that the buyer did not state.",
                "Never infer a material that the buyer did not state.",
                "If quantity is ambiguous, ask for clarification before proceeding.",
                "confidence_score must reflect actual field coverage.",
            ],
        },
    ),

    _make_packet(
        "supplier_inquiry",
        "1.0",
        {
            "required_fields_to_request": [
                "can_supply", "price", "currency", "moq", "lead_time_days"
            ],
            "optional_fields_to_request": [
                "available_quantity", "earliest_dispatch_date",
                "qc_commitment", "logistics_terms"
            ],
            "human_confirmation_required_before_dispatch": True,
            "disallow_fabricated_supplier_details": True,
            "rules": [
                "Do not fabricate supplier contact details.",
                "Do not modify the buyer requirement before sending.",
                "Human must confirm before dispatching inquiry to supplier.",
                "Every inquiry must reference a valid requirement_id.",
            ],
        },
    ),

    _make_packet(
        "supplier_response_normalization",
        "1.0",
        {
            "commercial_fields": ["price", "currency", "moq", "lead_time_days",
                                  "available_quantity", "earliest_dispatch_date"],
            "field_source_options": [
                "supplier_stated", "ai_normalized", "ai_inferred", "missing"
            ],
            "missing_field_handling": "store_as_null_with_risk_flag",
            "placeholder_values_forbidden": [999, -1, 0, "TBD", "N/A"],
            "ai_normalization_allowed": ["unit_conversion", "date_parsing",
                                         "currency_standardization"],
            "rules": [
                "price=None means supplier did not state a price. Do not fill with 999.",
                "lead_time_days=None means supplier did not state lead time. Do not invent.",
                "If can_supply=True but price=None, add missing_fields risk flag.",
                "AI may normalize units (e.g. '2 weeks' → 14 days) but must record "
                "field_source as ai_normalized.",
                "AI may never invent a commercial commitment.",
            ],
        },
    ),

    _make_packet(
        "feasibility_scoring",
        "1.0",
        {
            "scoring_dimensions": [
                "price_completeness", "lead_time_completeness",
                "moq_completeness", "qc_commitment", "risk_flag_count"
            ],
            "ranking_rule": "price ASC for complete responses; incomplete ranked last",
            "top_n": 3,
            "disqualification_rules": [
                "can_supply=False disqualifies the supplier.",
                "Missing both price AND lead_time means incomplete; rank after complete responses.",
            ],
            "rules": [
                "Incomplete responses must appear in the packet with missing_fields noted.",
                "Feasibility score must not be higher than evidence supports.",
                "If fewer than 3 complete responses exist, top_3 may contain incomplete ones "
                "clearly marked as such.",
            ],
        },
    ),

    _make_packet(
        "decision_packet_generation",
        "1.0",
        {
            "required_sections": [
                "rfq_summary", "supplier_comparison", "top_3_options",
                "recommended_option", "risk_flags", "missing_fields",
                "human_confirmation_required"
            ],
            "evidence_required_for": [
                "price", "lead_time_days", "moq", "can_supply",
                "qc_commitment", "logistics_terms"
            ],
            "ai_output_classification": {
                "supplier_stated": "direct quote from supplier response",
                "ai_normalized": "AI converted units or parsed date",
                "ai_inferred": "AI inferred from context — must be risk-flagged",
                "human_confirmed": "human explicitly confirmed this value"
            },
            "rules": [
                "Every commercial value in the packet must cite a supplier_response_id.",
                "Every risk flag must cite an evidence source.",
                "human_confirmation_required must always be true for buyer-facing packets.",
                "The packet must not present AI output as a legal or commercial commitment.",
                "Rule packet version must be recorded in the packet metadata.",
            ],
        },
    ),

    _make_packet(
        "order_confirmation",
        "1.0",
        {
            "confirmation_required_fields": [
                "selected_supplier_actor_id", "confirmed_price", "confirmed_currency",
                "confirmed_lead_time_days", "confirmed_quantity"
            ],
            "human_confirmation_required": True,
            "rules": [
                "Order confirmation requires human sign-off on all five fields above.",
                "AI may not autonomously confirm an order.",
                "Confirmed values must match the selected supplier_response row.",
                "Any deviation from the supplier-stated value must create an "
                "execution_event: HUMAN_OVERRIDE_DETECTED.",
                "Edge status must be set to APPROVED only after confirmation.",
            ],
        },
    ),

    _make_packet(
        "production_qc_logistics",
        "1.0",
        {
            "allowed_event_types": [
                "PRODUCTION_UPDATE_RECEIVED", "QC_UPDATE_RECEIVED",
                "EXCEPTION_REPORTED", "LOGISTICS_HANDOVER_RECEIVED", "ORDER_CLOSED"
            ],
            "rules": [
                "Production updates must include milestone name and progress percentage.",
                "QC updates must include result (pass/fail) and defect rate.",
                "Exception events must include reason and delay_days.",
                "Logistics events must include tracking number and carrier.",
                "All events must carry project_id, edge_id, actor_id.",
                "ORDER_CLOSED must be the final event; no events after closure.",
                "Events are append-only — never update or delete.",
            ],
        },
    ),
]

# Build lookup maps
_BY_TYPE_VERSION: Dict[str, dict] = {
    f"{p['rule_packet_type']}:{p['version']}": p for p in _RULE_PACKETS
}
_BY_ID: Dict[str, dict] = {p["rule_packet_id"]: p for p in _RULE_PACKETS}


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class RulePacketError(Exception):
    """Raised when a rule packet lookup or integrity check fails."""


class RulePacketRegistry:
    """Immutable, fail-closed registry for versioned rule packets."""

    def get(self, rule_type: str, version: str = "1.0") -> dict:
        """Return the rule packet for *rule_type* at *version*.

        Raises RulePacketError if:
        - packet not found
        - packet is deprecated / inactive
        - stored hash does not match content
        """
        key = f"{rule_type}:{version}"
        packet = _BY_TYPE_VERSION.get(key)
        if packet is None:
            raise RulePacketError(
                f"Missing rule packet: type={rule_type!r} version={version!r}. "
                "System fails closed."
            )
        if packet["status"] == "deprecated":
            raise RulePacketError(
                f"Deprecated rule packet cannot be used in active flow: "
                f"type={rule_type!r} version={version!r}."
            )
        if packet["status"] != "active":
            raise RulePacketError(
                f"Rule packet is not active (status={packet['status']!r}): "
                f"type={rule_type!r} version={version!r}."
            )
        if not verify_rule_hash(packet):
            raise RulePacketError(
                f"Rule hash mismatch for type={rule_type!r} version={version!r}. "
                "Possible tampering. System fails closed."
            )
        return packet

    def get_by_id(self, rule_packet_id: str) -> dict:
        """Look up a packet by its UUID."""
        packet = _BY_ID.get(rule_packet_id)
        if packet is None:
            raise RulePacketError(
                f"Unknown rule_packet_id: {rule_packet_id}. System fails closed."
            )
        return self.get(packet["rule_packet_type"], packet["version"])

    def list_active(self) -> List[dict]:
        """Return all active rule packets (safe summary — no content)."""
        return [
            {
                "rule_packet_id": p["rule_packet_id"],
                "rule_packet_type": p["rule_packet_type"],
                "version": p["version"],
                "status": p["status"],
                "rule_hash": p["rule_hash"],
            }
            for p in _RULE_PACKETS
            if p["status"] == "active"
        ]

    def assert_hash_stable(self, rule_type: str, version: str = "1.0") -> None:
        """Assert that the rule packet hash is stable (for CI regression guard)."""
        packet = self.get(rule_type, version)
        if not verify_rule_hash(packet):
            raise RulePacketError(
                f"Hash instability detected for {rule_type}:{version}"
            )


# Module-level default registry instance.
registry = RulePacketRegistry()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    import json as _json
    import sys

    args = sys.argv[1:]
    if "--list" in args:
        print(_json.dumps(registry.list_active(), indent=2))
    elif "--verify-all" in args:
        errors = []
        for p in _RULE_PACKETS:
            if not verify_rule_hash(p):
                errors.append(f"Hash mismatch: {p['rule_packet_type']}:{p['version']}")
        if errors:
            for e in errors:
                print(f"FAIL: {e}", file=sys.stderr)
            sys.exit(1)
        print(f"All {len(_RULE_PACKETS)} rule packets verified OK.")
    else:
        print("Usage: python rule_packet_registry.py [--list | --verify-all]")
