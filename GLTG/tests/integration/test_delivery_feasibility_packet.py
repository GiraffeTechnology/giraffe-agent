"""Integration tests: evaluate() -> DeliveryFeasibilityPacket."""

from __future__ import annotations

from datetime import date

import pytest

from gltg import LeadTimeGraphEngine, DeliveryFeasibilityPacket
from gltg.models.enums import FeasibilityStatus

from tests.conftest import make_participant, make_order


@pytest.fixture
def engine():
    return LeadTimeGraphEngine()


@pytest.fixture
def three_participant_order():
    participants = [make_participant(f"P{i}") for i in range(1, 4)]
    return make_order(
        order_id="INT-PKT-001",
        quantity=3000,
        participants=participants,
        requested_date=date(2026, 12, 31),
    )


@pytest.fixture
def two_participant_order():
    participants = [make_participant(f"P{i}") for i in range(1, 3)]
    return make_order(
        order_id="INT-PKT-002",
        quantity=2000,
        participants=participants,
        requested_date=date(2026, 12, 31),
    )


class TestDeliveryFeasibilityPacket:

    def test_evaluate_returns_packet(self, engine, three_participant_order):
        """engine.evaluate(order) should return a DeliveryFeasibilityPacket."""
        packet = engine.evaluate(three_participant_order)
        assert isinstance(packet, DeliveryFeasibilityPacket)

    def test_packet_has_commitable_date(self, engine, three_participant_order):
        """Packet with participants should have a commitable_date."""
        packet = engine.evaluate(three_participant_order)
        assert packet.commitable_date is not None

    def test_packet_status_correct(self, engine, three_participant_order):
        """Packet status should be a FeasibilityStatus value."""
        packet = engine.evaluate(three_participant_order)
        assert packet.status in set(FeasibilityStatus)

    def test_packet_options_capped_at_3(self, engine, three_participant_order):
        """Packet should never have more than 3 options."""
        packet = engine.evaluate(three_participant_order)
        assert len(packet.options) <= 3

    def test_packet_options_never_more_than_participants(self, engine, two_participant_order):
        """Number of options must not exceed number of participants."""
        packet = engine.evaluate(two_participant_order)
        n_participants = len(two_participant_order.participants)
        assert len(packet.options) <= n_participants

    def test_evidence_preserved_in_packet(self, engine, three_participant_order):
        """Packet evidence_summary should be non-empty when participants are present."""
        packet = engine.evaluate(three_participant_order)
        assert len(packet.evidence_summary) > 0

    def test_packet_has_order_id(self, engine, three_participant_order):
        """Packet order_id should match the input order_id."""
        packet = engine.evaluate(three_participant_order)
        assert packet.order_id == three_participant_order.order_id

    def test_packet_has_risk_flags(self, engine):
        """Any order evaluation should produce at least one risk flag."""
        order = make_order(participants=[])
        packet = engine.evaluate(order)
        assert len(packet.risk_flags) > 0

    def test_packet_options_have_commitable_date(self, engine, three_participant_order):
        """All options in the packet should have a commitable_date."""
        packet = engine.evaluate(three_participant_order)
        for opt in packet.options:
            assert opt.commitable_date is not None, f"Option {opt.option_id} missing commitable_date"

    def test_feasible_with_3_participants(self, engine, three_participant_order):
        """Three distinct participants should yield FEASIBLE status."""
        packet = engine.evaluate(three_participant_order)
        assert packet.status == FeasibilityStatus.FEASIBLE

    def test_packet_generated_at_set(self, engine, three_participant_order):
        """generated_at should be set on the returned packet."""
        packet = engine.evaluate(three_participant_order)
        assert packet.generated_at is not None

    # ------------------------------------------------------------------
    # human_review_required must be True for ALL supplier counts (v1.0)
    # ------------------------------------------------------------------

    def test_human_review_required_zero_suppliers(self, engine):
        order = make_order(order_id="HR-0", participants=[])
        packet = engine.evaluate(order)
        assert packet.human_review_required is True

    def test_human_review_required_one_supplier(self, engine):
        order = make_order(order_id="HR-1", participants=[make_participant("P1")])
        packet = engine.evaluate(order)
        assert packet.human_review_required is True

    def test_human_review_required_two_suppliers(self, engine):
        participants = [make_participant(f"P{i}") for i in range(1, 3)]
        order = make_order(order_id="HR-2", participants=participants)
        packet = engine.evaluate(order)
        assert packet.human_review_required is True

    def test_human_review_required_three_suppliers(self, engine, three_participant_order):
        packet = engine.evaluate(three_participant_order)
        assert packet.human_review_required is True
