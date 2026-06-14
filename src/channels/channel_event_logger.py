"""
Channel event logger — appends IEG ExecutionEvents for channel-layer activity.

Event types:
  CHANNEL_INBOUND_MESSAGE_RECEIVED
  CHANNEL_MESSAGE_NORMALIZED
  CHANNEL_ACTOR_RESOLVED
  CHANNEL_ROUTE_DECIDED
  CHANNEL_OUTBOUND_MESSAGE_SENT
  CHANNEL_DELIVERY_RECEIPT_RECEIVED
  CHANNEL_SIGNATURE_VERIFICATION_FAILED
  CHANNEL_ROUTE_FAILED
"""

from __future__ import annotations

import sys
from typing import Any


def log_channel_event(
    event_type: str,
    payload: dict[str, Any],
    source_channel: str | None = None,
    actor_id: str | None = None,
) -> None:
    """
    Append a channel event to the Industrial Execution Graph.
    Non-fatal: logs a warning to stderr on DB error rather than crashing.
    """
    try:
        from src.db.session import SessionLocal
        from src.db.repositories.execution_event_repo import ExecutionEventRepo

        db = SessionLocal()
        try:
            repo = ExecutionEventRepo(db)
            repo.log_event(
                event_type=event_type,
                payload_json=payload,
                source_channel=source_channel or payload.get("channel"),
                actor_id=actor_id,
            )
            db.commit()
        except Exception as exc:
            db.rollback()
            print(
                f"[channel_event_logger] WARNING: failed to log {event_type}: {exc}",
                file=sys.stderr,
            )
        finally:
            db.close()
    except Exception as exc:
        print(
            f"[channel_event_logger] WARNING: DB unavailable, skipping {event_type}: {exc}",
            file=sys.stderr,
        )
