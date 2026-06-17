"""Initial market_reference schema: raw_market_quotes and sku_reference_price

Revision ID: 0001
Revises:
Create Date: 2026-06-17
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS market_reference")

    op.create_table(
        "raw_market_quotes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("source_platform", sa.String(50), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("seller_id", sa.String(255), nullable=True),
        sa.Column("sku_model_raw", sa.Text(), nullable=False),
        sa.Column("sku_model_normalized", sa.String(500), nullable=True),
        sa.Column("unit_price", sa.Numeric(12, 4), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="CNY"),
        sa.Column("moq", sa.Integer(), nullable=True),
        sa.Column("quote_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("scraped_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("raw_html_snapshot_path", sa.Text(), nullable=True),
        sa.Column(
            "extraction_method",
            sa.String(100),
            nullable=False,
            server_default="qwen_nlp_extraction",
        ),
        sa.Column("extraction_confidence", sa.Numeric(3, 2), nullable=True),
        schema="market_reference",
    )
    op.create_index(
        "ix_rmq_sku_normalized",
        "raw_market_quotes",
        ["sku_model_normalized"],
        schema="market_reference",
    )
    op.create_index(
        "ix_rmq_source_platform",
        "raw_market_quotes",
        ["source_platform"],
        schema="market_reference",
    )
    op.create_index(
        "ix_rmq_quote_timestamp",
        "raw_market_quotes",
        ["quote_timestamp"],
        schema="market_reference",
    )

    op.create_table(
        "sku_reference_price",
        sa.Column("sku_model_normalized", sa.String(500), primary_key=True),
        sa.Column("sample_count", sa.Integer(), nullable=False),
        sa.Column("weighted_avg_price", sa.Numeric(12, 4), nullable=True),
        sa.Column("p25_price", sa.Numeric(12, 4), nullable=True),
        sa.Column("median_price", sa.Numeric(12, 4), nullable=True),
        sa.Column("p75_price", sa.Numeric(12, 4), nullable=True),
        sa.Column("min_price", sa.Numeric(12, 4), nullable=True),
        sa.Column("max_price", sa.Numeric(12, 4), nullable=True),
        sa.Column("low_confidence", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("calculation_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("calculation_formula_version", sa.String(20), nullable=False),
        schema="market_reference",
    )


def downgrade() -> None:
    op.drop_table("sku_reference_price", schema="market_reference")
    op.drop_index(
        "ix_rmq_quote_timestamp", table_name="raw_market_quotes", schema="market_reference"
    )
    op.drop_index(
        "ix_rmq_source_platform", table_name="raw_market_quotes", schema="market_reference"
    )
    op.drop_index(
        "ix_rmq_sku_normalized", table_name="raw_market_quotes", schema="market_reference"
    )
    op.drop_table("raw_market_quotes", schema="market_reference")
    op.execute("DROP SCHEMA IF EXISTS market_reference CASCADE")
