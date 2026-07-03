from __future__ import annotations
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy import String, Float, JSON, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base
from src.db.mixins import new_uuid


def _utcnow():
    return datetime.now(timezone.utc)


class SupplierScoreSnapshot(Base):
    __tablename__ = "supplier_score_snapshots"

    snapshot_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    actor_id: Mapped[str] = mapped_column(String(36), ForeignKey("actors.actor_id"), nullable=False)
    project_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("projects.project_id"), nullable=True)
    response_speed_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    acceptance_rate_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    on_time_delivery_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    media_cooperation_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    quality_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    lead_time_accuracy_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    quote_completeness_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    capability_confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    risk_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    computed_from_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)


class SupplierProfileUpdate(Base):
    __tablename__ = "supplier_profile_updates"

    update_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    actor_id: Mapped[str] = mapped_column(String(36), ForeignKey("actors.actor_id"), nullable=False)
    project_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("projects.project_id"), nullable=True)
    update_type: Mapped[str] = mapped_column(String(64), nullable=False)
    previous_value_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    new_value_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    evidence_event_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("execution_events.event_id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
