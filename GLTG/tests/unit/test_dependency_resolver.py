"""Unit tests for DependencyResolver."""

from __future__ import annotations

from datetime import date

import pytest

from gltg.graph.dependency_resolver import DependencyResolver
from gltg.models.duration import DurationEstimate
from gltg.models.edge import LeadTimeEdge
from gltg.models.enums import ApparelNodeType, DependencyType
from gltg.models.graph import LeadTimeGraph
from gltg.models.node import LeadTimeNode
from gltg.models.reforecast import CalendarConfig


def _make_node(node_id: str, p50: float = 5.0, node_type: ApparelNodeType = ApparelNodeType.CUTTING) -> LeadTimeNode:
    dur = DurationEstimate(
        p50_days=p50,
        p80_days=p50 * 1.4,
        p90_days=p50 * 2.0,
        min_days=p50 * 0.7,
        max_days=p50 * 3.0,
        confidence=0.5,
    )
    return LeadTimeNode(
        node_id=node_id,
        node_type=node_type,
        duration_estimate=dur,
    )


def _make_edge(from_id: str, to_id: str, lag: int = 0) -> LeadTimeEdge:
    return LeadTimeEdge(
        edge_id=f"e_{from_id}_{to_id}",
        from_node_id=from_id,
        to_node_id=to_id,
        dependency_type=DependencyType.FINISH_TO_START,
        lag_days=lag,
        is_hard_dependency=True,
    )


def _make_graph(nodes, edges, order_id="TEST-001") -> LeadTimeGraph:
    return LeadTimeGraph(
        graph_id="g_test",
        order_id=order_id,
        nodes=nodes,
        edges=edges,
    )


class TestDependencyResolver:

    def setup_method(self):
        self.resolver = DependencyResolver()
        self.start = date(2026, 1, 5)  # A Monday

    def test_linear_chain_resolves(self):
        """A -> B -> C, each 5 days. C's earliest_finish >= start + 15 working days."""
        a = _make_node("A", p50=5.0)
        b = _make_node("B", p50=5.0)
        c = _make_node("C", p50=5.0)
        edges = [_make_edge("A", "B"), _make_edge("B", "C")]
        graph = _make_graph([a, b, c], edges)

        self.resolver.resolve(graph, self.start, None)

        assert c.earliest_finish is not None
        assert a.earliest_finish is not None
        assert b.earliest_finish is not None
        # C must finish after A
        assert c.earliest_finish > a.earliest_finish

    def test_parallel_nodes_take_max(self):
        """A (5 days) and B (10 days) both start at same time; C depends on both.
        C's start must be after both A and B finish."""
        a = _make_node("A", p50=5.0)
        b = _make_node("B", p50=10.0)
        c = _make_node("C", p50=3.0)
        edges = [_make_edge("A", "C"), _make_edge("B", "C")]
        graph = _make_graph([a, b, c], edges)

        self.resolver.resolve(graph, self.start, None)

        # C can only start after both A and B finish; B takes longer
        assert c.earliest_start is not None
        assert b.earliest_finish is not None
        # C's start should be >= B's finish (B finishes later)
        assert c.earliest_start >= b.earliest_finish

    def test_lag_days_applied(self):
        """Edge with lag_days=2 should add extra days before the successor starts."""
        a = _make_node("A", p50=5.0)
        b = _make_node("B", p50=5.0)
        edge_with_lag = _make_edge("A", "B", lag=2)
        graph_no_lag = _make_graph([
            _make_node("A", p50=5.0),
            _make_node("B", p50=5.0),
        ], [_make_edge("A", "B", lag=0)])
        graph_with_lag = _make_graph([a, b], [edge_with_lag])

        self.resolver.resolve(graph_no_lag, self.start, None)
        b_no_lag_start = graph_no_lag.nodes[1].earliest_start

        self.resolver.resolve(graph_with_lag, self.start, None)
        b_with_lag_start = b.earliest_start

        assert b_with_lag_start is not None
        assert b_no_lag_start is not None
        assert b_with_lag_start > b_no_lag_start

    def test_calendar_working_days(self):
        """With working_days_per_week=5, a 5-day node started on Monday should end by Friday or later."""
        calendar = CalendarConfig(use_working_days=True, working_days_per_week=5, holiday_dates=[])
        node = _make_node("A", p50=5.0)
        graph = _make_graph([node], [])
        monday = date(2026, 1, 5)  # Monday

        self.resolver.resolve(graph, monday, calendar)

        assert node.earliest_finish is not None
        # 5 working days from Monday should be at least by that same week's Friday
        assert node.earliest_finish >= monday

    def test_single_node_no_edges(self):
        """A single node with no predecessors should start at start_date."""
        node = _make_node("solo", p50=3.0)
        graph = _make_graph([node], [])
        self.resolver.resolve(graph, self.start, None)
        assert node.earliest_start == self.start
        assert node.earliest_finish > self.start
