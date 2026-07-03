from __future__ import annotations
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy import String, Boolean, JSON, Index, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base
from src.db.mixins import new_uuid


def _utcnow():
    return datetime.now(timezone.utc)


class Actor(Base):
    __tablename__ = "actors"

    actor_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    actor_type: Mapped[str] = mapped_column(String(64), nullable=False)
    default_language: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    contact_channels_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    capabilities_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    profile_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)

    __table_args__ = (
        Index("ix_actors_actor_type", "actor_type"),
    )
