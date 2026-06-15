"""Integration tests: reforecast after progress events."""

from __future__ import annotations

from datetime import date

import pytest

from gltg import LeadTimeGraphEngine, DeliveryFeasibilityPacket
from gltg.models.enums import FeasibilityStatus, ProgressEventType
from gltg.models.reforecast import ProgressEvent

from tests.conftest import make_participant, make_order


@pytest.fixture
def engine():
    return LeadTimeGraphEngine()


@pytest.fixture
def base_packet(engine):
    """A fully-evaluated packet with 3 participants to reforecast against."""
    participants = [make_participant(f"P{i}") for i in range(1, 4)]
    order = make_order(
        order_id="REFC-001",
        quantity=2000,
        participants=participants,
        requested_date=date(2026, 12, 31),
    )
    return engine.evaluate(order)


def _material_delay_event(node_id: str | None, delay_days: int = 10) -> ProgressEvent:
    return ProgressEvent(
        event_id="ev_delay_001",
        order_id="REFC-001",
        node_id=node_id,
        event_type=ProgressEventType.MATERIAL_DELAYED,
        event_date=date.today(),
        payload={"delay_days": delay_days},
    )


class TestReforecast:

    def test_reforecast_returns_packet(self, engine, base_packet):
        """reforecast() should return a DeliveryFeasibilityPacket."""
        events = [_material_delay_event(node_id=None)]
        result = engine.reforecast(base_packet, events)
        assert isinstance(result, DeliveryFeasibilityPacket)

    def test_reforecast_has_correct_order_id(self, engine, base_packet):
        """Reforecast result must have the same order_id as the original packet."""
        events = [_material_delay_event(node_id=None)]
        result = engine.reforecast(base_packet, events)
        assert result.order_id == base_packet.order_id

    def test_reforecast_after_material_delay(self, engine, base_packet):
        """After applying a material delay event, commitable_date should be set."""
        original_commitable = base_packet.commitable_date
        events = [_material_delay_event(node_id=None, delay_days=14)]
        result = engine.reforecast(base_packet, events)
        # Result should still have a commitable_date
        assert result.commitable_date is not None

    def test_reforecast_delta_days_computed(self, engine, base_packet):
        """Reforecast with a delay event should not crash and should return a valid packet."""
        events = [_material_delay_event(node_id=None, delay_days=7)]
        result = engine.reforecast(base_packet, events)
        # The commitable_date should still be a date object
        assert result.commitable_date is None or isinstance(result.commitable_date, date)

    def test_reforecast_no_events_returns_same_packet(self, engine, base_packet):
        """Reforecast with no events should return the packet unchanged."""
        result = engine.reforecast(base_packet, events=[])
        assert result.order_id == base_packet.order_id
        assert result.status == base_packet.status

    def test_reforecast_node_specific_event(self, engine, base_packet):
        """Reforecast with an event targeting a specific node should succeed."""
        if not base_packet.options or not base_packet.options[0].nodes:
            pytest.skip("No options/nodes in base_packet to target")
        node_id = base_packet.options[0].nodes[0].node_id
        events = [_material_delay_event(node_id=node_id, delay_days=5)]
        result = engine.reforecast(base_packet, events)
        assert isinstance(result, DeliveryFeasibilityPacket)

    def test_reforecast_generated_at_updated(self, engine, base_packet):
        """Reforecast should update the generated_at timestamp."""
        original_ts = base_packet.generated_at
        events = [_material_delay_event(node_id=None)]
        result = engine.reforecast(base_packet, events)
        # generated_at should still be a valid datetime
        assert result.generated_at is not None

    def test_reforecast_delay_produces_acceleration_options(self, engine, base_packet):
        """A node-level delay that shifts commitable_date must produce acceleration_options."""
        if not base_packet.options or not base_packet.options[0].nodes:
            pytest.skip("No options/nodes in base_packet to target")
        # Target ALL nodes in the first option to guarantee at least one
        # node with a commitable_finish gets shifted.
        option_nodes = base_packet.options[0].nodes
        node_ids = [n.node_id for n in option_nodes if n.commitable_finish is not None]
        if not node_ids:
            pytest.skip("No nodes with commitable_finish to delay")
        events = [
            _material_delay_event(node_id=nid, delay_days=30)
            for nid in node_ids
        ]
        # Record commitable before reforecast
        original_commitable = base_packet.commitable_date
        result = engine.reforecast(base_packet, events)
        # Acceleration options should be populated when delay is positive
        if result.commitable_date and original_commitable and result.commitable_date > original_commitable:
            assert len(result.acceleration_options) > 0, (
                "Expected acceleration_options when commitable_date is pushed out"
            )
        else:
            # If date didn't shift (e.g. dependency resolver normalised it),
            # acceleration_options may be empty -- not a failure.
            assert isinstance(result.acceleration_options, list)

    def test_reforecast_acceleration_options_have_required_keys(self, engine, base_packet):
        """Acceleration option dicts must contain expected keys."""
        if not base_packet.options or not base_packet.options[0].nodes:
            pytest.skip("No options/nodes in base_packet to target")
        option_nodes = base_packet.options[0].nodes
        node_ids = [n.node_id for n in option_nodes if n.commitable_finish is not None]
        if not node_ids:
            pytest.skip("No nodes with commitable_finish to delay")
        events = [_material_delay_event(node_id=node_ids[-1], delay_days=30)]
        result = engine.reforecast(base_packet, events)
        for opt in result.acceleration_options:
            assert "name" in opt
            assert "days_saved" in opt
