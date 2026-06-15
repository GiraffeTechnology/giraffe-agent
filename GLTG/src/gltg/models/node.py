"""LeadTimeNode model representing a single workflow step in the graph."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel

from .enums import ApparelNodeType, ConfidenceLevel, NodeStatus
from .duration import DurationEstimate
from .evidence import EvidenceItem
from .risk import RiskFlag


class LeadTimeNode(BaseModel):
    """A single workflow node in the lead-time graph."""

    node_id: str
    node_type: ApparelNodeType
    label: str | None = None
    participant_id: str | None = None
    required_inputs: list[str] = []
    outputs: list[str] = []
    duration_estimate: DurationEstimate | None = None
    earliest_start: date | None = None
    earliest_finish: date | None = None
    most_likely_finish: date | None = None
    commitable_finish: date | None = None
    risk_adjusted_finish: date | None = None
    confidence_level: ConfidenceLevel = ConfidenceLevel.LOW
    risk_flags: list[RiskFlag] = []
    evidence: list[EvidenceItem] = []
    status: NodeStatus = NodeStatus.PENDING
    is_critical: bool = False
    metadata: dict = {}
