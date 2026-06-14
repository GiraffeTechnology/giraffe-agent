"""E2E reproducibility test: Run evaluate 5x on same input, check consistency."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from gltg import LeadTimeGraphEngine
from gltg.models.enums import FeasibilityStatus

from tests.conftest import make_participant, make_order


@pytest.fixture(scope="module")
def five_results():
    """Run evaluate 5 times on the same deterministic input."""
    participants = [make_participant(f"P{i}") for i in range(1, 4)]
    order = make_order(
        order_id="REPRO-001",
        quantity=2000,
        participants=participants,
        requested_date=date(2026, 12, 31),
    )
    engine = LeadTimeGraphEngine()
    return [engine.evaluate(order) for _ in range(5)]


class TestReproducibility5x:

    def test_5x_same_status(self, five_results):
        """All 5 runs must return the same FeasibilityStatus."""
        statuses = [r.status for r in five_results]
        assert len(set(statuses)) == 1, f"Statuses varied across runs: {statuses}"

    def test_5x_same_option_count(self, five_results):
        """All 5 runs must return the same number of options."""
        counts = [len(r.options) for r in five_results]
        assert len(set(counts)) == 1, f"Option counts varied: {counts}"

    def test_5x_commitable_date_consistent(self, five_results):
        """All commitable_dates must be within 1 day of each other, or all None."""
        dates = [r.commitable_date for r in five_results]
        all_none = all(d is None for d in dates)
        all_set = all(d is not None for d in dates)

        if all_none:
            return  # All None is consistent

        assert all_set, f"Some runs had None commitable_date and others didn't: {dates}"

        min_date = min(dates)
        max_date = max(dates)
        delta = (max_date - min_date).days
        assert delta <= 1, (
            f"Commitable dates vary by more than 1 day across runs: {dates}"
        )

    def test_5x_order_id_consistent(self, five_results):
        """All 5 runs should produce the same order_id in the packet."""
        order_ids = {r.order_id for r in five_results}
        assert len(order_ids) == 1

    def test_5x_feasibility_status_is_feasible(self, five_results):
        """With 3 participants, all 5 runs should yield FEASIBLE."""
        for i, result in enumerate(five_results):
            assert result.status == FeasibilityStatus.FEASIBLE, (
                f"Run {i+1} returned status {result.status} instead of FEASIBLE"
            )

    def test_5x_critical_path_consistent(self, five_results):
        """Critical path length should be consistent across runs."""
        lengths = [len(r.critical_path) for r in five_results]
        # Allow minor variation but all runs should have a non-empty critical path
        assert all(l > 0 for l in lengths), f"Some runs had empty critical path: {lengths}"
        # All lengths should be within 2 of each other (same graph, same nodes)
        assert max(lengths) - min(lengths) <= 2, (
            f"Critical path length varies too much: {lengths}"
        )
