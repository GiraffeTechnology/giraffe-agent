"""E2E test: Two suppliers — graceful degradation."""

from __future__ import annotations

import pathlib

import pytest

from gltg import LeadTimeGraphEngine, ApparelOrderInput, DeliveryFeasibilityPacket
from gltg.models.enums import FeasibilityStatus, RiskFlagCode
from gltg.integrations.json_io import load_order_from_json

from tests.conftest import make_participant, make_order

EXAMPLES_DIR = pathlib.Path(__file__).parent.parent.parent / "examples"
TWO_FILE = EXAMPLES_DIR / "two_suppliers.json"


def _load_order() -> ApparelOrderInput:
    """Load from file if it exists, otherwise build inline."""
    if TWO_FILE.exists():
        return load_order_from_json(TWO_FILE)
    p1 = make_participant("P1")
    p2 = make_participant("P2")
    return make_order(
        order_id="ORD-TWO",
        quantity=3000,
        participants=[p1, p2],
    )


@pytest.fixture(scope="module")
def packet():
    order = _load_order()
    engine = LeadTimeGraphEngine()
    return engine.evaluate(order)


class TestTwoSuppliersGraceful:

    def test_two_supplier_no_crash(self, packet):
        """evaluate() with two suppliers must not raise an exception."""
        assert packet is not None

    def test_two_supplier_status(self, packet):
        """Two suppliers -> status == LIMITED_OPTIONS."""
        assert packet.status == FeasibilityStatus.LIMITED_OPTIONS

    def test_two_supplier_two_options(self, packet):
        """Two suppliers -> exactly 2 delivery options."""
        assert len(packet.options) == 2

    def test_two_supplier_comparison_flag(self, packet):
        """Two suppliers -> LIMITED_COMPARISON flag must be present in risk_flags."""
        codes = {rf.code for rf in packet.risk_flags}
        assert RiskFlagCode.LIMITED_COMPARISON in codes

    def test_two_supplier_commitable_date_set(self, packet):
        """Two suppliers -> commitable_date should be set."""
        assert packet.commitable_date is not None

    def test_two_supplier_options_ordered_by_score(self, packet):
        """Options should be returned in descending score order."""
        if len(packet.options) < 2:
            pytest.skip("Not enough options to test ordering")
        scores = [o.score for o in packet.options if o.score is not None]
        for i in range(len(scores) - 1):
            assert scores[i] >= scores[i + 1], f"Options not sorted by score: {scores}"

    def test_two_supplier_no_fake_participants(self, packet):
        """Options should only reference real participants from the order."""
        order = _load_order()
        real_ids = {p.participant_id for p in order.participants}
        for opt in packet.options:
            for pid in opt.participant_combination:
                assert pid in real_ids, f"Invented participant: {pid}"
