"""Integration tests: GiraffeAgentAdapter."""

from __future__ import annotations

from datetime import date

import pytest

from gltg import LeadTimeGraphEngine, ApparelOrderInput, DeliveryFeasibilityPacket
from gltg.integrations.giraffe_agent_adapter import GiraffeAgentAdapter
from gltg.models.enums import FeasibilityStatus

from tests.conftest import make_participant, make_order


@pytest.fixture
def adapter():
    return GiraffeAgentAdapter()


@pytest.fixture
def engine():
    return LeadTimeGraphEngine()


@pytest.fixture
def sample_form_data():
    return {
        "order_id": "ADAPT-001",
        "product_type": "men_shirt_cotton",
        "quantity": 2000,
        "requested_delivery_date": "2026-12-31",
        "trade_term": "FOB",
        "destination": "Hamburg",
        "dynamic_form": {"fabric_type": "cotton"},
        "participants": [
            {
                "participant_id": "PA1",
                "name": "Factory A",
                "participant_type": "GARMENT_FACTORY",
                "capabilities": [
                    {
                        "capability_id": "PA1-sew",
                        "node_type": "SEWING",
                        "capacity_per_day": 500,
                        "typical_lead_days": 10,
                    }
                ],
                "reliability_score": 0.85,
                "on_time_delivery_rate": 0.82,
            }
        ],
    }


class TestGiraffeAgentAdapter:

    def test_dynamic_form_to_order(self, adapter, sample_form_data):
        """adapter.dynamic_form_to_order() should return an ApparelOrderInput."""
        order = adapter.dynamic_form_to_order(sample_form_data)
        assert isinstance(order, ApparelOrderInput)
        assert order.order_id == "ADAPT-001"
        assert order.product_type == "men_shirt_cotton"
        assert order.quantity == 2000

    def test_dynamic_form_requested_date_parsed(self, adapter, sample_form_data):
        """The requested_delivery_date string should be parsed to a date object."""
        order = adapter.dynamic_form_to_order(sample_form_data)
        assert order.requested_delivery_date == date(2026, 12, 31)

    def test_dynamic_form_participants_built(self, adapter, sample_form_data):
        """Participants from the form should be included in the order."""
        order = adapter.dynamic_form_to_order(sample_form_data)
        assert len(order.participants) == 1
        assert order.participants[0].participant_id == "PA1"

    def test_packet_to_agent_response(self, adapter, engine):
        """adapter.packet_to_agent_response() should convert a packet to a dict."""
        participants = [make_participant(f"P{i}") for i in range(1, 4)]
        order = make_order(participants=participants, requested_date=date(2026, 12, 31))
        packet = engine.evaluate(order)
        response = adapter.packet_to_agent_response(packet)
        assert isinstance(response, dict)
        assert "order_id" in response
        assert "status" in response
        assert "commitable_date" in response

    def test_round_trip_status_preserved(self, adapter, engine):
        """Status value is preserved through adapter conversion."""
        participants = [make_participant(f"P{i}") for i in range(1, 4)]
        order = make_order(participants=participants, requested_date=date(2026, 12, 31))
        packet = engine.evaluate(order)
        response = adapter.packet_to_agent_response(packet)
        # Status in response should match packet status value
        assert response["status"] == packet.status.value

    def test_response_options_present(self, adapter, engine):
        """Agent response should include options list."""
        participants = [make_participant(f"P{i}") for i in range(1, 4)]
        order = make_order(participants=participants, requested_date=date(2026, 12, 31))
        packet = engine.evaluate(order)
        response = adapter.packet_to_agent_response(packet)
        assert "options" in response
        assert isinstance(response["options"], list)

    def test_dynamic_form_missing_optional_fields(self, adapter):
        """Adapter should handle missing optional fields gracefully."""
        minimal_form = {
            "order_id": "MIN-001",
            "product_type": "shirt",
            "quantity": 100,
        }
        order = adapter.dynamic_form_to_order(minimal_form)
        assert order.order_id == "MIN-001"
        assert order.requested_delivery_date is None
        assert order.participants == []

    def test_response_human_review_required_field(self, adapter, engine):
        """Agent response should contain human_review_required field."""
        order = make_order(participants=[])
        packet = engine.evaluate(order)
        response = adapter.packet_to_agent_response(packet)
        assert "human_review_required" in response
        assert isinstance(response["human_review_required"], bool)
