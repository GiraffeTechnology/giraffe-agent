"""Serialization helpers for DeliveryFeasibilityPacket."""

from __future__ import annotations

from ..models.packet import DeliveryFeasibilityPacket


def serialize_packet(packet: DeliveryFeasibilityPacket) -> dict:
    """Serialize packet to a JSON-compatible dict using Pydantic v2 model_dump."""
    return packet.model_dump(mode="json")


def deserialize_packet(data: dict) -> DeliveryFeasibilityPacket:
    """Deserialize a dict (from JSON) back into a DeliveryFeasibilityPacket."""
    return DeliveryFeasibilityPacket.model_validate(data)
