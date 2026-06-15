"""DecisionPacket -- simplified view of the feasibility packet for agents."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel

from ..models.enums import FeasibilityStatus
from ..models.packet import DeliveryFeasibilityPacket


class DecisionOption(BaseModel):
    """Simplified single option for agent consumption."""

    option_id: str
    label: str | None = None
    commitable_date: date | None = None
    most_likely_date: date | None = None
    on_time_probability: float | None = None
    recommendation_reason: str | None = None
    risk_count: int = 0
    score: float | None = None


class DecisionPacket(BaseModel):
    """A lightweight summary of DeliveryFeasibilityPacket for downstream agents."""

    order_id: str
    status: FeasibilityStatus
    generated_at: datetime
    commitable_date: date | None = None
    most_likely_date: date | None = None
    on_time_probability: float | None = None
    options: list[DecisionOption] = []
    recommended_action: str | None = None
    human_review_required: bool = True
    top_risk_codes: list[str] = []
    missing_fields: list[str] = []

    @classmethod
    def from_packet(cls, packet: DeliveryFeasibilityPacket) -> "DecisionPacket":
        """Create a DecisionPacket from a full DeliveryFeasibilityPacket."""
        options = []
        for opt in packet.options:
            options.append(DecisionOption(
                option_id=opt.option_id,
                label=opt.label.value if opt.label else None,
                commitable_date=opt.commitable_date,
                most_likely_date=opt.most_likely_date,
                on_time_probability=opt.on_time_probability,
                recommendation_reason=opt.recommendation_reason,
                risk_count=len(opt.risk_flags),
                score=opt.score,
            ))

        top_risks = [rf.code.value for rf in packet.risk_flags[:5]]

        return cls(
            order_id=packet.order_id,
            status=packet.status,
            generated_at=packet.generated_at,
            commitable_date=packet.commitable_date,
            most_likely_date=packet.most_likely_date,
            on_time_probability=packet.on_time_probability,
            options=options,
            recommended_action=packet.recommended_action,
            human_review_required=packet.human_review_required,
            top_risk_codes=top_risks,
            missing_fields=packet.missing_fields,
        )
