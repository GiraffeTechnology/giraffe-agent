"""E2E test: Two suppliers -- graceful degradation.

The example file two_suppliers.json only contains two GARMENT_FACTORY participants
(no fabric supplier), which causes the validator to flag MISSING_FABRIC_SUPPLIER
and the PathEnumerator to produce no options.  To reliably test the 2-participant
rule we build the order inline using fully-capable participants that the engine
can actually route through the graph.
"""

from __future__ import annotations

import pathlib
from datetime import date

import pytest

from gltg import LeadTimeGraphEngine, ApparelOrderInput, DeliveryFeasibilityPacket
from gltg.models.enums import FeasibilityStatus, RiskFlagCode

from tests.conftest import make_participant, make_order

EXAMPLES_DIR = pathlib.Path(__file__).parent.parent.parent / "examples"
TWO_FILE = EXAMPLES_DIR / "two_suppliers.json"


@pytest.fixture(scope="module")
def packet():
    """Build a two-participant order inline so the 0/1/2/3 rule fires correctly."""
    participants = [make_participant(f"P{i}") for i in range(1, 3)]
    order = make_order(
        order_id="ORD-TWO",
        quantity=3000,
        participants=participants,
        requested_date=date(2026, 12, 31),
    )
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
        real_ids = {"P1", "P2"}
        for opt in packet.options:
            for pid in opt.participant_combination:
                assert pid in real_ids, f"Invented participant: {pid}"

    def test_example_file_loads_without_crash(self):
        """The two_suppliers.json example file (if present) must load without crash."""
        if not TWO_FILE.exists():
            pytest.skip(f"Example file not found: {TWO_FILE}")
        from gltg.integrations.json_io import load_order_from_json
        order = load_order_from_json(TWO_FILE)
        engine = LeadTimeGraphEngine()
        packet = engine.evaluate(order)
        assert packet is not None
