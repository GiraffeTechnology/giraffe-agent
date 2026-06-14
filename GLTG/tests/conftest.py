"""Shared fixtures and helpers for the GLTG test suite."""

from __future__ import annotations

from datetime import date

import pytest

from gltg.models.capability import Capability
from gltg.models.enums import ApparelNodeType, ParticipantType
from gltg.models.order import ApparelOrderInput
from gltg.models.participant import ParticipantProfile


def make_participant(pid, ptype=ParticipantType.GARMENT_FACTORY, node_types=None):
    """Create a ParticipantProfile with capabilities for the given node types."""
    if node_types is None:
        node_types = [
            ApparelNodeType.CUTTING,
            ApparelNodeType.SEWING,
            ApparelNodeType.PACKING,
        ]
    caps = [
        Capability(
            capability_id=f"{pid}-{nt.value[:4]}",
            node_type=nt,
            capacity_per_day=500,
            typical_lead_days=5,
        )
        for nt in node_types
    ]
    return ParticipantProfile(
        participant_id=pid,
        name=f"Participant {pid}",
        participant_type=ptype,
        capabilities=caps,
        reliability_score=0.85,
        on_time_delivery_rate=0.85,
    )


def make_order(order_id="TEST-001", quantity=1000, participants=None, requested_date=None):
    """Create a minimal ApparelOrderInput."""
    return ApparelOrderInput(
        order_id=order_id,
        product_type="men_shirt_cotton",
        quantity=quantity,
        requested_delivery_date=requested_date,
        dynamic_form={"fabric_type": "cotton"},
        participants=participants or [],
    )


# ---------------------------------------------------------------------------
# Pytest fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def three_participants():
    """Three distinct GARMENT_FACTORY participants."""
    return [
        make_participant("P1"),
        make_participant("P2"),
        make_participant("P3"),
    ]


@pytest.fixture
def base_order(three_participants):
    """A standard order with three participants and a requested date."""
    return make_order(
        participants=three_participants,
        requested_date=date(2026, 12, 31),
    )
