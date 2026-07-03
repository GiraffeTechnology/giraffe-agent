from __future__ import annotations
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy import String, Float, JSON, Index, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base
from src.db.mixins import new_uuid


def _utcnow():
    return datetime.now(timezone.utc)


class ChannelSession(Base):
    __tablename__ = "channel_sessions"

    session_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    project_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("projects.project_id"), nullable=True)
    edge_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("procurement_edges.edge_id"), nullable=True)
    actor_id: Mapped[str] = mapped_column(String(36), ForeignKey("actors.actor_id"), nullable=False)
    counterparty_actor_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("actors.actor_id"), nullable=True)
    channel_type: Mapped[str] = mapped_column(String(32), nullable=False)
    channel_user_id: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    state_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    last_message_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)


class Message(Base):
    __tablename__ = "messages"

    message_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    session_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("channel_sessions.session_id"), nullable=True)
    project_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("projects.project_id"), nullable=True)
    edge_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("procurement_edges.edge_id"), nullable=True)
    role_context_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("role_contexts.role_context_id"), nullable=True)
    sender_actor_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("actors.actor_id"), nullable=True)
    receiver_actor_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("actors.actor_id"), nullable=True)
    channel_type: Mapped[str] = mapped_column(String(32), nullable=False)
    direction: Mapped[str] = mapped_column(String(16), nullable=False, default="inbound")
    raw_text: Mapped[Optional[str]] = mapped_column(String(8192), nullable=True)
    normalized_text: Mapped[Optional[str]] = mapped_column(String(8192), nullable=True)
    attachments_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    parsed_intent: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    parsed_entities_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    __table_args__ = (
        Index("ix_messages_project_id", "project_id"),
        Index("ix_messages_session_id", "session_id"),
    )
