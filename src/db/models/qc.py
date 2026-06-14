"""
SQLAlchemy ORM models for QC reference images, process cards, and comparison reports.
Only active when GIRAFFE_DB_MODE=on.
"""
from sqlalchemy import String, Float, Boolean, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column
from src.db.base import Base


class QCReferenceImageORM(Base):
    __tablename__ = "qc_reference_images"

    ref_image_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    milestone_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    image_path: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    uploaded_by_actor_id: Mapped[str] = mapped_column(String(36), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[str] = mapped_column(String(32), nullable=False)


class QCProcessCardORM(Base):
    __tablename__ = "qc_process_cards"

    process_card_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    material_spec: Mapped[str | None] = mapped_column(Text, nullable=True)
    color_spec: Mapped[str | None] = mapped_column(String(256), nullable=True)
    size_spec: Mapped[str | None] = mapped_column(Text, nullable=True)
    finish_spec: Mapped[str | None] = mapped_column(String(256), nullable=True)
    defect_criteria: Mapped[str | None] = mapped_column(Text, nullable=True)
    supplier_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[str] = mapped_column(String(32), nullable=False)
    updated_at: Mapped[str] = mapped_column(String(32), nullable=False)


class QCComparisonReportORM(Base):
    __tablename__ = "qc_comparison_reports"

    report_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    milestone_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    overall_result: Mapped[str] = mapped_column(String(32), nullable=False)
    overall_score: Mapped[float] = mapped_column(Float, default=0.0)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    provider_name: Mapped[str] = mapped_column(String(32), nullable=False)
    model_name: Mapped[str] = mapped_column(String(64), nullable=False)
    requested_provider: Mapped[str] = mapped_column(String(32), nullable=False)
    fallback_used: Mapped[bool] = mapped_column(Boolean, default=False)
    m_side_feedback_zh: Mapped[str] = mapped_column(Text, nullable=False, default="")
    m_side_feedback_en: Mapped[str] = mapped_column(Text, nullable=False, default="")
    b_side_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    image_count: Mapped[int] = mapped_column(Integer, default=0)
    frames_used: Mapped[int] = mapped_column(Integer, default=0)
    buyer_confirmation_required: Mapped[bool] = mapped_column(Boolean, default=False)
    saved_at: Mapped[str] = mapped_column(String(32), nullable=False)
