"""Risk flag model for surfacing supply-chain risks."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from .enums import RiskFlagCode


class RiskFlag(BaseModel):
    """A flagged risk associated with an order or node."""

    code: RiskFlagCode
    description: str
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = "MEDIUM"
    affected_nodes: list[str] = []
    mitigation_hint: str | None = None
