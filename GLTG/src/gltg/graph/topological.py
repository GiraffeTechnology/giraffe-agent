"""Topological sort for the lead-time graph."""

from __future__ import annotations

from collections import defaultdict, deque

from ..errors import CyclicDependencyError
from ..models.edge import LeadTimeEdge
from ..models.node import LeadTimeNode


def topological_sort(
    nodes: list[LeadTimeNode], edges: list[LeadTimeEdge]
) -> list[LeadTimeNode]:
    """Return nodes in topological order (Kahn's algorithm).

    Raises CyclicDependencyError if the graph contains a cycle.
    """
    node_map: dict[str, LeadTimeNode] = {n.node_id: n for n in nodes}
    in_degree: dict[str, int] = {n.node_id: 0 for n in nodes}
    adjacency: dict[str, list[str]] = defaultdict(list)

    for edge in edges:
        if edge.from_node_id in node_map and edge.to_node_id in node_map:
            adjacency[edge.from_node_id].append(edge.to_node_id)
            in_degree[edge.to_node_id] += 1

    queue: deque[str] = deque(
        nid for nid, deg in in_degree.items() if deg == 0
    )
    result: list[LeadTimeNode] = []

    while queue:
        nid = queue.popleft()
        result.append(node_map[nid])
        for successor in adjacency[nid]:
            in_degree[successor] -= 1
            if in_degree[successor] == 0:
                queue.append(successor)

    if len(result) != len(nodes):
        # Identify nodes still in cycle
        cycle_nodes = [nid for nid, deg in in_degree.items() if deg > 0]
        raise CyclicDependencyError(cycle=cycle_nodes)

    return result
