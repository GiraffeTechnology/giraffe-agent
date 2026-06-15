"""Maps an ApparelOrderInput into a list of LeadTimeNode objects."""

from __future__ import annotations

import uuid
from datetime import datetime

from ..models.enums import ApparelNodeType, ConfidenceLevel, EvidenceSourceType
from ..models.evidence import EvidenceItem
from ..models.node import LeadTimeNode
from ..models.order import ApparelOrderInput
from ..models.participant import ParticipantProfile
from .baselines import get_baseline
from .workflow_templates import ApparelWorkflowTemplate


def _short_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


class ApparelOrderMapper:
    """Converts an ApparelOrderInput to a list of LeadTimeNode objects.

    Duration estimates are populated from baselines at this stage;
    the estimation submodule refines them with evidence.
    """

    def __init__(self) -> None:
        self._template = ApparelWorkflowTemplate()

    def map(self, order: ApparelOrderInput) -> list[LeadTimeNode]:
        """Return ordered LeadTimeNode list for the order."""
        node_specs = self._template.get_nodes_for_order(order)
        nodes: list[LeadTimeNode] = []

        for spec in node_specs:
            node_type: ApparelNodeType = spec["node_type"]
            baseline = get_baseline(node_type, order.quantity)

            # Find best participant for this node type
            participant = self._find_participant(order, node_type)

            # Baseline evidence item
            evidence = EvidenceItem(
                evidence_id=_short_id("ev"),
                source_type=EvidenceSourceType.CATEGORY_BASELINE,
                description=f"Category baseline for {node_type.value}",
                value=baseline,
                confidence=0.4,
                created_at=datetime.utcnow(),
            )

            from ..models.duration import DurationEstimate

            duration = DurationEstimate(
                p50_days=baseline["p50"],
                p80_days=baseline["p80"],
                p90_days=baseline["p90"],
                min_days=baseline["min"],
                max_days=baseline["max"],
                confidence=0.4,
                evidence_summary=[evidence],
            )

            node = LeadTimeNode(
                node_id=_short_id("node"),
                node_type=node_type,
                label=node_type.value.replace("_", " ").title(),
                participant_id=participant.participant_id if participant else None,
                required_inputs=list(spec.get("required_inputs", [])),
                outputs=list(spec.get("outputs", [])),
                duration_estimate=duration,
                confidence_level=ConfidenceLevel.LOW,
                evidence=[evidence],
                metadata={"order_id": order.order_id},
            )
            nodes.append(node)

        return nodes

    def _find_participant(
        self, order: ApparelOrderInput, node_type: ApparelNodeType
    ) -> ParticipantProfile | None:
        """Return the first participant that can handle this node type."""
        for p in order.participants:
            if p.can_handle(node_type):
                return p
        return None
