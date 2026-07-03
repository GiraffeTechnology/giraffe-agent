from __future__ import annotations
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy import String, Float, Integer, Boolean, JSON, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base
from src.db.mixins import new_uuid


def _utcnow():
    return datetime.now(timezone.utc)


class DependencyNeed(Base):
    __tablename__ = "dependency_needs"

    dependency_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.project_id"), nullable=False)
    created_by_actor_id: Mapped[str] = mapped_column(String(36), ForeignKey("actors.actor_id"), nullable=False)
    dependency_type: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(String(1024), nullable=False, default="")
    required_specs_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    quantity_required: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    required_by_date: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    risk_level: Mapped[str] = mapped_column(String(32), nullable=False, default="medium")
    why_needed: Mapped[str] = mapped_column(String(1024), nullable=False, default="")
    candidate_actor_ids_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    source: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)


class UpstreamInquiry(Base):
    __tablename__ = "upstream_inquiries"

    upstream_inquiry_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.project_id"), nullable=False)
    edge_id: Mapped[str] = mapped_column(String(36), ForeignKey("procurement_edges.edge_id"), nullable=False)
    dependency_id: Mapped[str] = mapped_column(String(36), ForeignKey("dependency_needs.dependency_id"), nullable=False)
    parent_main_supplier_actor_id: Mapped[str] = mapped_column(String(36), ForeignKey("actors.actor_id"), nullable=False)
    upstream_actor_id: Mapped[str] = mapped_column(String(36), ForeignKey("actors.actor_id"), nullable=False)
    message_text_en: Mapped[Optional[str]] = mapped_column(String(4096), nullable=True)
    message_text_zh: Mapped[Optional[str]] = mapped_column(String(4096), nullable=True)
    requested_fields_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    required_reply_schema_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    due_time: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    dispatch_channel: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="SENT")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)


class UpstreamResponse(Base):
    __tablename__ = "upstream_responses"

    upstream_response_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.project_id"), nullable=False)
    edge_id: Mapped[str] = mapped_column(String(36), ForeignKey("procurement_edges.edge_id"), nullable=False)
    upstream_inquiry_id: Mapped[str] = mapped_column(String(36), ForeignKey("upstream_inquiries.upstream_inquiry_id"), nullable=False)
    dependency_id: Mapped[str] = mapped_column(String(36), ForeignKey("dependency_needs.dependency_id"), nullable=False)
    from_actor_id: Mapped[str] = mapped_column(String(36), ForeignKey("actors.actor_id"), nullable=False)
    can_supply: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    matched_specs_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    currency: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    moq: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    available_quantity: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    lead_time_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    earliest_dispatch_date: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    quality_notes: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    substitute_options_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    risk_flags_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    completeness_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    raw_message: Mapped[Optional[str]] = mapped_column(String(8192), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)


class UpstreamOption(Base):
    __tablename__ = "upstream_options"

    option_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.project_id"), nullable=False)
    dependency_id: Mapped[str] = mapped_column(String(36), ForeignKey("dependency_needs.dependency_id"), nullable=False)
    upstream_actor_id: Mapped[str] = mapped_column(String(36), ForeignKey("actors.actor_id"), nullable=False)
    option_label: Mapped[str] = mapped_column(String(32), nullable=False)
    price_summary: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    lead_time_summary: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    risk_summary: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    response_ids_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)
