"""DeliveryPathOption -- one possible delivery scenario."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel

from .enums import DeliveryMode, OptionLabel, OptionStatus
from .node import LeadTimeNode
from .edge import LeadTimeEdge
from .risk import RiskFlag
from .evidence import EvidenceItem


class DeliveryPathOption(BaseModel):
    """A candidate delivery path with full date/risk/evidence breakdown."""

    option_id: str
    status: OptionStatus = OptionStatus.FEASIBLE
    label: OptionLabel | None = None
    delivery_mode: DeliveryMode = DeliveryMode.FULL_DELIVERY
    participant_combination: list[str] = []   # participant_ids involved
    nodes: list[LeadTimeNode] = []
    edges: list[LeadTimeEdge] = []
    earliest_feasible_date: date | None = None
    most_likely_date: date | None = None
    commitable_date: date | None = None
    risk_adjusted_latest_date: date | None = None
    on_time_probability: float | None = None  # 0.0-1.0
    critical_path: list[str] = []             # ordered node_ids
    bottleneck_nodes: list[str] = []
    risk_flags: list[RiskFlag] = []
    missing_fields: list[str] = []
    score: float | None = None
    recommendation_reason: str | None = None
    evidence_summary: list[EvidenceItem] = []
    infeasibility_reason: str | None = None
