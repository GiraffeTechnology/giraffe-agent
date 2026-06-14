"""Generates DeliveryPathOption objects from a resolved LeadTimeGraph."""

from __future__ import annotations

import uuid
from datetime import date

from ..models.enums import DeliveryMode, OptionStatus
from ..models.graph import LeadTimeGraph
from ..models.path import DeliveryPathOption
from ..graph.critical_path import CriticalPathFinder


class PathEnumerator:
    """Enumerates delivery path options from a resolved graph."""

    def __init__(self) -> None:
        self._cp_finder = CriticalPathFinder()

    def enumerate(self, graph: LeadTimeGraph) -> list[DeliveryPathOption]:
        """Generate at least one DeliveryPathOption from the graph.

        Returns a list of options (currently one per participant combination).
        """
        if not graph.nodes:
            return []

        critical_path = self._cp_finder.find(graph)
        bottlenecks = self._cp_finder.find_bottlenecks(graph, critical_path)

        # Determine terminal node dates
        terminal_node = self._find_terminal_node(graph)
        if terminal_node is None:
            return []

        earliest = terminal_node.earliest_finish
        most_likely = terminal_node.most_likely_finish
        commitable = terminal_node.commitable_finish
        risk_adj = terminal_node.risk_adjusted_finish

        # Determine status
        status = OptionStatus.FEASIBLE
        infeasibility_reason: str | None = None

        # Collect unique participants from nodes
        participant_ids = list({
            n.participant_id for n in graph.nodes if n.participant_id
        })

        # No participants assigned → no real option can be generated
        if not participant_ids:
            return []

        # Collect all evidence from nodes
        all_evidence = []
        for node in graph.nodes:
            all_evidence.extend(node.evidence)

        option = DeliveryPathOption(
            option_id=f"opt_{uuid.uuid4().hex[:8]}",
            status=status,
            delivery_mode=DeliveryMode.FULL_DELIVERY,
            participant_combination=participant_ids,
            nodes=list(graph.nodes),
            edges=list(graph.edges),
            earliest_feasible_date=earliest,
            most_likely_date=most_likely,
            commitable_date=commitable,
            risk_adjusted_latest_date=risk_adj,
            critical_path=critical_path,
            bottleneck_nodes=bottlenecks,
            risk_flags=[rf for node in graph.nodes for rf in node.risk_flags],
            evidence_summary=all_evidence[:20],  # keep manageable
            infeasibility_reason=infeasibility_reason,
        )

        return [option]

    def _find_terminal_node(self, graph):
        """Return the node with no successors that has the latest commitable finish."""
        has_successor = {e.from_node_id for e in graph.edges}
        terminals = [n for n in graph.nodes if n.node_id not in has_successor]
        if not terminals:
            # Fall back to the last node
            return graph.nodes[-1] if graph.nodes else None
        # Pick the one with the latest commitable finish
        return max(
            terminals,
            key=lambda n: n.commitable_finish or date.min,
        )
