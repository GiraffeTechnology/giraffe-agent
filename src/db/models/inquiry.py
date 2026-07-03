from __future__ import annotations
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy import String, JSON, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base
from src.db.mixins import new_uuid


def _utcnow():
    return datetime.now(timezone.utc)


class SupplierInquiry(Base):
    __tablename__ = "supplier_inquiries"

    inquiry_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.project_id"), nullable=False)
    edge_id: Mapped[str] = mapped_column(String(36), ForeignKey("procurement_edges.edge_id"), nullable=False)
    from_actor_id: Mapped[str] = mapped_column(String(36), ForeignKey("actors.actor_id"), nullable=False)
    to_actor_id: Mapped[str] = mapped_column(String(36), ForeignKey("actors.actor_id"), nullable=False)
    requirement_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("structured_requirements.requirement_id"), nullable=True)
    message_text_en: Mapped[Optional[str]] = mapped_column(String(4096), nullable=True)
    message_text_zh: Mapped[Optional[str]] = mapped_column(String(4096), nullable=True)
    message_text_local: Mapped[Optional[str]] = mapped_column(String(4096), nullable=True)
    requested_fields_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    required_reply_schema_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="SENT")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)
