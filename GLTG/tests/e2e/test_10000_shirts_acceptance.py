"""E2E acceptance test: 10,000 shirts order from example JSON file."""

from __future__ import annotations

import pathlib

import pytest

from gltg import LeadTimeGraphEngine, DeliveryFeasibilityPacket
from gltg.integrations.json_io import load_order_from_json

EXAMPLES_DIR = pathlib.Path(__file__).parent.parent.parent / "examples"
ORDER_FILE = EXAMPLES_DIR / "10000_shirts_order.json"


@pytest.fixture(scope="module")
def packet():
    """Load and evaluate the 10,000 shirts order. Skip if file not found."""
    if not ORDER_FILE.exists():
        pytest.skip(f"Example file not found: {ORDER_FILE}")
    order = load_order_from_json(ORDER_FILE)
    engine = LeadTimeGraphEngine()
    return engine.evaluate(order)


class TestTenThousandShirtsAcceptance:

    def test_loads_and_evaluates(self, packet):
        """Loading and evaluating the order must not crash; returns a packet."""
        assert packet is not None
        assert isinstance(packet, DeliveryFeasibilityPacket)

    def test_has_commitable_date(self, packet):
        """Packet commitable_date must not be None (order has participants)."""
        assert packet.commitable_date is not None

    def test_has_options(self, packet):
        """Packet should have at least 1 delivery option."""
        assert len(packet.options) >= 1

    def test_has_critical_path(self, packet):
        """Packet critical_path should contain at least one node."""
        assert len(packet.critical_path) >= 1

    def test_risk_flags_present(self, packet):
        """Packet should have at least one risk flag."""
        assert len(packet.risk_flags) >= 1

    def test_order_id_matches(self, packet):
        """Packet order_id should match the example file's order_id."""
        assert packet.order_id == "ORD-2025-001"

    def test_options_have_valid_scores(self, packet):
        """All options should have scores in [0, 1]."""
        for opt in packet.options:
            if opt.score is not None:
                assert 0.0 <= opt.score <= 1.0, f"Score {opt.score} out of range"

    def test_evidence_summary_present(self, packet):
        """Packet should have a non-empty evidence summary."""
        assert len(packet.evidence_summary) > 0
