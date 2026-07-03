from __future__ import annotations
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy import String, Boolean, JSON, Index, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base
from src.db.mixins import new_uuid


def _utcnow():
    return datetime.now(timezone.utc)


class RoleContext(Base):
    __tablename__ = "role_contexts"

    role_context_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.project_id"), nullable=False)
    edge_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("procurement_edges.edge_id"), nullable=True)
    actor_id: Mapped[str] = mapped_column(String(36), ForeignKey("actors.actor_id"), nullable=False)
    counterparty_actor_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("actors.actor_id"), nullable=True)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    role_reason: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    permissions_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    can_create_upstream_inquiry: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    can_approve_upstream_option: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    can_submit_response_to_buyer: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    __table_args__ = (
        Index("ix_role_contexts_project_id", "project_id"),
        Index("ix_role_contexts_actor_id", "actor_id"),
    )
