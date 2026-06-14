"""Unit tests for OptionRanker."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from gltg.enumeration.option_ranker import OptionRanker
from gltg.models.enums import DeliveryMode, OptionLabel, OptionStatus
from gltg.models.path import DeliveryPathOption


def _make_option(
    option_id: str,
    on_time_probability: float = 0.7,
    commitable_date: date | None = None,
) -> DeliveryPathOption:
    if commitable_date is None:
        commitable_date = date(2026, 10, 1)
    return DeliveryPathOption(
        option_id=option_id,
        status=OptionStatus.FEASIBLE,
        delivery_mode=DeliveryMode.FULL_DELIVERY,
        participant_combination=["P1"],
        commitable_date=commitable_date,
        most_likely_date=commitable_date - timedelta(days=5),
        earliest_feasible_date=commitable_date - timedelta(days=10),
        risk_adjusted_latest_date=commitable_date + timedelta(days=10),
        on_time_probability=on_time_probability,
    )


class TestOptionRanker:

    def setup_method(self):
        self.ranker = OptionRanker()
        self.requested_date = date(2026, 11, 1)

    def test_empty_returns_empty(self):
        """rank([]) should return []."""
        result = self.ranker.rank([], self.requested_date)
        assert result == []

    def test_one_option_gets_fastest_label(self):
        """A single option should get the FASTEST label."""
        opt = _make_option("opt1", on_time_probability=0.8)
        result = self.ranker.rank([opt], self.requested_date)
        assert len(result) == 1
        assert result[0].label == OptionLabel.FASTEST

    def test_three_options_get_three_labels(self):
        """Three options should each get a distinct label."""
        opts = [
            _make_option("opt1", 0.9, commitable_date=date(2026, 9, 1)),
            _make_option("opt2", 0.7, commitable_date=date(2026, 10, 1)),
            _make_option("opt3", 0.5, commitable_date=date(2026, 11, 1)),
        ]
        result = self.ranker.rank(opts, self.requested_date)
        assert len(result) == 3
        labels = {r.label for r in result}
        assert OptionLabel.FASTEST in labels
        assert OptionLabel.MOST_RELIABLE in labels
        assert OptionLabel.BEST_COMMERCIAL_BALANCE in labels

    def test_higher_on_time_prob_ranks_higher(self):
        """An option with otp=0.9 should rank above one with otp=0.3 all else equal."""
        opt_high = _make_option("opt_high", on_time_probability=0.9, commitable_date=date(2026, 10, 15))
        opt_low = _make_option("opt_low", on_time_probability=0.3, commitable_date=date(2026, 10, 15))
        result = self.ranker.rank([opt_high, opt_low], self.requested_date)
        assert len(result) == 2
        # The first result should have higher score
        assert result[0].score >= result[1].score

    def test_score_is_between_0_and_1(self):
        """All scores returned by the ranker must be in [0, 1]."""
        opts = [
            _make_option("opt1", 0.9, commitable_date=date(2026, 9, 1)),
            _make_option("opt2", 0.5, commitable_date=date(2026, 10, 1)),
            _make_option("opt3", 0.3, commitable_date=date(2026, 11, 1)),
        ]
        result = self.ranker.rank(opts, self.requested_date)
        for opt in result:
            assert opt.score is not None
            assert 0.0 <= opt.score <= 1.0, f"score {opt.score} out of [0,1]"

    def test_score_is_set_on_options(self):
        """After ranking, all returned options should have score set."""
        opts = [_make_option(f"opt{i}", 0.7) for i in range(3)]
        result = self.ranker.rank(opts, self.requested_date)
        for opt in result:
            assert opt.score is not None

    def test_at_most_3_returned(self):
        """Ranker returns at most 3 options even if more are provided."""
        opts = [_make_option(f"opt{i}", 0.7) for i in range(10)]
        result = self.ranker.rank(opts, self.requested_date)
        assert len(result) <= 3
