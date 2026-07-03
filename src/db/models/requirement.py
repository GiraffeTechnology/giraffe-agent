from __future__ import annotations
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Float, JSON, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base
from src.db.mixins import new_uuid


def _utcnow():
    return datetime.now(timezone.utc)


class StructuredRequirement(Base):
    __tablename__ = "structured_requirements"

    requirement_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.project_id"), nullable=False)
    source_actor_id: Mapped[str] = mapped_column(String(36), ForeignKey("actors.actor_id"), nullable=False)
    source_message_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    raw_input_refs_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    quantity: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    material: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    specs_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    deadline: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    destination: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    missing_fields_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)
