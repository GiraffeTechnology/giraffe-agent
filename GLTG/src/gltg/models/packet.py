"""DeliveryFeasibilityPacket -- the top-level output of the GLTG engine."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel

from .enums import FeasibilityStatus
from .path import DeliveryPathOption
from .risk import RiskFlag
from .evidence import EvidenceItem


class DeliveryFeasibilityPacket(BaseModel):
    """The complete feasibility assessment for an order."""

    order_id: str
    status: FeasibilityStatus
    generated_at: datetime
    earliest_feasible_date: date | None = None
    most_likely_date: date | None = None
    commitable_date: date | None = None
    risk_adjusted_latest_date: date | None = None
    on_time_probability: float | None = None   # 0.0-1.0
    options: list[DeliveryPathOption] = []     # 0 to 3 ranked options
    critical_path: list[str] = []              # node_ids in order
    bottleneck_nodes: list[str] = []
    risk_flags: list[RiskFlag] = []
    missing_fields: list[str] = []
    evidence_summary: list[EvidenceItem] = []
    recommended_action: str | None = None
    human_review_required: bool = True
