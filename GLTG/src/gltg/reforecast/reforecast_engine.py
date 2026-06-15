"""Reforecast engine -- re-evaluates an order after progress events."""

from __future__ import annotations

from datetime import datetime, date

from ..models.packet import DeliveryFeasibilityPacket
from ..models.reforecast import ProgressEvent, ReforecastResult
from .event_applier import EventApplier
from .expedite_options import ExpediteOptionGenerator


class ReforecastEngine:
    """Re-evaluates a DeliveryFeasibilityPacket given new progress events."""

    def __init__(self) -> None:
        self._applier = EventApplier()
        self._expedite = ExpediteOptionGenerator()

    def reforecast(
        self,
        packet: DeliveryFeasibilityPacket,
        events: list[ProgressEvent],
    ) -> DeliveryFeasibilityPacket:
        """Apply events to the packet's options and return an updated packet.

        Event-applied dates are used as ANCHORS during re-resolve so that
        node-level mutations (delay shifts, completion dates) are not discarded
        when the dependency graph is re-propagated forward.
        """
        if not packet.options or not events:
            return packet

        all_changed: set[str] = set()
        previous_commitable = packet.commitable_date

        for option in packet.options:
            from ..models.graph import LeadTimeGraph
            temp_graph = LeadTimeGraph(
                graph_id="reforecast_temp",
                order_id=packet.order_id,
                nodes=list(option.nodes),
                edges=list(option.edges),
            )

            # Record commitable_finish BEFORE event application so we can
            # use post-event dates as floors during re-resolve.
            pre_cf = {
                n.node_id: n.commitable_finish
                for n in temp_graph.nodes
                if n.commitable_finish is not None
            }

            for event in events:
                changed = self._applier.apply(temp_graph, event)
                all_changed.update(changed)

            # Build anchor map: for nodes that EventApplier mutated,
            # use their post-event commitable_finish as a floor so the
            # forward-pass resolver propagates the real (delayed) date
            # rather than overwriting it with baseline durations.
            node_finish_floors: dict[str, date] = {}
            for nid in all_changed:
                node = temp_graph.get_node(nid)
                if node and node.commitable_finish is not None:
                    pre = pre_cf.get(nid)
                    # Use floor only if the event actually shifted the date
                    if pre is None or node.commitable_finish != pre:
                        node_finish_floors[nid] = node.commitable_finish

            from ..graph.dependency_resolver import DependencyResolver
            from ..graph.critical_path import CriticalPathFinder

            resolver = DependencyResolver()
            cp_finder = CriticalPathFinder()

            # Use a start date that respects already-completed work.
            # The node_finish_floors anchors the re-resolve to event dates.
            start = date.today()
            resolver.resolve(temp_graph, start, None, node_finish_floors=node_finish_floors)

            new_critical = cp_finder.find(temp_graph)
            new_bottlenecks = cp_finder.find_bottlenecks(temp_graph, new_critical)

            option.nodes = temp_graph.nodes
            option.edges = temp_graph.edges
            option.critical_path = new_critical
            option.bottleneck_nodes = new_bottlenecks

            has_successor = {e.from_node_id for e in temp_graph.edges}
            terminals = [n for n in temp_graph.nodes if n.node_id not in has_successor]
            if terminals:
                terminal = max(terminals, key=lambda n: n.commitable_finish or date.min)
                option.commitable_date = terminal.commitable_finish
                option.most_likely_date = terminal.most_likely_finish
                option.earliest_feasible_date = terminal.earliest_finish
                option.risk_adjusted_latest_date = terminal.risk_adjusted_finish

        best = packet.options[0]
        new_commitable = best.commitable_date

        delta_days: int | None = None
        if previous_commitable and new_commitable:
            delta_days = (new_commitable - previous_commitable).days

        acceleration = []
        if delta_days and delta_days > 0:
            acceleration = self._expedite.generate(days_needed_to_save=delta_days)

        critical_path_changed = (best.critical_path != packet.critical_path)

        new_flags = []
        if delta_days and delta_days > 7:
            from ..models.enums import RiskFlagCode
            from ..models.risk import RiskFlag
            new_flags.append(RiskFlag(
                code=RiskFlagCode.TIGHT_DEADLINE,
                description=f"Reforecast shows {delta_days} day delay vs original commitment.",
                severity="HIGH",
                mitigation_hint="Consider expedite options.",
            ))

        packet.commitable_date = new_commitable
        packet.most_likely_date = best.most_likely_date
        packet.earliest_feasible_date = best.earliest_feasible_date
        packet.risk_adjusted_latest_date = best.risk_adjusted_latest_date
        packet.critical_path = best.critical_path
        packet.bottleneck_nodes = best.bottleneck_nodes
        packet.risk_flags = packet.risk_flags + new_flags
        packet.acceleration_options = acceleration
        packet.generated_at = datetime.utcnow()

        return packet

    def build_reforecast_result(
        self,
        order_id: str,
        previous_commitable: date | None,
        new_commitable: date | None,
        changed_nodes: list[str],
        critical_path_changed: bool,
        new_risk_flags,
        acceleration_options: list[dict],
    ) -> ReforecastResult:
        delta = None
        if previous_commitable and new_commitable:
            delta = (new_commitable - previous_commitable).days

        return ReforecastResult(
            order_id=order_id,
            reforecast_at=datetime.utcnow(),
            previous_commitable_date=previous_commitable,
            new_commitable_date=new_commitable,
            delta_days=delta,
            changed_nodes=changed_nodes,
            critical_path_changed=critical_path_changed,
            new_risk_flags=new_risk_flags,
            acceleration_options=acceleration_options,
        )
