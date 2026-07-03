from __future__ import annotations
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy import String, JSON, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base
from src.db.mixins import new_uuid


def _utcnow():
    return datetime.now(timezone.utc)


class ApprovalRequest(Base):
    __tablename__ = "approval_requests"

    approval_request_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.project_id"), nullable=False)
    dependency_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("dependency_needs.dependency_id"), nullable=True)
    requested_by_actor_id: Mapped[str] = mapped_column(String(36), ForeignKey("actors.actor_id"), nullable=False)
    approval_mode: Mapped[str] = mapped_column(String(32), nullable=False, default="human")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")
    options_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    approved_option_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    approved_by_actor_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    approved_by_mode: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
