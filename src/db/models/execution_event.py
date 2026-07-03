from __future__ import annotations
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy import String, Float, JSON, Index, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base
from src.db.mixins import new_uuid


def _utcnow():
    return datetime.now(timezone.utc)


class ExecutionEvent(Base):
    __tablename__ = "execution_events"

    event_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    project_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("projects.project_id"), nullable=True)
    edge_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("procurement_edges.edge_id"), nullable=True)
    actor_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("actors.actor_id"), nullable=True)
    role_context_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("role_contexts.role_context_id"), nullable=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    source_channel: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    source_message_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    __table_args__ = (
        Index("ix_execution_events_project_id", "project_id"),
        Index("ix_execution_events_event_type", "event_type"),
        Index("ix_execution_events_created_at", "created_at"),
    )
