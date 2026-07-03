from __future__ import annotations
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy import String, JSON, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base
from src.db.mixins import new_uuid


def _utcnow():
    return datetime.now(timezone.utc)


class ShopCapabilityProfile(Base):
    __tablename__ = "shop_capability_profiles"

    profile_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    actor_id: Mapped[str] = mapped_column(String(36), ForeignKey("actors.actor_id"), nullable=False)
    profile_name: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    machines_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    tooling_inventory_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    qc_equipment_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    material_inventory_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    in_house_processes_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    outsourced_processes_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    schedule_summary_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)
