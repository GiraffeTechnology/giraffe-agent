"""QC equipment profile for shop capability."""
from __future__ import annotations
from pydantic import BaseModel, Field


class QCEquipmentProfile(BaseModel):
    equipment_id: str
    name: str
    capability: str
    measurement_range_mm: float | None = None
    resolution_mm: float | None = None
    certifications: list[str] = Field(default_factory=list)
