"""LeadTimeGraph model -- the container for the full order graph."""

from __future__ import annotations

from pydantic import BaseModel

from .node import LeadTimeNode
from .edge import LeadTimeEdge


class LeadTimeGraph(BaseModel):
    """The complete lead-time graph for an order."""

    graph_id: str
    order_id: str
    nodes: list[LeadTimeNode] = []
    edges: list[LeadTimeEdge] = []
    metadata: dict = {}

    def get_node(self, node_id: str) -> LeadTimeNode | None:
        """Return the node with the given id, or None."""
        for n in self.nodes:
            if n.node_id == node_id:
                return n
        return None

    def get_predecessors(self, node_id: str) -> list[str]:
        """Return node_ids that must finish before node_id can start."""
        return [e.from_node_id for e in self.edges if e.to_node_id == node_id]

    def get_successors(self, node_id: str) -> list[str]:
        """Return node_ids that depend on node_id."""
        return [e.to_node_id for e in self.edges if e.from_node_id == node_id]

    def get_edges_to(self, node_id: str) -> list[LeadTimeEdge]:
        """Return all edges whose to_node_id matches."""
        return [e for e in self.edges if e.to_node_id == node_id]

    def get_edges_from(self, node_id: str) -> list[LeadTimeEdge]:
        """Return all edges whose from_node_id matches."""
        return [e for e in self.edges if e.from_node_id == node_id]
