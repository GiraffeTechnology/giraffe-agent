"""Unit tests for EvidenceWeighter."""

from __future__ import annotations

import pytest

from gltg.estimation.evidence_weighting import EvidenceWeighter, EVIDENCE_WEIGHTS
from gltg.models.enums import EvidenceSourceType


class TestEvidenceWeighter:

    def setup_method(self):
        self.weighter = EvidenceWeighter()

    def test_actual_progress_dominates(self):
        """ACTUAL_PROGRESS weight must be the highest of all source types."""
        actual_weight = self.weighter.get_weight(EvidenceSourceType.ACTUAL_PROGRESS)
        for source_type in EvidenceSourceType:
            if source_type != EvidenceSourceType.ACTUAL_PROGRESS:
                assert actual_weight >= self.weighter.get_weight(source_type), (
                    f"ACTUAL_PROGRESS ({actual_weight}) not >= {source_type} ({self.weighter.get_weight(source_type)})"
                )

    def test_category_baseline_lowest_weight(self):
        """CATEGORY_BASELINE should have the lowest weight among defined sources."""
        baseline_weight = self.weighter.get_weight(EvidenceSourceType.CATEGORY_BASELINE)
        for source_type in EvidenceSourceType:
            if source_type != EvidenceSourceType.AI_ESTIMATE:
                # AI_ESTIMATE is explicitly lower; among the rest, CATEGORY_BASELINE should be <= all
                other_weight = self.weighter.get_weight(source_type)
                assert baseline_weight <= other_weight, (
                    f"CATEGORY_BASELINE ({baseline_weight}) > {source_type} ({other_weight})"
                )

    def test_all_evidence_types_produce_valid_blend(self):
        """Blending one item of each evidence type should produce a finite positive value."""
        items = [
            (10.0, EvidenceSourceType.ACTUAL_PROGRESS, 0.9),
            (12.0, EvidenceSourceType.SUPPLIER_CONFIRMATION, 0.75),
            (11.0, EvidenceSourceType.HISTORICAL_MEMORY, 0.6),
            (13.0, EvidenceSourceType.SUPPLIER_QUOTE, 0.5),
            (14.0, EvidenceSourceType.CATEGORY_BASELINE, 0.4),
        ]
        result = self.weighter.blend(items)
        assert result is not None
        assert result > 0
        # Result should be between the min and max input values
        assert 10.0 <= result <= 14.0

    def test_empty_evidence_returns_baseline_weight(self):
        """Blending an empty list returns None (fallback to baseline)."""
        result = self.weighter.blend([])
        assert result is None

    def test_overall_confidence_empty_returns_low(self):
        """No evidence items -> confidence defaults to low value."""
        conf = self.weighter.overall_confidence([])
        assert 0.0 <= conf <= 0.3

    def test_overall_confidence_increases_with_sources(self):
        """More authoritative sources should yield higher confidence."""
        conf_baseline_only = self.weighter.overall_confidence([
            (EvidenceSourceType.CATEGORY_BASELINE, 0.4),
        ])
        conf_with_actual = self.weighter.overall_confidence([
            (EvidenceSourceType.CATEGORY_BASELINE, 0.4),
            (EvidenceSourceType.ACTUAL_PROGRESS, 0.9),
        ])
        assert conf_with_actual > conf_baseline_only

    def test_all_weights_between_0_and_1(self):
        """Every evidence source type weight should be in [0, 1]."""
        for source_type in EvidenceSourceType:
            w = self.weighter.get_weight(source_type)
            assert 0.0 <= w <= 1.0, f"{source_type} weight {w} out of [0,1]"
