"""Unit tests for CriticalPathFinder and topological_sort."""

from __future__ import annotations

from datetime import date

import pytest

from gltg.errors import CyclicDependencyError
from gltg.graph.critical_path import CriticalPathFinder
from gltg.graph.dependency_resolver import DependencyResolver
from gltg.graph.topological import topological_sort
from gltg.models.duration import DurationEstimate
from gltg.models.edge import LeadTimeEdge
from gltg.models.enums import ApparelNodeType, DependencyType
from gltg.models.graph import LeadTimeGraph
from gltg.models.node import LeadTimeNode


def _make_dur(p50: float) -> DurationEstimate:
    return DurationEstimate(
        p50_days=p50,
        p80_days=p50 * 1.4,
        p90_days=p50 * 2.0,
        min_days=p50 * 0.7,
        max_days=p50 * 3.0,
        confidence=0.5,
    )


def _make_node(node_id: str, p50: float = 5.0) -> LeadTimeNode:
    return LeadTimeNode(
        node_id=node_id,
        node_type=ApparelNodeType.CUTTING,
        duration_estimate=_make_dur(p50),
    )


def _make_edge(from_id: str, to_id: str) -> LeadTimeEdge:
    return LeadTimeEdge(
        edge_id=f"e_{from_id}_{to_id}",
        from_node_id=from_id,
        to_node_id=to_id,
        dependency_type=DependencyType.FINISH_TO_START,
        lag_days=0,
        is_hard_dependency=True,
    )


def _build_and_resolve_graph(nodes, edges, start=date(2026, 1, 5)) -> LeadTimeGraph:
    graph = LeadTimeGraph(
        graph_id="g_test",
        order_id="TEST",
        nodes=nodes,
        edges=edges,
    )
    resolver = DependencyResolver()
    resolver.resolve(graph, start, None)
    return graph


class TestCriticalPathFinder:

    def setup_method(self):
        self.finder = CriticalPathFinder()

    def test_single_path_is_critical(self):
        """In a linear A->B->C graph, all three nodes should be on the critical path."""
        a = _make_node("A", 5.0)
        b = _make_node("B", 5.0)
        c = _make_node("C", 5.0)
        graph = _build_and_resolve_graph([a, b, c], [_make_edge("A", "B"), _make_edge("B", "C")])

        critical = self.finder.find(graph)
        assert len(critical) == 3
        assert "A" in critical
        assert "B" in critical
        assert "C" in critical

    def test_longer_branch_is_critical(self):
        """A->C (10 days) and B->C (2 days); A should be on critical path, not B alone."""
        a = _make_node("A", 10.0)
        b = _make_node("B", 2.0)
        c = _make_node("C", 3.0)
        graph = _build_and_resolve_graph(
            [a, b, c],
            [_make_edge("A", "C"), _make_edge("B", "C")],
        )
        critical = self.finder.find(graph)
        assert "A" in critical
        assert "C" in critical

    def test_critical_nodes_marked(self):
        """After find(), nodes on the critical path should have is_critical=True."""
        a = _make_node("A", 5.0)
        b = _make_node("B", 5.0)
        graph = _build_and_resolve_graph([a, b], [_make_edge("A", "B")])

        critical = self.finder.find(graph)
        critical_ids = set(critical)
        for node in graph.nodes:
            if node.node_id in critical_ids:
                assert node.is_critical is True

    def test_bottlenecks_detected(self):
        """A node with p90 - p50 > 7 days on the critical path should be a bottleneck."""
        # p50=5, p90=14 => variance = 9 > 7
        a = LeadTimeNode(
            node_id="A",
            node_type=ApparelNodeType.FABRIC_ORDERING,
            duration_estimate=DurationEstimate(
                p50_days=5.0, p80_days=10.0, p90_days=14.0,
                min_days=3.0, max_days=20.0, confidence=0.5,
            ),
        )
        b = _make_node("B", 3.0)
        graph = _build_and_resolve_graph([a, b], [_make_edge("A", "B")])

        critical = self.finder.find(graph)
        bottlenecks = self.finder.find_bottlenecks(graph, critical)
        # "A" has high variance so should be in bottlenecks if on critical path
        if "A" in critical:
            assert "A" in bottlenecks

    def test_cyclic_graph_raises(self):
        """topological_sort must raise CyclicDependencyError on a cyclic graph."""
        a = _make_node("A", 5.0)
        b = _make_node("B", 5.0)
        edges = [_make_edge("A", "B"), _make_edge("B", "A")]  # cycle!
        with pytest.raises(CyclicDependencyError):
            topological_sort([a, b], edges)

    def test_empty_graph_returns_empty(self):
        """An empty graph should return an empty critical path."""
        graph = LeadTimeGraph(graph_id="g_empty", order_id="TEST", nodes=[], edges=[])
        critical = self.finder.find(graph)
        assert critical == []
