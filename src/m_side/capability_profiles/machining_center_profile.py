"""
Machining Center Profile — represents a CNC machine's capability parameters.
"""

from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field


class MachiningCenterProfile(BaseModel):
    machine_id: str
    actor_id: str
    machine_name: str
    machine_type: Literal[
        "cnc_milling",
        "cnc_turning",
        "turn_mill",
        "5_axis_machining_center",
        "grinding",
        "edm",
        "other",
    ]
    axis_count: int | None = None
    travel_x_mm: float | None = None
    travel_y_mm: float | None = None
    travel_z_mm: float | None = None
    max_part_weight_kg: float | None = None
    spindle_speed_rpm: int | None = None
    spindle_power_kw: float | None = None
    tool_magazine_capacity: int | None = None
    supported_materials: list[str] = Field(default_factory=list)
    typical_tolerance_mm: float | None = None
    best_tolerance_mm: float | None = None
    surface_finish_capability: list[str] = Field(default_factory=list)
    available_operations: list[str] = Field(default_factory=list)
    schedule_status: Literal["available", "limited", "busy", "unknown"] = "unknown"
    earliest_start_date: str | None = None

    def can_fit_part(self, length_mm: float, width_mm: float, height_mm: float) -> bool:
        """Check if part dimensions fit within this machine's work envelope."""
        if self.travel_x_mm and length_mm > self.travel_x_mm:
            return False
        if self.travel_y_mm and width_mm > self.travel_y_mm:
            return False
        if self.travel_z_mm and height_mm > self.travel_z_mm:
            return False
        return True

    def supports_material(self, material: str) -> bool:
        """Case-insensitive material support check."""
        material_lower = material.lower()
        return any(m.lower() in material_lower or material_lower in m.lower()
                   for m in self.supported_materials)

    def can_achieve_tolerance(self, required_mm: float) -> bool:
        """Check if machine can achieve required tolerance."""
        if self.best_tolerance_mm is None:
            return True  # unknown — assume possible
        return required_mm >= self.best_tolerance_mm
