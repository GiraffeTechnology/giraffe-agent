from __future__ import annotations
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy import String, Float, Boolean, JSON, Index, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base
from src.db.mixins import new_uuid


def _utcnow():
    return datetime.now(timezone.utc)


class SupplierResponseRollup(Base):
    __tablename__ = "supplier_response_rollups"

    rollup_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.project_id"), nullable=False)
    main_supplier_actor_id: Mapped[str] = mapped_column(String(36), ForeignKey("actors.actor_id"), nullable=False)
    can_accept_order: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    main_capacity_summary: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    approved_upstream_options_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    material_basis_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    trim_basis_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    subcontract_basis_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    qc_basis_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    packaging_basis_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    logistics_basis_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    price_basis_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    lead_time_basis_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    unresolved_dependencies_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    risk_flags_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    completeness_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    recommended_response_to_buyer_en: Mapped[Optional[str]] = mapped_column(String(4096), nullable=True)
    recommended_response_to_buyer_zh: Mapped[Optional[str]] = mapped_column(String(4096), nullable=True)
    cad_requirement_packet_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    cad_cnc_match_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    capability_fit_report_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    cnc_parameter_match_summary_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    can_make_in_house: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    recommended_machine_ids_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    capability_gaps_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    upstream_dependency_basis_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)

    __table_args__ = (
        Index("ix_supplier_response_rollups_project_id", "project_id"),
    )
