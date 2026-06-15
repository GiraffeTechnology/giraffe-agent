"""Unit tests for the 0/1/2/3 feasibility rules.

Rules (from FeasibilityPacketBuilder):
  0 participants -> NO_FEASIBLE_OPTION, 0 options
  1 participant  -> LIMITED_OPTIONS + LIMITED_COMPETITION flag, 1 option
  2 participants -> LIMITED_OPTIONS + LIMITED_COMPARISON flag, 2 options
  3 participants -> FEASIBLE, 3 options
"""

from __future__ import annotations

from datetime import date

import pytest

from gltg import LeadTimeGraphEngine
from gltg.models.enums import FeasibilityStatus, RiskFlagCode

from tests.conftest import make_participant, make_order


def _evaluate(num_participants: int, requested_date=date(2026, 12, 31)):
    engine = LeadTimeGraphEngine()
    participants = [make_participant(f"P{i}") for i in range(1, num_participants + 1)]
    order = make_order(participants=participants, requested_date=requested_date)
    return engine.evaluate(order)


class TestNoExactTop3Requirement:

    def test_zero_participants_no_crash(self):
        """evaluate() with 0 participants must not raise an exception."""
        result = _evaluate(0)
        assert result is not None

    def test_zero_participants_no_feasible_option(self):
        """0 participants -> status == NO_FEASIBLE_OPTION."""
        result = _evaluate(0)
        assert result.status == FeasibilityStatus.NO_FEASIBLE_OPTION

    def test_one_participant_limited_competition(self):
        """1 participant -> LIMITED_COMPETITION flag present in risk_flags."""
        result = _evaluate(1)
        codes = {rf.code for rf in result.risk_flags}
        assert RiskFlagCode.LIMITED_COMPETITION in codes

    def test_one_participant_one_option(self):
        """1 participant -> exactly 1 option returned."""
        result = _evaluate(1)
        assert len(result.options) == 1

    def test_one_participant_limited_options_status(self):
        """1 participant -> status == LIMITED_OPTIONS."""
        result = _evaluate(1)
        assert result.status == FeasibilityStatus.LIMITED_OPTIONS

    def test_two_participants_limited_comparison(self):
        """2 participants -> LIMITED_COMPARISON flag present in risk_flags."""
        result = _evaluate(2)
        codes = {rf.code for rf in result.risk_flags}
        assert RiskFlagCode.LIMITED_COMPARISON in codes

    def test_two_participants_two_options(self):
        """2 participants -> exactly 2 options returned."""
        result = _evaluate(2)
        assert len(result.options) == 2

    def test_two_participants_limited_options_status(self):
        """2 participants -> status == LIMITED_OPTIONS."""
        result = _evaluate(2)
        assert result.status == FeasibilityStatus.LIMITED_OPTIONS

    def test_three_participants_feasible(self):
        """3 participants -> status == FEASIBLE."""
        result = _evaluate(3)
        assert result.status == FeasibilityStatus.FEASIBLE

    def test_three_participants_three_options(self):
        """3 participants -> exactly 3 options returned."""
        result = _evaluate(3)
        assert len(result.options) == 3

    def test_no_fake_participants_invented(self):
        """The engine must not invent participants -- only use those passed in."""
        n = 2
        result = _evaluate(n)
        # Each option's participant_combination should only reference real participant IDs
        real_ids = {f"P{i}" for i in range(1, n + 1)}
        for opt in result.options:
            for pid in opt.participant_combination:
                assert pid in real_ids, f"Invented participant: {pid}"

    def test_zero_participants_human_review_required(self):
        """0 participants -> human_review_required == True."""
        result = _evaluate(0)
        assert result.human_review_required is True

    def test_options_never_exceed_participant_count(self):
        """Number of options must never exceed number of participants."""
        for n in range(0, 4):
            result = _evaluate(n)
            assert len(result.options) <= n, (
                f"For {n} participants, got {len(result.options)} options"
            )
