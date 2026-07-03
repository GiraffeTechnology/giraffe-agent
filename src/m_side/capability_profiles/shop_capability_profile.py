"""
Shop Capability Profile — represents a manufacturer's complete shop-floor capability.
"""

from __future__ import annotations
import json
from pathlib import Path
from pydantic import BaseModel, Field

from src.m_side.capability_profiles.machining_center_profile import MachiningCenterProfile


class ShopCapabilityProfile(BaseModel):
    actor_id: str
    machines: list[MachiningCenterProfile] = Field(default_factory=list)
    tooling_inventory: dict = Field(default_factory=dict)
    qc_equipment: list[dict] = Field(default_factory=list)
    in_house_processes: list[str] = Field(default_factory=list)
    outsourced_processes: list[str] = Field(default_factory=list)
    material_inventory: dict = Field(default_factory=dict)
    schedule_summary: dict = Field(default_factory=dict)

    def has_material_in_stock(self, material: str) -> bool:
        material_lower = material.lower()
        for key in self.material_inventory:
            if material_lower in key.lower() or key.lower() in material_lower:
                qty = self.material_inventory[key]
                if isinstance(qty, (int, float)) and qty > 0:
                    return True
                if isinstance(qty, dict) and qty.get("quantity", 0) > 0:
                    return True
        return False

    def material_is_supported(self, material: str) -> bool:
        """Check if any machine supports this material."""
        return any(m.supports_material(material) for m in self.machines)

    def get_best_machines_for(
        self, axis_count: int | None = None, material: str | None = None
    ) -> list[MachiningCenterProfile]:
        candidates = self.machines
        if axis_count is not None:
            candidates = [m for m in candidates if (m.axis_count or 0) >= axis_count]
        if material:
            candidates = [m for m in candidates if m.supports_material(material)]
        return candidates

    def can_do_process_in_house(self, process: str) -> bool:
        process_lower = process.lower()
        return any(process_lower in p.lower() or p.lower() in process_lower
                   for p in self.in_house_processes)

    def has_qc_capability(self, qc_type: str) -> bool:
        qc_type_lower = qc_type.lower()
        for qc in self.qc_equipment:
            cap = qc.get("capability", "")
            if qc_type_lower in cap.lower() or cap.lower() in qc_type_lower:
                return True
        return False


def load_shop_profile_from_fixture(fixture_path: str) -> ShopCapabilityProfile:
    path = Path(fixture_path)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return ShopCapabilityProfile.model_validate(data)
