"""Duration estimate model with percentile confidence bands."""

from __future__ import annotations

from pydantic import BaseModel, Field

from .evidence import EvidenceItem


class DurationEstimate(BaseModel):
    """Probabilistic duration estimate for a single workflow node."""

    p50_days: float  # median estimate
    p80_days: float  # 80th percentile (comfortable buffer)
    p90_days: float  # 90th percentile (commitable)
    min_days: float | None = None
    max_days: float | None = None
    supplier_claim_days: float | None = None   # what the supplier stated
    computed_days: float | None = None          # capacity-based calculation
    memory_adjusted_days: float | None = None   # adjusted by historical records
    confidence: float = Field(ge=0.0, le=1.0)  # overall confidence 0.0-1.0
    evidence_summary: list[EvidenceItem] = []
