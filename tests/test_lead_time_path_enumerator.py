"""
Tests for the lead time path enumerator and ranker.

Covers:
1. enumerate_delivery_paths returns one path per viable supplier
2. can_make=False skips supplier
3. assign_labels assigns BEST_OVERALL
4. Fastest path gets FASTEST label
5. Rank ordering is correct
6. Paths with prices can get LOWEST_COST label
7. risk_flags propagate to paths
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.lead_time.models import ProductionCapacity
from src.lead_time.path_enumerator import enumerate_delivery_paths
from src.lead_time.path_ranker import rank_paths, assign_labels, _composite_score

PROJECT_ID = "PROJ-ENUMTEST"


def _make_capacity() -> ProductionCapacity:
    return ProductionCapacity(
        actor_id="actor_m",
        daily_capacity_units=50.0,
        setup_days=1.0,
        queue_days=0.0,
        confidence_score=0.85,
    )


def _make_sr(
    supplier_id: str,
    supplier_name: str,
    fabric_days: int,
    trim_days: int = 2,
    logistics_days: int = 3,
    qc_days: int = 2,
    packaging_days: int = 1,
    confidence_score: float = 0.85,
    risk_flags: list | None = None,
    unit_price: float | None = None,
    can_make: bool = True,
) -> dict:
    return {
        "response_id": f"RESP-{supplier_id.upper()}",
        "supplier_id": supplier_id,
        "supplier_name": supplier_name,
        "can_make": can_make,
        "fabric_days": fabric_days,
        "trim_days": trim_days,
        "qc_days": qc_days,
        "packaging_days": packaging_days,
        "logistics_days": logistics_days,
        "risk_flags": risk_flags or [],
        "confidence_score": confidence_score,
        "completeness_score": confidence_score,
        "unit_price": unit_price,
    }


class TestEnumerateDeliveryPaths:
    def test_returns_path_for_each_viable_supplier(self):
        responses = [
            _make_sr("s1", "Supplier 1", fabric_days=5),
            _make_sr("s2", "Supplier 2", fabric_days=3),
        ]
        paths = enumerate_delivery_paths(
            project_id=PROJECT_ID,
            supplier_responses=responses,
            quantity=100,
        )
        assert len(paths) == 2

    def test_skips_cannot_make_suppliers(self):
        responses = [
            _make_sr("s1", "Supplier 1", fabric_days=5),
            _make_sr("s2", "Supplier 2", fabric_days=3, can_make=False),
        ]
        paths = enumerate_delivery_paths(
            project_id=PROJECT_ID,
            supplier_responses=responses,
            quantity=100,
        )
        assert len(paths) == 1
        assert paths[0].supplier_id == "s1"

    def test_empty_responses_returns_empty(self):
        paths = enumerate_delivery_paths(
            project_id=PROJECT_ID,
            supplier_responses=[],
            quantity=100,
        )
        assert paths == []

    def test_all_cannot_make_returns_empty(self):
        responses = [
            _make_sr("s1", "Supplier 1", fabric_days=5, can_make=False),
        ]
        paths = enumerate_delivery_paths(
            project_id=PROJECT_ID,
            supplier_responses=responses,
        )
        assert paths == []

    def test_path_has_correct_supplier_id(self):
        responses = [_make_sr("supplier_abc", "ABC Corp", fabric_days=5)]
        paths = enumerate_delivery_paths(
            project_id=PROJECT_ID,
            supplier_responses=responses,
        )
        assert paths[0].supplier_id == "supplier_abc"

    def test_path_has_correct_project_id(self):
        responses = [_make_sr("s1", "Supplier 1", fabric_days=5)]
        paths = enumerate_delivery_paths(
            project_id="PROJ-SPECIFIC",
            supplier_responses=responses,
        )
        assert paths[0].project_id == "PROJ-SPECIFIC"

    def test_deadline_applied_to_all_paths(self):
        responses = [
            _make_sr("s1", "Supplier 1", fabric_days=5),
            _make_sr("s2", "Supplier 2", fabric_days=20),
        ]
        paths = enumerate_delivery_paths(
            project_id=PROJECT_ID,
            supplier_responses=responses,
            buyer_deadline_days=30,
            quantity=100,
        )
        for p in paths:
            assert p.deadline_days == 30
            assert p.slack_days is not None

    def test_risk_flags_propagated(self):
        responses = [
            _make_sr("s1", "Supplier 1", fabric_days=5, risk_flags=["substitute_material"]),
        ]
        paths = enumerate_delivery_paths(
            project_id=PROJECT_ID,
            supplier_responses=responses,
            quantity=100,
        )
        assert "substitute_material" in paths[0].risk_flags

    def test_quantity_passed_correctly(self):
        cap = _make_capacity()
        responses = [_make_sr("s1", "Supplier 1", fabric_days=5)]
        paths_100 = enumerate_delivery_paths(
            project_id=PROJECT_ID,
            supplier_responses=responses,
            production_capacity=cap,
            quantity=100,
        )
        paths_1000 = enumerate_delivery_paths(
            project_id=PROJECT_ID,
            supplier_responses=responses,
            production_capacity=cap,
            quantity=1000,
        )
        # More quantity → more production days → longer lead time
        assert paths_1000[0].total_lead_time_days > paths_100[0].total_lead_time_days


class TestRankPaths:
    def test_rank_paths_assigns_rank_1_to_best(self):
        responses = [
            _make_sr("s1", "Supplier 1", fabric_days=5, confidence_score=0.9),
            _make_sr("s2", "Supplier 2", fabric_days=15, confidence_score=0.5),
        ]
        paths = enumerate_delivery_paths(
            project_id=PROJECT_ID,
            supplier_responses=responses,
            quantity=100,
        )
        ranked = rank_paths(paths)
        assert ranked[0].rank == 1
        assert ranked[1].rank == 2

    def test_shorter_lead_time_generally_ranks_higher(self):
        responses = [
            _make_sr("s1", "Supplier 1 (slow)", fabric_days=20, confidence_score=0.85),
            _make_sr("s2", "Supplier 2 (fast)", fabric_days=2, confidence_score=0.85),
        ]
        paths = enumerate_delivery_paths(
            project_id=PROJECT_ID,
            supplier_responses=responses,
            quantity=100,
        )
        ranked = rank_paths(paths)
        # Fast supplier should rank higher (rank=1)
        fast_path = next(p for p in ranked if p.supplier_id == "s2")
        assert fast_path.rank == 1

    def test_rank_is_contiguous(self):
        responses = [
            _make_sr("s1", "Supplier 1", fabric_days=5),
            _make_sr("s2", "Supplier 2", fabric_days=3),
            _make_sr("s3", "Supplier 3", fabric_days=8),
        ]
        paths = enumerate_delivery_paths(
            project_id=PROJECT_ID,
            supplier_responses=responses,
            quantity=100,
        )
        ranked = rank_paths(paths)
        ranks = sorted([p.rank for p in ranked])
        assert ranks == [1, 2, 3]


class TestAssignLabels:
    def test_best_overall_label_assigned(self):
        responses = [
            _make_sr("s1", "Supplier 1", fabric_days=5, confidence_score=0.9),
            _make_sr("s2", "Supplier 2", fabric_days=3, confidence_score=0.7),
        ]
        paths = enumerate_delivery_paths(
            project_id=PROJECT_ID,
            supplier_responses=responses,
            quantity=100,
        )
        labeled = assign_labels(paths)
        labels = [p.label for p in labeled]
        assert "BEST_OVERALL" in labels

    def test_fastest_label_different_from_best(self):
        # s1 has better confidence (BEST_OVERALL) but s2 has shorter lead time (FASTEST)
        responses = [
            _make_sr("s1", "Supplier 1 (best conf)", fabric_days=10, confidence_score=0.95),
            _make_sr("s2", "Supplier 2 (fastest)", fabric_days=2, confidence_score=0.6),
        ]
        paths = enumerate_delivery_paths(
            project_id=PROJECT_ID,
            supplier_responses=responses,
            quantity=100,
        )
        labeled = assign_labels(paths)
        labels = [p.label for p in labeled]
        assert "BEST_OVERALL" in labels
        assert "FASTEST" in labels
        # They should be different suppliers
        best = next(p for p in labeled if p.label == "BEST_OVERALL")
        fastest = next(p for p in labeled if p.label == "FASTEST")
        assert best.path_id != fastest.path_id

    def test_lowest_cost_label_assigned_when_prices_differ(self):
        responses = [
            _make_sr("s1", "Supplier 1 (expensive)", fabric_days=5, confidence_score=0.9, unit_price=50.0),
            _make_sr("s2", "Supplier 2 (cheap)", fabric_days=5, confidence_score=0.7, unit_price=5.0),
            _make_sr("s3", "Supplier 3 (mid)", fabric_days=5, confidence_score=0.75, unit_price=20.0),
        ]
        paths = enumerate_delivery_paths(
            project_id=PROJECT_ID,
            supplier_responses=responses,
            quantity=100,
        )
        labeled = assign_labels(paths)
        labels = [p.label for p in labeled]
        assert "LOWEST_COST" in labels
        cheapest = next(p for p in labeled if p.label == "LOWEST_COST")
        assert cheapest.unit_price == 5.0

    def test_single_supplier_gets_best_overall(self):
        responses = [_make_sr("s1", "Only Supplier", fabric_days=5)]
        paths = enumerate_delivery_paths(
            project_id=PROJECT_ID,
            supplier_responses=responses,
        )
        labeled = assign_labels(paths)
        assert labeled[0].label == "BEST_OVERALL"

    def test_all_paths_get_a_label(self):
        responses = [
            _make_sr("s1", "Supplier 1", fabric_days=5, confidence_score=0.9, unit_price=20.0),
            _make_sr("s2", "Supplier 2", fabric_days=2, confidence_score=0.7, unit_price=25.0),
            _make_sr("s3", "Supplier 3", fabric_days=8, confidence_score=0.6, unit_price=15.0),
            _make_sr("s4", "Supplier 4", fabric_days=6, confidence_score=0.5, unit_price=18.0),
        ]
        paths = enumerate_delivery_paths(
            project_id=PROJECT_ID,
            supplier_responses=responses,
            quantity=100,
        )
        labeled = assign_labels(paths)
        for p in labeled:
            assert p.label is not None, f"Path {p.supplier_id} has no label"

    def test_empty_paths_returns_empty(self):
        result = assign_labels([])
        assert result == []
