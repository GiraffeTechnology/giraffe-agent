from __future__ import annotations
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Boolean, JSON, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base
from src.db.mixins import new_uuid


def _utcnow():
    return datetime.now(timezone.utc)


class Artifact(Base):
    __tablename__ = "artifacts"

    artifact_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    project_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("projects.project_id"), nullable=True)
    owner_actor_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("actors.actor_id"), nullable=True)
    artifact_type: Mapped[str] = mapped_column(String(32), nullable=False)
    file_name: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    file_ref: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_hash: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    mime_type: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    product_tier: Mapped[str] = mapped_column(String(32), nullable=False, default="professional_free")
    cap_level: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    encryption_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    dynamic_watermark_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    secure_viewer_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    warning_acknowledged: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)
