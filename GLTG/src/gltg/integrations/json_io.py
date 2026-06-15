"""JSON I/O helpers for orders, events, and packets."""

from __future__ import annotations

import json
from pathlib import Path

from ..models.order import ApparelOrderInput
from ..models.packet import DeliveryFeasibilityPacket
from ..models.reforecast import ProgressEvent
from ..packets.serializers import deserialize_packet, serialize_packet


def load_order_from_json(path: str | Path) -> ApparelOrderInput:
    """Load an ApparelOrderInput from a JSON file."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return ApparelOrderInput.model_validate(data)


def load_events_from_json(path: str | Path) -> list[ProgressEvent]:
    """Load a list of ProgressEvent objects from a JSON file.

    The file may contain a JSON array or a JSON object with an 'events' key.
    """
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, list):
        events_data = data
    else:
        events_data = data.get("events", [])
    return [ProgressEvent.model_validate(e) for e in events_data]


def save_packet_to_json(packet: DeliveryFeasibilityPacket, path: str | Path) -> None:
    """Save a DeliveryFeasibilityPacket to a JSON file."""
    serialized = serialize_packet(packet)
    Path(path).write_text(
        json.dumps(serialized, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
