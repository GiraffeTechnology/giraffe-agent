from __future__ import annotations
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy import String, Float, Integer, Boolean, JSON, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base
from src.db.mixins import new_uuid


def _utcnow():
    return datetime.now(timezone.utc)


class SupplierResponse(Base):
    __tablename__ = "supplier_responses"

    response_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.project_id"), nullable=False)
    edge_id: Mapped[str] = mapped_column(String(36), ForeignKey("procurement_edges.edge_id"), nullable=False)
    inquiry_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("supplier_inquiries.inquiry_id"), nullable=True)
    from_actor_id: Mapped[str] = mapped_column(String(36), ForeignKey("actors.actor_id"), nullable=False)
    to_actor_id: Mapped[str] = mapped_column(String(36), ForeignKey("actors.actor_id"), nullable=False)
    can_supply: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    currency: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    moq: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    available_quantity: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    lead_time_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    earliest_dispatch_date: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    capacity_basis_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    material_basis_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    subcontract_basis_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    qc_basis_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    logistics_basis_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    risk_flags_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    raw_message: Mapped[Optional[str]] = mapped_column(String(8192), nullable=True)
    parsed_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    completeness_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)
