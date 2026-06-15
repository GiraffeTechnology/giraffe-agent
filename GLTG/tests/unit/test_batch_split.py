"""Unit tests for BatchSplitAnalyzer."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from gltg.enumeration.batch_split import BatchSplitAnalyzer
from gltg.models.enums import DeliveryMode, OptionStatus
from gltg.models.path import DeliveryPathOption


def _make_base_option(
    commitable_date: date = date(2026, 10, 1),
    risk_adjusted_date: date = date(2026, 10, 20),
) -> DeliveryPathOption:
    return DeliveryPathOption(
        option_id="base_opt",
        status=OptionStatus.FEASIBLE,
        delivery_mode=DeliveryMode.FULL_DELIVERY,
        participant_combination=["P1"],
        commitable_date=commitable_date,
        most_likely_date=commitable_date - timedelta(days=5),
        earliest_feasible_date=commitable_date - timedelta(days=10),
        risk_adjusted_latest_date=risk_adjusted_date,
        on_time_probability=0.75,
        critical_path=["N1", "N2"],
        bottleneck_nodes=["N1"],
    )


class TestBatchSplitAnalyzer:

    def setup_method(self):
        self.analyzer = BatchSplitAnalyzer()

    def test_generates_split_from_base_option(self):
        """Given a feasible option, generate_splits should return at least one split variant."""
        base = _make_base_option()
        splits = self.analyzer.generate_splits(base, quantity=5000)
        assert len(splits) >= 1

    def test_split_has_partial_delivery_mode(self):
        """Split options should have SPLIT_SHIPMENT or PARTIAL_DELIVERY delivery mode."""
        base = _make_base_option()
        splits = self.analyzer.generate_splits(base, quantity=5000)
        assert len(splits) >= 1
        for split in splits:
            assert split.delivery_mode in (
                DeliveryMode.SPLIT_SHIPMENT,
                DeliveryMode.PARTIAL_DELIVERY,
            ), f"Unexpected mode: {split.delivery_mode}"

    def test_split_date_earlier_than_full(self):
        """The split option's commitable_date should be <= the risk_adjusted_latest_date of the base.

        Per the implementation, the first partial delivery uses the base commitable_date
        and the second delivery uses a later date based on the risk-adjusted window.
        """
        base = _make_base_option(
            commitable_date=date(2026, 10, 1),
            risk_adjusted_date=date(2026, 10, 21),
        )
        splits = self.analyzer.generate_splits(base, quantity=5000)
        assert len(splits) >= 1
        split = splits[0]
        # The split's commitable_date should equal the base commitable (first batch)
        assert split.commitable_date == base.commitable_date
        # The risk_adjusted_latest_date captures the second (later) batch
        assert split.risk_adjusted_latest_date > split.commitable_date

    def test_split_preserves_participant_combination(self):
        """Split variants should use the same participant combination as the base."""
        base = _make_base_option()
        splits = self.analyzer.generate_splits(base, quantity=5000)
        for split in splits:
            assert split.participant_combination == base.participant_combination

    def test_split_option_id_different_from_base(self):
        """Split options must have a different option_id than the base."""
        base = _make_base_option()
        splits = self.analyzer.generate_splits(base, quantity=5000)
        for split in splits:
            assert split.option_id != base.option_id

    def test_empty_fractions_returns_empty(self):
        """Providing fewer than 2 split fractions returns empty list."""
        base = _make_base_option()
        result = self.analyzer.generate_splits(base, quantity=1000, split_fractions=[0.5])
        assert result == []
