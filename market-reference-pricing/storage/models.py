import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


SCHEMA = "market_reference"


class RawMarketQuote(Base):
    """
    One row = one price quote from one seller on one B2B platform.
    Every row must be traceable to source_url + raw_html_snapshot_path.
    """

    __tablename__ = "raw_market_quotes"
    __table_args__ = {"schema": SCHEMA}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_platform = Column(
        String(50), nullable=False, comment="alibaba / made_in_china / global_sources"
    )
    source_url = Column(
        Text, nullable=False, comment="Original page URL — mandatory for audit trail"
    )
    seller_id = Column(String(255), nullable=True, comment="Shop ID or seller name")
    sku_model_raw = Column(
        Text, nullable=False, comment="Raw model/spec text as scraped, pre-normalisation"
    )
    sku_model_normalized = Column(
        String(500),
        nullable=True,
        index=True,
        comment="Normalised SKU key used for exact matching",
    )
    unit_price = Column(Numeric(12, 4), nullable=False)
    currency = Column(String(3), nullable=False, default="CNY")
    moq = Column(Integer, nullable=True, comment="Minimum order quantity")
    quote_timestamp = Column(
        DateTime(timezone=True),
        nullable=False,
        comment="Page publish / quote date — used for time-decay weighting",
    )
    scraped_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    raw_html_snapshot_path = Column(
        Text,
        nullable=True,
        comment="Path to stored HTML/JSON snapshot for audit back-tracing",
    )
    extraction_method = Column(
        String(100),
        nullable=False,
        default="qwen_nlp_extraction",
        comment="Fixed: qwen_nlp_extraction — Qwen was used only for structured field parsing",
    )
    extraction_confidence = Column(
        Numeric(3, 2),
        nullable=True,
        comment="Qwen extraction confidence 0-1. Records < 0.8 require human review.",
    )


class SKUReferencePrice(Base):
    """
    Aggregated reference price per normalised SKU.
    Computed deterministically from RawMarketQuote rows — no ML involved.

    UI MUST display disclaimer: 市场参考价格区间（第三方平台公开报价统计，非成交价，仅供参考）
    """

    __tablename__ = "sku_reference_price"
    __table_args__ = {"schema": SCHEMA}

    sku_model_normalized = Column(String(500), primary_key=True)
    sample_count = Column(Integer, nullable=False)
    weighted_avg_price = Column(Numeric(12, 4), nullable=True)
    p25_price = Column(Numeric(12, 4), nullable=True)
    median_price = Column(Numeric(12, 4), nullable=True)
    p75_price = Column(Numeric(12, 4), nullable=True)
    min_price = Column(Numeric(12, 4), nullable=True)
    max_price = Column(Numeric(12, 4), nullable=True)
    low_confidence = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="True when sample_count < 5; frontend must show warning",
    )
    calculation_timestamp = Column(DateTime(timezone=True), nullable=False)
    calculation_formula_version = Column(
        String(20),
        nullable=False,
        comment="Bump version when DECAY_LAMBDA or formula changes; never overwrite history",
    )
