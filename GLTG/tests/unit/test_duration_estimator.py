"""Unit tests for DurationEstimator."""

from __future__ import annotations

from datetime import date

import pytest

from gltg.estimation.duration_estimator import DurationEstimator
from gltg.models.capability import Capability
from gltg.models.enums import ApparelNodeType, EvidenceSourceType, ParticipantType
from gltg.models.participant import ParticipantProfile, SupplierMemoryRecord, SupplierResponse


def _make_participant(pid: str = "FACT-001", node_type: ApparelNodeType = ApparelNodeType.SEWING, typical_lead_days: float = 10) -> ParticipantProfile:
    cap = Capability(
        capability_id=f"{pid}-cap",
        node_type=node_type,
        capacity_per_day=500,
        typical_lead_days=typical_lead_days,
    )
    return ParticipantProfile(
        participant_id=pid,
        name="Test Factory",
        participant_type=ParticipantType.GARMENT_FACTORY,
        capabilities=[cap],
        reliability_score=0.85,
        on_time_delivery_rate=0.85,
    )


class TestDurationEstimator:

    def setup_method(self):
        self.estimator = DurationEstimator()

    def test_baseline_only(self):
        """No supplier response, no memory -> uses category baseline -> confidence <= 0.5."""
        est = self.estimator.estimate(
            node_type=ApparelNodeType.CUTTING,
            participant=None,
            supplier_response=None,
            memory_records=[],
            progress_events=[],
            quantity=1000,
        )
        assert est.p50_days > 0
        assert est.confidence <= 0.5

    def test_supplier_claim_raises_confidence(self):
        """With a supplier response, confidence should exceed baseline-only confidence."""
        # Get baseline-only confidence first
        baseline_est = self.estimator.estimate(
            node_type=ApparelNodeType.SEWING,
            participant=None,
            supplier_response=None,
            memory_records=[],
            progress_events=[],
            quantity=1000,
        )

        # Now add a supplier response
        sr = SupplierResponse(
            response_id="resp-001",
            participant_id="FACT-001",
            node_type=ApparelNodeType.SEWING,
            confirmed_days=10.0,
        )
        with_sr = self.estimator.estimate(
            node_type=ApparelNodeType.SEWING,
            participant=None,
            supplier_response=sr,
            memory_records=[],
            progress_events=[],
            quantity=1000,
        )
        assert with_sr.confidence > baseline_est.confidence

    def test_memory_adjusted_estimate(self):
        """Memory records showing delays should produce a higher duration than stated."""
        participant = _make_participant(typical_lead_days=10)
        # Memory shows supplier consistently runs late
        memory = [
            SupplierMemoryRecord(
                record_id="m1",
                participant_id="FACT-001",
                node_type=ApparelNodeType.SEWING,
                stated_days=10.0,
                actual_days=14.0,
                on_time=False,
                recorded_at=date(2025, 1, 1),
            ),
            SupplierMemoryRecord(
                record_id="m2",
                participant_id="FACT-001",
                node_type=ApparelNodeType.SEWING,
                stated_days=10.0,
                actual_days=13.0,
                on_time=False,
                recorded_at=date(2025, 2, 1),
            ),
        ]
        est = self.estimator.estimate(
            node_type=ApparelNodeType.SEWING,
            participant=participant,
            supplier_response=None,
            memory_records=memory,
            progress_events=[],
            quantity=1000,
        )
        # Memory-adjusted estimate should be present
        assert est.memory_adjusted_days is not None
        # The memory-adjusted days should reflect the actual delay pattern
        assert est.memory_adjusted_days > 10.0

    def test_missing_participant_adds_low_confidence(self):
        """Without a participant, confidence should be low (<= 0.5)."""
        est = self.estimator.estimate(
            node_type=ApparelNodeType.FABRIC_ORDERING,
            participant=None,
            supplier_response=None,
            memory_records=[],
            progress_events=[],
            quantity=1000,
        )
        assert est.confidence <= 0.5

    def test_p50_lt_p80_lt_p90(self):
        """p50 < p80 < p90 must always hold for any node type."""
        for node_type in [
            ApparelNodeType.CUTTING,
            ApparelNodeType.SEWING,
            ApparelNodeType.FABRIC_ORDERING,
            ApparelNodeType.SHIPMENT,
        ]:
            est = self.estimator.estimate(
                node_type=node_type,
                participant=None,
                supplier_response=None,
                memory_records=[],
                progress_events=[],
                quantity=1000,
            )
            assert est.p50_days <= est.p80_days, f"{node_type}: p50={est.p50_days} > p80={est.p80_days}"
            assert est.p80_days <= est.p90_days, f"{node_type}: p80={est.p80_days} > p90={est.p90_days}"

    def test_quantity_scaling(self):
        """SEWING node with 10000 qty should yield larger p50 than with 1000 qty."""
        est_1000 = self.estimator.estimate(
            node_type=ApparelNodeType.SEWING,
            participant=None,
            supplier_response=None,
            memory_records=[],
            progress_events=[],
            quantity=1000,
        )
        est_10000 = self.estimator.estimate(
            node_type=ApparelNodeType.SEWING,
            participant=None,
            supplier_response=None,
            memory_records=[],
            progress_events=[],
            quantity=10000,
        )
        assert est_10000.p50_days > est_1000.p50_days
