"""Unit tests for risk flag generation via ApparelOrderValidator."""

from __future__ import annotations

import pytest

from gltg.apparel.validators import ApparelOrderValidator
from gltg.models.enums import ParticipantType, RiskFlagCode
from gltg.models.order import ApparelOrderInput

from tests.conftest import make_participant, make_order


class TestRiskFlags:

    def setup_method(self):
        self.validator = ApparelOrderValidator()

    def test_no_participants_creates_missing_capacity_flag(self):
        """An order with no participants should produce a MISSING_PRODUCTION_CAPACITY flag."""
        order = make_order(participants=[])
        _, flags = self.validator.validate(order)
        codes = {f.code for f in flags}
        assert RiskFlagCode.MISSING_PRODUCTION_CAPACITY in codes

    def test_missing_fabric_supplier_creates_flag(self):
        """An order with no FABRIC_SUPPLIER participant should produce MISSING_FABRIC_SUPPLIER."""
        # Only a garment factory — no fabric supplier
        factory = make_participant("F1", ptype=ParticipantType.GARMENT_FACTORY)
        order = make_order(participants=[factory])
        _, flags = self.validator.validate(order)
        codes = {f.code for f in flags}
        assert RiskFlagCode.MISSING_FABRIC_SUPPLIER in codes

    def test_risk_flag_has_description(self):
        """All risk flags produced by the validator should have a non-empty description."""
        order = make_order(participants=[])
        _, flags = self.validator.validate(order)
        assert len(flags) > 0
        for flag in flags:
            assert flag.description and len(flag.description) > 0, f"Flag {flag.code} has empty description"

    def test_risk_flag_severity_is_valid(self):
        """All risk flags must have a severity in {LOW, MEDIUM, HIGH, CRITICAL}."""
        valid_severities = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
        order = make_order(participants=[])
        _, flags = self.validator.validate(order)
        for flag in flags:
            assert flag.severity in valid_severities, f"Flag {flag.code} has invalid severity: {flag.severity}"

    def test_valid_order_with_fabric_supplier_no_missing_fabric_flag(self):
        """An order with a fabric supplier should NOT have MISSING_FABRIC_SUPPLIER flag."""
        from gltg.models.capability import Capability
        from gltg.models.enums import ApparelNodeType
        fabric_participant = make_participant(
            "FAB1",
            ptype=ParticipantType.FABRIC_SUPPLIER,
            node_types=[ApparelNodeType.FABRIC_ORDERING],
        )
        order = make_order(participants=[fabric_participant])
        _, flags = self.validator.validate(order)
        codes = {f.code for f in flags}
        assert RiskFlagCode.MISSING_FABRIC_SUPPLIER not in codes

    def test_missing_required_field_flag_when_no_delivery_date(self):
        """Order without a requested delivery date should produce MISSING_REQUIRED_FIELD flag."""
        order = make_order(requested_date=None)
        _, flags = self.validator.validate(order)
        codes = {f.code for f in flags}
        assert RiskFlagCode.MISSING_REQUIRED_FIELD in codes

    def test_low_reliability_supplier_produces_flag(self):
        """A participant with reliability < 0.7 should produce a LOW_SUPPLIER_RELIABILITY flag."""
        from gltg.models.participant import ParticipantProfile
        from gltg.models.capability import Capability
        from gltg.models.enums import ApparelNodeType
        low_rel_supplier = ParticipantProfile(
            participant_id="LOW_REL",
            name="Unreliable Factory",
            participant_type=ParticipantType.GARMENT_FACTORY,
            capabilities=[
                Capability(
                    capability_id="lr-sew",
                    node_type=ApparelNodeType.SEWING,
                    capacity_per_day=100,
                    typical_lead_days=10,
                )
            ],
            reliability_score=0.50,
        )
        order = make_order(participants=[low_rel_supplier])
        _, flags = self.validator.validate(order)
        codes = {f.code for f in flags}
        assert RiskFlagCode.LOW_SUPPLIER_RELIABILITY in codes
