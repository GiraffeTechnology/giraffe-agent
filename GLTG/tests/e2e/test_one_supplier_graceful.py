"""E2E test: One supplier — graceful degradation.

The example file one_supplier.json only contains a GARMENT_FACTORY participant
(no fabric supplier), which causes the validator to flag MISSING_FABRIC_SUPPLIER
and the PathEnumerator to produce no options.  To reliably test the 1-participant
rule we build the order inline using a fully-capable participant that the engine
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
ONE_FILE = EXAMPLES_DIR / "one_supplier.json"


@pytest.fixture(scope="module")
def packet():
    """Build a one-participant order inline so the 0/1/2/3 rule fires correctly."""
    p = make_participant("P1")
    order = make_order(
        order_id="ORD-ONE",
        quantity=2000,
        participants=[p],
        requested_date=date(2026, 12, 31),
    )
    engine = LeadTimeGraphEngine()
    return engine.evaluate(order)


class TestOneSupplierGraceful:

    def test_one_supplier_no_crash(self, packet):
        """evaluate() with one supplier must not raise an exception."""
        assert packet is not None

    def test_one_supplier_status(self, packet):
        """One supplier -> status == LIMITED_OPTIONS."""
        assert packet.status == FeasibilityStatus.LIMITED_OPTIONS

    def test_one_supplier_one_option(self, packet):
        """One supplier -> exactly 1 delivery option."""
        assert len(packet.options) == 1

    def test_one_supplier_competition_flag(self, packet):
        """One supplier -> LIMITED_COMPETITION flag must be present in risk_flags."""
        codes = {rf.code for rf in packet.risk_flags}
        assert RiskFlagCode.LIMITED_COMPETITION in codes

    def test_one_supplier_commitable_date_set(self, packet):
        """One supplier with capabilities -> commitable_date should be set."""
        assert packet.commitable_date is not None

    def test_one_supplier_human_review_required(self, packet):
        """One supplier -> human_review_required == True (single-source risk)."""
        assert packet.human_review_required is True

    def test_one_supplier_option_has_participant(self, packet):
        """The single option should reference the one real participant."""
        assert len(packet.options) == 1
        assert len(packet.options[0].participant_combination) >= 1

    def test_example_file_loads_without_crash(self):
        """The one_supplier.json example file (if present) must load without crash."""
        if not ONE_FILE.exists():
            pytest.skip(f"Example file not found: {ONE_FILE}")
        from gltg.integrations.json_io import load_order_from_json
        order = load_order_from_json(ONE_FILE)
        engine = LeadTimeGraphEngine()
        packet = engine.evaluate(order)
        assert packet is not None
