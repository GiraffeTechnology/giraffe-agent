"""GraphBuilder -- wires nodes into a LeadTimeGraph with appropriate edges."""

from __future__ import annotations

import uuid

from ..models.edge import LeadTimeEdge
from ..models.enums import ApparelNodeType, DependencyType
from ..models.graph import LeadTimeGraph
from ..models.node import LeadTimeNode
from ..models.order import ApparelOrderInput

# Apparel workflow dependency rules:
# Each entry: (from_type, to_type, dependency_type, lag_days, is_hard)
APPAREL_EDGE_RULES: list[tuple[ApparelNodeType, ApparelNodeType, DependencyType, int, bool]] = [
    (ApparelNodeType.BUYER_REQUIREMENT_CONFIRMATION, ApparelNodeType.DESIGN_OR_TECH_PACK_CONFIRMATION, DependencyType.FINISH_TO_START, 0, True),
    (ApparelNodeType.DESIGN_OR_TECH_PACK_CONFIRMATION, ApparelNodeType.FABRIC_SELECTION, DependencyType.FINISH_TO_START, 0, True),
    (ApparelNodeType.DESIGN_OR_TECH_PACK_CONFIRMATION, ApparelNodeType.TRIM_SELECTION, DependencyType.FINISH_TO_START, 0, True),
    (ApparelNodeType.DESIGN_OR_TECH_PACK_CONFIRMATION, ApparelNodeType.SAMPLE_MAKING, DependencyType.FINISH_TO_START, 0, True),
    (ApparelNodeType.DESIGN_OR_TECH_PACK_CONFIRMATION, ApparelNodeType.PACKAGING_MATERIAL_CONFIRMATION, DependencyType.FINISH_TO_START, 0, False),
    (ApparelNodeType.FABRIC_SELECTION, ApparelNodeType.FABRIC_AVAILABILITY_CONFIRMATION, DependencyType.FINISH_TO_START, 0, True),
    (ApparelNodeType.FABRIC_AVAILABILITY_CONFIRMATION, ApparelNodeType.FABRIC_ORDERING, DependencyType.FINISH_TO_START, 0, True),
    (ApparelNodeType.FABRIC_ORDERING, ApparelNodeType.FABRIC_DYEING_OR_PRINTING, DependencyType.MATERIAL_READY_BEFORE_START, 0, False),
    (ApparelNodeType.FABRIC_ORDERING, ApparelNodeType.FABRIC_FINISHING, DependencyType.MATERIAL_READY_BEFORE_START, 0, False),
    (ApparelNodeType.FABRIC_DYEING_OR_PRINTING, ApparelNodeType.FABRIC_FINISHING, DependencyType.FINISH_TO_START, 0, False),
    (ApparelNodeType.FABRIC_FINISHING, ApparelNodeType.FABRIC_TESTING, DependencyType.FINISH_TO_START, 0, False),
    (ApparelNodeType.FABRIC_ORDERING, ApparelNodeType.FABRIC_TESTING, DependencyType.MATERIAL_READY_BEFORE_START, 0, False),
    (ApparelNodeType.FABRIC_TESTING, ApparelNodeType.CUTTING, DependencyType.APPROVAL_READY_BEFORE_START, 0, True),
    (ApparelNodeType.FABRIC_ORDERING, ApparelNodeType.CUTTING, DependencyType.MATERIAL_READY_BEFORE_START, 0, True),
    (ApparelNodeType.TRIM_SELECTION, ApparelNodeType.TRIM_AVAILABILITY_CONFIRMATION, DependencyType.FINISH_TO_START, 0, True),
    (ApparelNodeType.TRIM_AVAILABILITY_CONFIRMATION, ApparelNodeType.TRIM_ORDERING, DependencyType.FINISH_TO_START, 0, True),
    (ApparelNodeType.TRIM_ORDERING, ApparelNodeType.SEWING, DependencyType.MATERIAL_READY_BEFORE_START, 0, True),
    (ApparelNodeType.SAMPLE_MAKING, ApparelNodeType.SAMPLE_APPROVAL, DependencyType.FINISH_TO_START, 0, True),
    (ApparelNodeType.SAMPLE_APPROVAL, ApparelNodeType.PP_SAMPLE_APPROVAL, DependencyType.FINISH_TO_START, 0, False),
    (ApparelNodeType.SAMPLE_APPROVAL, ApparelNodeType.PRODUCTION_SLOT_BOOKING, DependencyType.APPROVAL_READY_BEFORE_START, 0, True),
    (ApparelNodeType.SAMPLE_APPROVAL, ApparelNodeType.LOGISTICS_BOOKING, DependencyType.APPROVAL_READY_BEFORE_START, 0, False),
    (ApparelNodeType.PP_SAMPLE_APPROVAL, ApparelNodeType.CUTTING, DependencyType.APPROVAL_READY_BEFORE_START, 0, False),
    (ApparelNodeType.PRODUCTION_SLOT_BOOKING, ApparelNodeType.CUTTING, DependencyType.CAPACITY_SLOT_REQUIRED, 0, True),
    (ApparelNodeType.CUTTING, ApparelNodeType.SEWING, DependencyType.FINISH_TO_START, 0, True),
    (ApparelNodeType.SEWING, ApparelNodeType.WASHING_OR_FINISHING, DependencyType.FINISH_TO_START, 0, False),
    (ApparelNodeType.SEWING, ApparelNodeType.INLINE_QC, DependencyType.START_TO_START, 1, False),
    (ApparelNodeType.SEWING, ApparelNodeType.FINAL_QC, DependencyType.FINISH_TO_START, 0, True),
    (ApparelNodeType.WASHING_OR_FINISHING, ApparelNodeType.FINAL_QC, DependencyType.FINISH_TO_START, 0, False),
    (ApparelNodeType.FINAL_QC, ApparelNodeType.REWORK_IF_NEEDED, DependencyType.CONDITIONAL, 0, False),
    (ApparelNodeType.FINAL_QC, ApparelNodeType.PACKING, DependencyType.FINISH_TO_START, 0, True),
    (ApparelNodeType.REWORK_IF_NEEDED, ApparelNodeType.PACKING, DependencyType.CONDITIONAL, 0, False),
    (ApparelNodeType.PACKAGING_MATERIAL_CONFIRMATION, ApparelNodeType.PACKING, DependencyType.MATERIAL_READY_BEFORE_START, 0, True),
    (ApparelNodeType.PACKING, ApparelNodeType.CUSTOMS_OR_EXPORT_DOCS, DependencyType.FINISH_TO_START, 0, True),
    (ApparelNodeType.CUSTOMS_OR_EXPORT_DOCS, ApparelNodeType.SHIPMENT, DependencyType.FINISH_TO_START, 0, True),
    (ApparelNodeType.LOGISTICS_BOOKING, ApparelNodeType.SHIPMENT, DependencyType.CAPACITY_SLOT_REQUIRED, 0, True),
    (ApparelNodeType.SHIPMENT, ApparelNodeType.BUYER_RECEIPT, DependencyType.FINISH_TO_START, 0, True),
    (ApparelNodeType.BUYER_RECEIPT, ApparelNodeType.BUYER_SIGN_OFF, DependencyType.FINISH_TO_START, 0, False),
]


class GraphBuilder:
    """Builds a LeadTimeGraph from an order and its resolved nodes."""

    def build(self, order: ApparelOrderInput, nodes: list[LeadTimeNode]) -> LeadTimeGraph:
        """Create graph with edges derived from workflow dependency rules."""
        graph_id = f"g_{uuid.uuid4().hex[:12]}"

        # Index nodes by type (take the first if duplicates)
        type_to_node: dict[ApparelNodeType, LeadTimeNode] = {}
        for node in nodes:
            if node.node_type not in type_to_node:
                type_to_node[node.node_type] = node

        edges: list[LeadTimeEdge] = []
        for from_type, to_type, dep_type, lag, is_hard in APPAREL_EDGE_RULES:
            from_node = type_to_node.get(from_type)
            to_node = type_to_node.get(to_type)
            if from_node and to_node:
                edge = LeadTimeEdge(
                    edge_id=f"e_{uuid.uuid4().hex[:8]}",
                    from_node_id=from_node.node_id,
                    to_node_id=to_node.node_id,
                    dependency_type=dep_type,
                    lag_days=lag,
                    is_hard_dependency=is_hard,
                )
                edges.append(edge)

        return LeadTimeGraph(
            graph_id=graph_id,
            order_id=order.order_id,
            nodes=list(nodes),
            edges=edges,
            metadata={"product_type": order.product_type, "quantity": order.quantity},
        )
