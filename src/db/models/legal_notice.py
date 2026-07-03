from __future__ import annotations
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy import String, JSON, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base
from src.db.mixins import new_uuid


def _utcnow():
    return datetime.now(timezone.utc)


class LegalNotice(Base):
    __tablename__ = "legal_notices"

    notice_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    notice_type: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[str] = mapped_column(String(16), nullable=False)
    text_en: Mapped[str] = mapped_column(String(8192), nullable=False)
    text_zh: Mapped[Optional[str]] = mapped_column(String(8192), nullable=True)
    effective_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
