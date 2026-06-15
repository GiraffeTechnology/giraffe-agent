"""Integration tests: ApparelOrderInput -> LeadTimeGraph."""

from __future__ import annotations

from datetime import date

import pytest

from gltg import LeadTimeGraphEngine, ApparelOrderInput
from gltg.models.enums import ParticipantType

from tests.conftest import make_participant, make_order


@pytest.fixture
def engine():
    return LeadTimeGraphEngine()


@pytest.fixture
def order_with_participants():
    participants = [
        make_participant("P1"),
        make_participant("P2"),
    ]
    return make_order(
        order_id="INT-001",
        quantity=2000,
        participants=participants,
        requested_date=date(2026, 12, 31),
    )


class TestApparelOrderToGraph:

    def test_order_produces_graph(self, engine, order_with_participants):
        """ApparelOrderInput with participants -> build_graph returns a LeadTimeGraph with nodes."""
        graph = engine.build_graph(order_with_participants)
        assert graph is not None
        assert len(graph.nodes) > 0

    def test_graph_has_edges(self, engine, order_with_participants):
        """The built graph should have edges connecting nodes."""
        graph = engine.build_graph(order_with_participants)
        assert len(graph.edges) > 0

    def test_all_nodes_have_duration(self, engine, order_with_participants):
        """All nodes must have a duration_estimate with p50/p80/p90 set."""
        graph = engine.build_graph(order_with_participants)
        for node in graph.nodes:
            assert node.duration_estimate is not None, f"Node {node.node_id} missing duration"
            assert node.duration_estimate.p50_days > 0
            assert node.duration_estimate.p80_days >= node.duration_estimate.p50_days
            assert node.duration_estimate.p90_days >= node.duration_estimate.p80_days

    def test_nodes_have_dates(self, engine, order_with_participants):
        """After build_graph (which calls resolve), all nodes should have earliest_finish set."""
        graph = engine.build_graph(order_with_participants)
        for node in graph.nodes:
            assert node.earliest_finish is not None, f"Node {node.node_id} missing earliest_finish"

    def test_critical_path_nonempty(self, engine, order_with_participants):
        """graph.metadata['critical_path'] should be non-empty after build_graph."""
        graph = engine.build_graph(order_with_participants)
        critical = graph.metadata.get("critical_path", [])
        assert len(critical) > 0

    def test_graph_order_id_matches_input(self, engine, order_with_participants):
        """Graph's order_id should match the input order's order_id."""
        graph = engine.build_graph(order_with_participants)
        assert graph.order_id == order_with_participants.order_id

    def test_node_ids_are_unique(self, engine, order_with_participants):
        """All node IDs in the graph must be unique."""
        graph = engine.build_graph(order_with_participants)
        node_ids = [n.node_id for n in graph.nodes]
        assert len(node_ids) == len(set(node_ids))

    def test_graph_without_participants_still_has_nodes(self, engine):
        """Even with no participants, the graph should be built with nodes (no participants assigned)."""
        order = make_order(participants=[])
        graph = engine.build_graph(order)
        assert graph is not None
        assert len(graph.nodes) > 0

    def test_quantity_reflected_in_metadata(self, engine, order_with_participants):
        """Graph metadata should record the order quantity."""
        graph = engine.build_graph(order_with_participants)
        assert graph.metadata.get("quantity") == order_with_participants.quantity
