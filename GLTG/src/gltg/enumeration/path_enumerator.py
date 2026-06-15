"""Generates DeliveryPathOption objects from a resolved LeadTimeGraph."""

from __future__ import annotations

import uuid
from datetime import date

from ..models.enums import ApparelNodeType, DeliveryMode, OptionStatus, ParticipantType
from ..models.graph import LeadTimeGraph
from ..models.order import ApparelOrderInput
from ..models.path import DeliveryPathOption
from ..graph.critical_path import CriticalPathFinder

# Node types that identify a garment factory as the primary manufacturer
_FACTORY_NODE_TYPES: frozenset[ApparelNodeType] = frozenset({
    ApparelNodeType.CUTTING,
    ApparelNodeType.SEWING,
    ApparelNodeType.WASHING_OR_FINISHING,
    ApparelNodeType.PACKING,
    ApparelNodeType.SAMPLE_MAKING,
    ApparelNodeType.INLINE_QC,
})

# Participant types that are garment factories
_FACTORY_PARTICIPANT_TYPES: frozenset[ParticipantType] = frozenset({
    ParticipantType.GARMENT_FACTORY,
})


def _is_factory_participant(p) -> bool:
    """Return True if the participant is a garment factory (by type or capabilities)."""
    if p.participant_type in _FACTORY_PARTICIPANT_TYPES:
        return True
    return any(c.node_type in _FACTORY_NODE_TYPES for c in p.capabilities)


class PathEnumerator:
    """Generates one DeliveryPathOption per factory participant combination."""

    def __init__(self) -> None:
        self._cp_finder = CriticalPathFinder()

    def enumerate(
        self,
        graph: LeadTimeGraph,
        order_input: ApparelOrderInput | None = None,
    ) -> list[DeliveryPathOption]:
        """Generate options from the resolved graph.

        Strategy:
        - When order_input is provided, identify factory participants from
          order_input.participants (by type or capability) — this correctly
          enumerates all alternative factories even when the graph was built
          using only the first available participant per node type.
        - Generate one DeliveryPathOption per factory (up to 3).
        - Support participants (non-factory) are included in every option.
        - If no factory participants exist but others do, return a single generic
          option with all participants.
        - If no participants at all, return [].
        """
        if not graph.nodes:
            return []

        critical_path = self._cp_finder.find(graph)
        bottlenecks = self._cp_finder.find_bottlenecks(graph, critical_path)
        terminal_node = self._find_terminal_node(graph)
        if terminal_node is None:
            return []

        # Prefer order_input participants for accurate factory enumeration
        if order_input and order_input.participants:
            return self._enumerate_from_order(
                graph, critical_path, bottlenecks, terminal_node, order_input
            )

        # Fallback: derive participants from graph node assignments
        return self._enumerate_from_graph(
            graph, critical_path, bottlenecks, terminal_node
        )

    def _enumerate_from_order(
        self,
        graph: LeadTimeGraph,
        critical_path: list[str],
        bottlenecks: list[str],
        terminal_node,
        order_input: ApparelOrderInput,
    ) -> list[DeliveryPathOption]:
        """Enumerate options using participant definitions from the order."""
        factory_participants = [
            p for p in order_input.participants if _is_factory_participant(p)
        ]
        support_participants = [
            p for p in order_input.participants if not _is_factory_participant(p)
        ]
        support_pids = [p.participant_id for p in support_participants]

        if not factory_participants:
            # No factories but other participants → single generic option
            all_pids = [p.participant_id for p in order_input.participants]
            if not all_pids:
                return []
            return [self._create_option(
                graph, critical_path, bottlenecks, terminal_node,
                participant_combination=all_pids,
            )]

        options: list[DeliveryPathOption] = []
        for factory in factory_participants[:3]:
            combination = [factory.participant_id] + support_pids
            options.append(self._create_option(
                graph, critical_path, bottlenecks, terminal_node,
                participant_combination=combination,
            ))
        return options

    def _enumerate_from_graph(
        self,
        graph: LeadTimeGraph,
        critical_path: list[str],
        bottlenecks: list[str],
        terminal_node,
    ) -> list[DeliveryPathOption]:
        """Fallback: derive factory participants from graph node assignments."""
        all_assigned_pids = {n.participant_id for n in graph.nodes if n.participant_id}
        if not all_assigned_pids:
            return []

        factory_pids: list[str] = list({
            n.participant_id
            for n in graph.nodes
            if n.participant_id and n.node_type in _FACTORY_NODE_TYPES
        })
        support_pids = [p for p in all_assigned_pids if p not in factory_pids]

        if not factory_pids:
            return [self._create_option(
                graph, critical_path, bottlenecks, terminal_node,
                participant_combination=list(all_assigned_pids),
            )]

        options: list[DeliveryPathOption] = []
        for fac_pid in factory_pids[:3]:
            combination = [fac_pid] + support_pids
            options.append(self._create_option(
                graph, critical_path, bottlenecks, terminal_node,
                participant_combination=combination,
            ))
        return options

    def _create_option(
        self,
        graph: LeadTimeGraph,
        critical_path: list[str],
        bottlenecks: list[str],
        terminal_node,
        participant_combination: list[str],
    ) -> DeliveryPathOption:
        earliest = terminal_node.earliest_finish
        most_likely = terminal_node.most_likely_finish
        commitable = terminal_node.commitable_finish
        risk_adj = terminal_node.risk_adjusted_finish

        all_evidence = []
        for node in graph.nodes:
            all_evidence.extend(node.evidence)

        all_risk_flags = [rf for node in graph.nodes for rf in node.risk_flags]

        return DeliveryPathOption(
            option_id=f"opt_{uuid.uuid4().hex[:8]}",
            status=OptionStatus.FEASIBLE,
            delivery_mode=DeliveryMode.FULL_DELIVERY,
            participant_combination=participant_combination,
            nodes=list(graph.nodes),
            edges=list(graph.edges),
            earliest_feasible_date=earliest,
            most_likely_date=most_likely,
            commitable_date=commitable,
            risk_adjusted_latest_date=risk_adj,
            critical_path=critical_path,
            bottleneck_nodes=bottlenecks,
            risk_flags=all_risk_flags,
            evidence_summary=all_evidence[:20],
        )

    def _find_terminal_node(self, graph: LeadTimeGraph):
        """Return the node with no successors that has the latest commitable finish."""
        has_successor = {e.from_node_id for e in graph.edges}
        terminals = [n for n in graph.nodes if n.node_id not in has_successor]
        if not terminals:
            return graph.nodes[-1] if graph.nodes else None
        return max(
            terminals,
            key=lambda n: n.commitable_finish or date.min,
        )
