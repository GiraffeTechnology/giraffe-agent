"""Evidence item model for tracking data sources and confidence."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from .enums import EvidenceSourceType


class EvidenceItem(BaseModel):
    """A single piece of evidence that supports a duration or date estimate."""

    evidence_id: str
    source_type: EvidenceSourceType
    source_id: str | None = None
    description: str
    value: Any | None = None
    confidence: float = Field(ge=0.0, le=1.0)  # 0.0 to 1.0
    created_at: datetime | None = None
