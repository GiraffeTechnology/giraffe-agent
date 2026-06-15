"""Unit tests for PathEnumerator."""

from __future__ import annotations

from datetime import date

import pytest

from gltg import LeadTimeGraphEngine, ApparelOrderInput, ParticipantProfile
from gltg.enumeration.path_enumerator import PathEnumerator
from gltg.models.capability import Capability
from gltg.models.duration import DurationEstimate
from gltg.models.edge import LeadTimeEdge
from gltg.models.enums import ApparelNodeType, DependencyType, ParticipantType
from gltg.models.graph import LeadTimeGraph
from gltg.models.node import LeadTimeNode

from tests.conftest import make_participant, make_order


def _make_resolved_graph_with_participant(pid: str) -> LeadTimeGraph:
    """Build a minimal resolved graph that has a participant assigned."""
    from gltg.graph.dependency_resolver import DependencyResolver
    dur = DurationEstimate(
        p50_days=5.0, p80_days=7.0, p90_days=10.0,
        min_days=3.0, max_days=15.0, confidence=0.5,
    )
    node_a = LeadTimeNode(
        node_id="N_A",
        node_type=ApparelNodeType.CUTTING,
        participant_id=pid,
        duration_estimate=dur,
    )
    node_b = LeadTimeNode(
        node_id="N_B",
        node_type=ApparelNodeType.SEWING,
        participant_id=pid,
        duration_estimate=dur,
    )
    edge = LeadTimeEdge(
        edge_id="e_AB",
        from_node_id="N_A",
        to_node_id="N_B",
        dependency_type=DependencyType.FINISH_TO_START,
        lag_days=0,
        is_hard_dependency=True,
    )
    graph = LeadTimeGraph(
        graph_id="g_test",
        order_id="TEST",
        nodes=[node_a, node_b],
        edges=[edge],
    )
    resolver = DependencyResolver()
    resolver.resolve(graph, date(2026, 1, 5), None)
    return graph


class TestPathEnumerator:

    def setup_method(self):
        self.enumerator = PathEnumerator()
        self.engine = LeadTimeGraphEngine()

    def test_no_participants_returns_empty(self):
        """Graph with no participant_ids set on any node returns []."""
        dur = DurationEstimate(
            p50_days=5.0, p80_days=7.0, p90_days=10.0,
            min_days=3.0, max_days=15.0, confidence=0.5,
        )
        node = LeadTimeNode(
            node_id="N1",
            node_type=ApparelNodeType.CUTTING,
            participant_id=None,
            duration_estimate=dur,
        )
        graph = LeadTimeGraph(
            graph_id="g_test",
            order_id="TEST",
            nodes=[node],
            edges=[],
        )
        from gltg.graph.dependency_resolver import DependencyResolver
        DependencyResolver().resolve(graph, date(2026, 1, 5), None)

        options = self.enumerator.enumerate(graph)
        assert options == []

    def test_one_participant_returns_one_option(self):
        """Graph with one participant_id on all nodes -> exactly one option returned."""
        graph = _make_resolved_graph_with_participant("P1")
        options = self.enumerator.enumerate(graph)
        assert len(options) == 1

    def test_option_has_critical_path(self):
        """Returned option should have a non-empty critical_path list."""
        graph = _make_resolved_graph_with_participant("P1")
        options = self.enumerator.enumerate(graph)
        assert len(options) >= 1
        assert len(options[0].critical_path) >= 1

    def test_option_has_commitable_date(self):
        """Returned option's commitable_date should not be None."""
        graph = _make_resolved_graph_with_participant("P1")
        options = self.enumerator.enumerate(graph)
        assert len(options) >= 1
        assert options[0].commitable_date is not None

    def test_via_engine_full_flow(self):
        """PathEnumerator via full engine: with one participant produces at least one option."""
        p = make_participant("P1")
        order = make_order(participants=[p], requested_date=date(2026, 12, 31))
        graph = self.engine.build_graph(order)
        options = self.enumerator.enumerate(graph)
        # With one participant assigned, should get one option
        assert len(options) >= 1
