"""Critical path finder using earliest/latest finish dates."""

from __future__ import annotations

from datetime import date

from ..models.graph import LeadTimeGraph


class CriticalPathFinder:
    """Identifies the critical path and bottleneck nodes in a resolved graph."""

    def find(self, graph: LeadTimeGraph) -> list[str]:
        """Return ordered list of node_ids on the critical path.

        Also marks nodes with is_critical=True.

        Strategy: The critical path is the sequence of nodes whose
        commitable_finish forms the longest chain to the project end.
        We use a backward-pass approach after a forward pass has set dates.
        """
        if not graph.nodes:
            return []

        # Build id -> node map
        node_map = {n.node_id: n for n in graph.nodes}

        # Find the terminal node(s) — nodes with no successors
        has_successor = {e.from_node_id for e in graph.edges}
        terminal_ids = [n.node_id for n in graph.nodes if n.node_id not in has_successor]

        if not terminal_ids:
            return []

        # Latest commitable finish of all terminal nodes
        def cf(nid: str) -> date:
            n = node_map.get(nid)
            if n and n.commitable_finish:
                return n.commitable_finish
            return date.min

        project_end_nid = max(terminal_ids, key=cf)

        # Backward trace: from project_end follow the predecessor with latest finish
        critical: list[str] = []
        current_id: str | None = project_end_nid

        visited: set[str] = set()
        while current_id and current_id not in visited:
            visited.add(current_id)
            critical.append(current_id)
            node = node_map.get(current_id)
            if node:
                node.is_critical = True

            predecessors = graph.get_predecessors(current_id)
            if not predecessors:
                break

            # Pick predecessor with the latest commitable_finish (longest path)
            current_id = max(predecessors, key=cf)

        critical.reverse()
        return critical

    def find_bottlenecks(self, graph: LeadTimeGraph, critical_path: list[str]) -> list[str]:
        """Return node_ids that are both on the critical path and have high variance.

        High variance = p90 - p50 > 7 days (a week of uncertainty).
        """
        bottlenecks: list[str] = []
        node_map = {n.node_id: n for n in graph.nodes}
        for nid in critical_path:
            node = node_map.get(nid)
            if node and node.duration_estimate:
                dur = node.duration_estimate
                variance = dur.p90_days - dur.p50_days
                if variance > 7:
                    bottlenecks.append(nid)
        return bottlenecks
