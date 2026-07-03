"""
M-side Industrial Execution Graph event logger.
Writes JSONL events to data/industrial_execution_graph/events.jsonl.
"""

from __future__ import annotations
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

_EVENTS_FILE = Path("data/industrial_execution_graph/events.jsonl")


def _ensure_dir() -> None:
    _EVENTS_FILE.parent.mkdir(parents=True, exist_ok=True)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def log_m_event(
    event_type: str,
    m_workspace_id: str | None = None,
    b_workspace_id: str | None = None,
    supplier_id: str | None = None,
    rfq_id: str | None = None,
    order_execution_id: str | None = None,
    payload: dict | None = None,
) -> None:
    """
    Log an M-side Industrial Execution Graph event as a JSONL line.

    Each event contains:
    - event_id
    - event_type
    - timestamp
    - b_workspace_id (if available)
    - m_workspace_id (if available)
    - supplier_id (if available)
    - rfq_id (if available)
    - order_execution_id (if available)
    - payload
    """
    _ensure_dir()

    event = {
        "event_id": f"EVT-{uuid.uuid4().hex[:12].upper()}",
        "event_type": event_type,
        "timestamp": _utcnow(),
        "b_workspace_id": b_workspace_id,
        "m_workspace_id": m_workspace_id,
        "supplier_id": supplier_id,
        "rfq_id": rfq_id,
        "order_execution_id": order_execution_id,
        "payload": payload or {},
    }

    with open(_EVENTS_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def read_events(
    event_type: str | None = None,
    m_workspace_id: str | None = None,
    b_workspace_id: str | None = None,
    order_execution_id: str | None = None,
) -> list[dict]:
    """Read and filter events from the JSONL event log."""
    _ensure_dir()
    if not _EVENTS_FILE.exists():
        return []

    events = []
    with open(_EVENTS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                evt = json.loads(line)
                if event_type and evt.get("event_type") != event_type:
                    continue
                if m_workspace_id and evt.get("m_workspace_id") != m_workspace_id:
                    continue
                if b_workspace_id and evt.get("b_workspace_id") != b_workspace_id:
                    continue
                if order_execution_id and evt.get("order_execution_id") != order_execution_id:
                    continue
                events.append(evt)
            except json.JSONDecodeError:
                pass
    return events


def get_event_log_path() -> str:
    """Return the absolute path to the event log file."""
    return str(_EVENTS_FILE.resolve())
