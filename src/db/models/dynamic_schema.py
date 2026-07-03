from __future__ import annotations
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy import String, Float, Integer, JSON, Index, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base
from src.db.mixins import new_uuid


def _utcnow():
    return datetime.now(timezone.utc)


class SchemaRegistry(Base):
    __tablename__ = "schema_registry"

    schema_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    industry: Mapped[str] = mapped_column(String(64), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class FieldDefinition(Base):
    __tablename__ = "field_definitions"

    field_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    schema_id: Mapped[str] = mapped_column(String(36), ForeignKey("schema_registry.schema_id"), nullable=False)
    field_name: Mapped[str] = mapped_column(String(128), nullable=False)
    normalized_field_name: Mapped[str] = mapped_column(String(128), nullable=False)
    field_type: Mapped[str] = mapped_column(String(32), nullable=False)
    unit: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    required_level: Mapped[str] = mapped_column(String(32), nullable=False, default="optional")
    validation_rule_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    example_values_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    source: Mapped[str] = mapped_column(String(128), nullable=False, default="manual")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="approved")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)

    __table_args__ = (
        Index("ix_field_definitions_normalized_field_name", "normalized_field_name"),
    )


class ObservedField(Base):
    __tablename__ = "observed_fields"

    observed_field_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    project_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("projects.project_id"), nullable=True)
    actor_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("actors.actor_id"), nullable=True)
    source_message_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("messages.message_id"), nullable=True)
    source_artifact_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("artifacts.artifact_id"), nullable=True)
    candidate_field_name: Mapped[str] = mapped_column(String(128), nullable=False)
    normalized_field_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    candidate_value: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    candidate_unit: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    normalized_value: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    evidence_text: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    __table_args__ = (
        Index("ix_observed_fields_normalized_field_name", "normalized_field_name"),
    )


class FieldProposal(Base):
    __tablename__ = "field_proposals"

    proposal_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    schema_id: Mapped[str] = mapped_column(String(36), ForeignKey("schema_registry.schema_id"), nullable=False)
    candidate_field_name: Mapped[str] = mapped_column(String(128), nullable=False)
    normalized_field_name: Mapped[str] = mapped_column(String(128), nullable=False)
    field_type: Mapped[str] = mapped_column(String(32), nullable=False)
    suggested_unit: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    business_reason: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    example_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    project_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    supplier_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(32), nullable=False, default="low")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="proposed")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class EntityDynamicValue(Base):
    __tablename__ = "entity_dynamic_values"

    value_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False)
    field_id: Mapped[str] = mapped_column(String(36), ForeignKey("field_definitions.field_id"), nullable=False)
    field_value: Mapped[str] = mapped_column(String(1024), nullable=False)
    unit: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    source: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    source_message_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("messages.message_id"), nullable=True)
    source_artifact_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("artifacts.artifact_id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    __table_args__ = (
        Index("ix_entity_dynamic_values_entity_type_id", "entity_type", "entity_id"),
    )


class FieldAlias(Base):
    __tablename__ = "field_aliases"

    alias_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    field_id: Mapped[str] = mapped_column(String(36), ForeignKey("field_definitions.field_id"), nullable=False)
    alias_text: Mapped[str] = mapped_column(String(256), nullable=False)
    language: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)


class UnitDictionary(Base):
    __tablename__ = "unit_dictionary"

    unit_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    unit_name: Mapped[str] = mapped_column(String(64), nullable=False)
    unit_symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    unit_type: Mapped[str] = mapped_column(String(64), nullable=False)
    conversion_rule_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)


class FieldPromotionDecision(Base):
    __tablename__ = "field_promotion_decisions"

    decision_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    proposal_id: Mapped[str] = mapped_column(String(36), ForeignKey("field_proposals.proposal_id"), nullable=False)
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    decided_by: Mapped[str] = mapped_column(String(128), nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
