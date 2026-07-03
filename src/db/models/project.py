from __future__ import annotations
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy import String, Integer, JSON, Index, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base
from src.db.mixins import new_uuid


def _utcnow():
    return datetime.now(timezone.utc)


class Project(Base):
    __tablename__ = "projects"

    project_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    original_buyer_actor_id: Mapped[str] = mapped_column(String(36), ForeignKey("actors.actor_id"), nullable=False)
    main_supplier_actor_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("actors.actor_id"), nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    product_summary: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    quantity: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="CREATED")
    product_tier: Mapped[str] = mapped_column(String(32), nullable=False, default="free")
    created_by_channel: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    __table_args__ = (
        Index("ix_projects_original_buyer_actor_id", "original_buyer_actor_id"),
        Index("ix_projects_main_supplier_actor_id", "main_supplier_actor_id"),
        Index("ix_projects_status", "status"),
        Index("ix_projects_category", "category"),
        Index("ix_projects_created_at", "created_at"),
    )
