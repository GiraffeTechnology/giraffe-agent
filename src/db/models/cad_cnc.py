from __future__ import annotations
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy import String, Float, Integer, Boolean, JSON, Index, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base
from src.db.mixins import new_uuid


def _utcnow():
    return datetime.now(timezone.utc)


class CADRequirementPacket(Base):
    __tablename__ = "cad_requirement_packets"

    packet_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.project_id"), nullable=False)
    original_buyer_actor_id: Mapped[str] = mapped_column(String(36), ForeignKey("actors.actor_id"), nullable=False)
    main_supplier_actor_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("actors.actor_id"), nullable=True)
    file_refs_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    source_types_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    part_summary: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    material: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    quantity: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    dimensions_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    tolerance_requirements_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    surface_finish_requirements_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    thread_requirements_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    heat_treatment_requirements_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    operation_requirements_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    qc_requirements_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    packaging_requirements_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    delivery_deadline: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    missing_information_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    extraction_confidence_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)


class ManufacturingFeatureSet(Base):
    __tablename__ = "manufacturing_feature_sets"

    feature_set_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    packet_id: Mapped[str] = mapped_column(String(36), ForeignKey("cad_requirement_packets.packet_id"), nullable=False)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.project_id"), nullable=False)
    required_processes_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    required_machine_types_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    min_axis_requirement: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    work_envelope_required_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    material_required: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    tolerance_class: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    surface_finish_class: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    thread_or_hole_features_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    heat_treatment_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    external_process_likely_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    qc_required_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    risk_flags_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    missing_information_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)


class CADCNCMatchResult(Base):
    __tablename__ = "cad_cnc_match_results"

    match_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.project_id"), nullable=False)
    actor_id: Mapped[str] = mapped_column(String(36), ForeignKey("actors.actor_id"), nullable=False)
    cad_requirement_packet_id: Mapped[str] = mapped_column(String(36), ForeignKey("cad_requirement_packets.packet_id"), nullable=False)
    shop_capability_profile_id: Mapped[str] = mapped_column(String(36), ForeignKey("shop_capability_profiles.profile_id"), nullable=False)
    can_make_in_house: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    recommended_machine_ids_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    machine_fit_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    work_envelope_fit: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown")
    material_fit: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown")
    tolerance_fit: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown")
    surface_finish_fit: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown")
    tooling_fit: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown")
    qc_fit: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown")
    schedule_fit: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown")
    required_upstream_dependencies_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    required_subcontract_dependencies_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    risk_flags_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    missing_information_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    explanation: Mapped[Optional[str]] = mapped_column(String(4096), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)

    __table_args__ = (
        Index("ix_cad_cnc_match_results_project_id", "project_id"),
    )


class CapabilityFitReport(Base):
    __tablename__ = "capability_fit_reports"

    report_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.project_id"), nullable=False)
    actor_id: Mapped[str] = mapped_column(String(36), ForeignKey("actors.actor_id"), nullable=False)
    cad_cnc_match_id: Mapped[str] = mapped_column(String(36), ForeignKey("cad_cnc_match_results.match_id"), nullable=False)
    buyer_facing_summary_en: Mapped[Optional[str]] = mapped_column(String(4096), nullable=True)
    buyer_facing_summary_zh: Mapped[Optional[str]] = mapped_column(String(4096), nullable=True)
    internal_summary: Mapped[Optional[str]] = mapped_column(String(4096), nullable=True)
    can_quote_now: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    can_make_in_house: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    recommended_next_actions_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    required_upstream_inquiries_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    required_subcontractor_inquiries_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    risk_flags_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)
