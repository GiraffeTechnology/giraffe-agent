"""Evidence guard for the B/M-side trust boundary.

Validates that AI-generated fields in supplier responses are supported by
source evidence.  Rules enforced here match rule packet
``supplier_response_normalization`` v1.0:

- price must come from supplier response or be stored as None
- lead_time_days must come from supplier response or be stored as None
- moq must come from supplier response or be stored as None
- currency must come from supplier response or be stored as None

Placeholder values (999, -1, 0, "TBD", "N/A") are forbidden in any
commercial field.  ai_inferred values are allowed ONLY if they are also
risk-flagged.

When unsupported or forbidden values are detected:
  - do NOT silently accept them
  - add ``evidence_gap`` risk flag to the response
  - write ``execution_event: AI_OUTPUT_EVIDENCE_GAP`` via adapter (if supplied)
  - the caller must gate on ``result.requires_human_confirmation``

All ``src.db.*`` imports are lazy (inside functions only).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

COMMERCIAL_FIELDS: Tuple[str, ...] = (
    "price",
    "currency",
    "moq",
    "lead_time_days",
    "available_quantity",
    "earliest_dispatch_date",
)

PLACEHOLDER_VALUES = frozenset([999, -1, 0, "TBD", "N/A", "999"])

ALLOWED_FIELD_SOURCES = frozenset([
    "supplier_stated",
    "ai_normalized",
    "ai_inferred",
    "missing",
])

# ai_inferred is allowed only when the value is explicitly risk-flagged.
REQUIRES_RISK_FLAG_WHEN_INFERRED = frozenset(COMMERCIAL_FIELDS)


# ---------------------------------------------------------------------------
# Result dataclass (no pydantic dependency)
# ---------------------------------------------------------------------------

class EvidenceGuardResult:
    """Outcome of a single evidence-guard check."""

    def __init__(
        self,
        is_clean: bool,
        risk_flags: List[str],
        evidence_gaps: List[dict],
        events_written: List[str],
    ) -> None:
        self.is_clean = is_clean
        self.risk_flags = risk_flags
        self.evidence_gaps = evidence_gaps
        self.events_written = events_written
        self.requires_human_confirmation: bool = not is_clean

    def to_dict(self) -> dict:
        return {
            "is_clean": self.is_clean,
            "requires_human_confirmation": self.requires_human_confirmation,
            "risk_flags": self.risk_flags,
            "evidence_gaps": self.evidence_gaps,
            "events_written": self.events_written,
        }


# ---------------------------------------------------------------------------
# Core guard logic
# ---------------------------------------------------------------------------

def _is_placeholder(value: Any) -> bool:
    """Return True when *value* is a forbidden placeholder."""
    if value is None:
        return False
    return value in PLACEHOLDER_VALUES


def _check_field_source(
    field: str,
    value: Any,
    field_sources: Dict[str, str],
    risk_flags_json: Any,
) -> Optional[str]:
    """Return an error string if this field has a source violation, else None.

    Rules:
    - If source is ``ai_inferred`` and field is commercial, the response's
      risk_flags_json MUST already contain a flag for this field.
    - If source is not in ALLOWED_FIELD_SOURCES, that is an error.
    - If value is non-None and source is ``missing``, that is inconsistent.
    """
    source = field_sources.get(field)
    if source is None:
        return None  # no source annotation present; no violation to record

    if source not in ALLOWED_FIELD_SOURCES:
        return (
            f"field '{field}' has unknown source '{source}'; "
            f"expected one of {sorted(ALLOWED_FIELD_SOURCES)}"
        )

    if source == "missing" and value is not None:
        return (
            f"field '{field}' source=missing but value is {value!r}; "
            "inconsistent — store as None or correct the source annotation"
        )

    if source == "ai_inferred" and field in REQUIRES_RISK_FLAG_WHEN_INFERRED:
        rf = risk_flags_json or {}
        if isinstance(rf, dict):
            has_flag = field in rf or "ai_inferred_fields" in rf
        elif isinstance(rf, list):
            has_flag = any(field in str(f) for f in rf)
        else:
            has_flag = False
        if not has_flag:
            return (
                f"field '{field}' source=ai_inferred but no corresponding "
                "risk flag in risk_flags_json — ai_inferred commercial values "
                "must be risk-flagged"
            )

    return None


def _write_evidence_gap_event(
    adapter: Any,
    project_id: Optional[str],
    edge_id: Optional[str],
    actor_id: Optional[str],
    gaps: List[dict],
    response_id: Optional[str],
) -> Optional[str]:
    """Write an AI_OUTPUT_EVIDENCE_GAP execution event and return its event_id."""
    if adapter is None:
        return None
    try:
        event = adapter.log_event(
            event_type="AI_OUTPUT_EVIDENCE_GAP",
            project_id=project_id or "unknown",
            actor_id=actor_id or "system",
            edge_id=edge_id,
            payload_json={
                "response_id": response_id,
                "evidence_gaps": gaps,
                "human_confirmation_required": True,
            },
        )
        eid = event.get("event_id") if isinstance(event, dict) else str(uuid.uuid4())
        return eid
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def check_response(
    response: dict,
    *,
    field_sources: Optional[Dict[str, str]] = None,
    adapter: Any = None,
    project_id: Optional[str] = None,
    edge_id: Optional[str] = None,
    actor_id: Optional[str] = None,
) -> EvidenceGuardResult:
    """Validate *response* against evidence rules.

    Parameters
    ----------
    response:
        Dict containing at minimum the commercial fields (price, currency,
        moq, lead_time_days, etc.) and optionally ``risk_flags_json``.
    field_sources:
        Optional mapping of field name → source label
        (``"supplier_stated" | "ai_normalized" | "ai_inferred" | "missing"``).
        When omitted, only placeholder-value checks are performed.
    adapter:
        Optional ``BMDbAdapter`` instance.  When supplied, evidence-gap events
        are written to the DB.
    project_id, edge_id, actor_id:
        Context for event logging.  Ignored when *adapter* is None.
    """
    risk_flags: List[str] = []
    evidence_gaps: List[dict] = []
    events_written: List[str] = []

    response_id = response.get("response_id") or response.get("inquiry_id")
    rf_json = response.get("risk_flags_json")

    # ------------------------------------------------------------------ 1. Placeholder check
    for field in COMMERCIAL_FIELDS:
        value = response.get(field)
        if _is_placeholder(value):
            flag = (
                f"placeholder_value_forbidden: field='{field}' value={value!r} "
                "— store as None instead"
            )
            risk_flags.append(flag)
            evidence_gaps.append({
                "field": field,
                "value": value,
                "violation": "placeholder_value_forbidden",
                "rule": "supplier_response_normalization v1.0",
            })

    # ------------------------------------------------------------------ 2. Field-source check
    if field_sources:
        for field in COMMERCIAL_FIELDS:
            value = response.get(field)
            err = _check_field_source(field, value, field_sources, rf_json)
            if err:
                risk_flags.append(f"source_violation: {err}")
                evidence_gaps.append({
                    "field": field,
                    "value": value,
                    "source": field_sources.get(field),
                    "violation": "source_violation",
                    "detail": err,
                })

    # ------------------------------------------------------------------ 3. can_supply=True but price=None
    if response.get("can_supply") is True and response.get("price") is None:
        flag = (
            "missing_commercial_field: can_supply=True but price=None "
            "— missing_fields risk flag required"
        )
        risk_flags.append(flag)
        evidence_gaps.append({
            "field": "price",
            "value": None,
            "violation": "missing_when_can_supply_true",
            "rule": "supplier_response_normalization v1.0",
        })

    # ------------------------------------------------------------------ 4. Event logging
    is_clean = len(evidence_gaps) == 0
    if not is_clean and adapter is not None:
        eid = _write_evidence_gap_event(
            adapter, project_id, edge_id, actor_id, evidence_gaps, response_id
        )
        if eid:
            events_written.append(eid)

    return EvidenceGuardResult(
        is_clean=is_clean,
        risk_flags=risk_flags,
        evidence_gaps=evidence_gaps,
        events_written=events_written,
    )


def check_many(
    responses: List[dict],
    *,
    field_sources_map: Optional[Dict[str, Dict[str, str]]] = None,
    adapter: Any = None,
    project_id: Optional[str] = None,
    actor_id: Optional[str] = None,
) -> Dict[str, EvidenceGuardResult]:
    """Run ``check_response`` for each response dict in *responses*.

    Parameters
    ----------
    responses:
        List of response dicts, each expected to have a ``response_id`` key.
    field_sources_map:
        Optional mapping of response_id → {field → source}.
    adapter, project_id, actor_id:
        Passed through to ``check_response`` for event logging.
    """
    results: Dict[str, EvidenceGuardResult] = {}
    fsm = field_sources_map or {}
    for resp in responses:
        rid = resp.get("response_id", str(uuid.uuid4()))
        result = check_response(
            resp,
            field_sources=fsm.get(rid),
            adapter=adapter,
            project_id=project_id,
            edge_id=resp.get("edge_id"),
            actor_id=actor_id,
        )
        results[rid] = result
    return results
