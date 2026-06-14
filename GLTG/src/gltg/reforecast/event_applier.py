"""Applies progress events to modify node states in a graph."""

from __future__ import annotations

from ..models.enums import NodeStatus, ProgressEventType
from ..models.graph import LeadTimeGraph
from ..models.reforecast import ProgressEvent


class EventApplier:
    """Mutates graph nodes based on incoming progress events."""

    def apply(self, graph: LeadTimeGraph, event: ProgressEvent) -> list[str]:
        """Apply a single ProgressEvent to the graph.

        Returns list of node_ids that were changed.
        """
        changed: list[str] = []
        node_id = event.node_id

        if node_id:
            node = graph.get_node(node_id)
            if node:
                self._apply_to_node(node, event)
                changed.append(node_id)
        else:
            # Order-level event — may affect multiple nodes
            changed.extend(self._apply_order_level(graph, event))

        return changed

    def _apply_to_node(self, node, event: ProgressEvent) -> None:
        """Mutate a specific node based on event type."""
        etype = event.event_type
        payload = event.payload

        if etype == ProgressEventType.NODE_COMPLETED:
            node.status = NodeStatus.COMPLETED
            if "completion_date" in payload:
                from datetime import date
                cd = payload["completion_date"]
                if isinstance(cd, str):
                    cd = date.fromisoformat(cd)
                node.earliest_finish = cd
                node.most_likely_finish = cd
                node.commitable_finish = cd

        elif etype == ProgressEventType.NODE_STARTED:
            node.status = NodeStatus.IN_PROGRESS
            if "start_date" in payload:
                from datetime import date
                sd = payload["start_date"]
                if isinstance(sd, str):
                    sd = date.fromisoformat(sd)
                node.earliest_start = sd

        elif etype in (
            ProgressEventType.MATERIAL_DELAYED,
            ProgressEventType.TRIM_DELAYED,
            ProgressEventType.SAMPLE_APPROVAL_DELAYED,
            ProgressEventType.LOGISTICS_DELAYED,
            ProgressEventType.BUYER_APPROVAL_DELAYED,
        ):
            node.status = NodeStatus.BLOCKED
            delay_days = payload.get("delay_days", 0)
            if delay_days and node.commitable_finish:
                from datetime import timedelta
                node.commitable_finish = node.commitable_finish + timedelta(days=delay_days)
                node.most_likely_finish = (
                    node.most_likely_finish + timedelta(days=delay_days)
                    if node.most_likely_finish else node.commitable_finish
                )
                node.risk_adjusted_finish = (
                    node.risk_adjusted_finish + timedelta(days=int(delay_days * 1.2))
                    if node.risk_adjusted_finish else None
                )

        elif etype == ProgressEventType.QC_FAILED:
            node.status = NodeStatus.BLOCKED
            # Add rework buffer to duration
            rework_days = payload.get("expected_rework_days", 5)
            if node.duration_estimate:
                node.duration_estimate.p50_days += rework_days
                node.duration_estimate.p80_days += rework_days * 1.4
                node.duration_estimate.p90_days += rework_days * 2.0

        elif etype in (ProgressEventType.REWORK_STARTED, ProgressEventType.REWORK_COMPLETED):
            if etype == ProgressEventType.REWORK_COMPLETED:
                node.status = NodeStatus.COMPLETED
            else:
                node.status = NodeStatus.IN_PROGRESS

        elif etype == ProgressEventType.PRODUCTION_PROGRESS_UPDATE:
            pct = payload.get("percent_complete", 0)
            if pct >= 100:
                node.status = NodeStatus.COMPLETED
            elif pct > 0:
                node.status = NodeStatus.IN_PROGRESS
            # Adjust remaining duration
            remaining = payload.get("remaining_days")
            if remaining is not None and node.duration_estimate:
                node.duration_estimate.p50_days = max(0.5, float(remaining))
                node.duration_estimate.p80_days = max(0.5, float(remaining) * 1.3)
                node.duration_estimate.p90_days = max(0.5, float(remaining) * 1.6)

    def _apply_order_level(self, graph: LeadTimeGraph, event: ProgressEvent) -> list[str]:
        """Apply events that affect all pending nodes."""
        changed: list[str] = []
        if event.event_type == ProgressEventType.SUPPLIER_CONFIRMED:
            participant_id = event.payload.get("participant_id")
            if participant_id:
                for node in graph.nodes:
                    if node.participant_id == participant_id and node.status == NodeStatus.PENDING:
                        # Mark as in-progress or update dates
                        confirmed_days = event.payload.get("confirmed_days")
                        if confirmed_days and node.duration_estimate:
                            node.duration_estimate.supplier_claim_days = float(confirmed_days)
                        changed.append(node.node_id)
        return changed
