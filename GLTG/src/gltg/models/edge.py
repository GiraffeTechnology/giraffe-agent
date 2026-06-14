"""LeadTimeEdge model representing a dependency between two nodes."""

from __future__ import annotations

from pydantic import BaseModel

from .enums import DependencyType


class LeadTimeEdge(BaseModel):
    """A directed dependency edge between two workflow nodes."""

    edge_id: str
    from_node_id: str
    to_node_id: str
    dependency_type: DependencyType = DependencyType.FINISH_TO_START
    lag_days: int = 0
    is_hard_dependency: bool = True
    condition: str | None = None
