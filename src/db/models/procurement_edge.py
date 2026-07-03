from __future__ import annotations
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy import String, JSON, Index, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base
from src.db.mixins import new_uuid


def _utcnow():
    return datetime.now(timezone.utc)


class ProcurementEdge(Base):
    __tablename__ = "procurement_edges"

    edge_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.project_id"), nullable=False)
    from_actor_id: Mapped[str] = mapped_column(String(36), ForeignKey("actors.actor_id"), nullable=False)
    to_actor_id: Mapped[str] = mapped_column(String(36), ForeignKey("actors.actor_id"), nullable=False)
    edge_type: Mapped[str] = mapped_column(String(64), nullable=False)
    parent_edge_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("procurement_edges.edge_id"), nullable=True)
    inquiry_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    response_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    __table_args__ = (
        Index("ix_procurement_edges_project_id", "project_id"),
        Index("ix_procurement_edges_from_actor_id", "from_actor_id"),
        Index("ix_procurement_edges_to_actor_id", "to_actor_id"),
        Index("ix_procurement_edges_parent_edge_id", "parent_edge_id"),
        Index("ix_procurement_edges_edge_type", "edge_type"),
        Index("ix_procurement_edges_status", "status"),
    )
