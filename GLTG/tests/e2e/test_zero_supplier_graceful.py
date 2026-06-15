"""E2E test: Zero suppliers -- graceful degradation."""

from __future__ import annotations

import pathlib
from datetime import date

import pytest

from gltg import LeadTimeGraphEngine, ApparelOrderInput, DeliveryFeasibilityPacket
from gltg.models.enums import FeasibilityStatus
from gltg.integrations.json_io import load_order_from_json

EXAMPLES_DIR = pathlib.Path(__file__).parent.parent.parent / "examples"
ZERO_FILE = EXAMPLES_DIR / "zero_suppliers.json"


def _load_order() -> ApparelOrderInput:
    """Load from file if exists, otherwise build inline."""
    if ZERO_FILE.exists():
        return load_order_from_json(ZERO_FILE)
    return ApparelOrderInput(
        order_id="ORD-ZERO",
        product_type="shirt",
        quantity=5000,
        requested_delivery_date=date(2025, 9, 1),
        dynamic_form={},
        participants=[],
    )


@pytest.fixture(scope="module")
def packet():
    order = _load_order()
    engine = LeadTimeGraphEngine()
    return engine.evaluate(order)


class TestZeroSupplierGraceful:

    def test_zero_supplier_no_crash(self, packet):
        """evaluate() with zero suppliers must not raise an exception."""
        assert packet is not None

    def test_zero_supplier_status(self, packet):
        """Zero suppliers -> status == NO_FEASIBLE_OPTION."""
        assert packet.status == FeasibilityStatus.NO_FEASIBLE_OPTION

    def test_zero_supplier_no_options(self, packet):
        """Zero suppliers -> no delivery options in packet."""
        assert len(packet.options) == 0

    def test_zero_supplier_human_review_required(self, packet):
        """Zero suppliers -> human_review_required == True."""
        assert packet.human_review_required is True

    def test_zero_supplier_has_risk_flags(self, packet):
        """Zero suppliers -> at least one risk flag should be present."""
        assert len(packet.risk_flags) > 0

    def test_zero_supplier_no_commitable_date(self, packet):
        """Zero suppliers -> commitable_date should be None."""
        assert packet.commitable_date is None

    def test_zero_supplier_packet_has_order_id(self, packet):
        """Packet should retain the order_id from the input."""
        assert packet.order_id is not None
        assert len(packet.order_id) > 0
