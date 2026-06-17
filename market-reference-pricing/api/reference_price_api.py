"""
Market Reference Pricing API — external HTTP interface for GPM.

IMPORTANT: This API is the ONLY sanctioned way for GPM to consume
market reference data. GPM must call this API over HTTP; it must NOT
import any module from this package directly.

Every response includes a `disclaimer` field that MUST be surfaced
verbatim in the product UI:
  「市场参考价格区间（第三方平台公开报价统计，非成交价，仅供参考）」
"""

import os
from datetime import datetime
from decimal import Decimal
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

UI_DISCLAIMER = "市场参考价格区间（第三方平台公开报价统计，非成交价，仅供参考）"

app = FastAPI(
    title="Market Reference Pricing API",
    description=(
        "**重要声明：** 本 API 返回的价格仅为市场参考价格区间，"
        "不构成 GPM 正式定价依据。"
        "不得将本 API 返回的任何数字直接写入 GPM 定价公式或参数表。"
    ),
    version="1.0.0",
)

_engine = None
_SessionLocal = None


def _get_engine():
    global _engine, _SessionLocal
    if _engine is None:
        db_url = os.environ["DATABASE_URL"]
        _engine = create_engine(db_url, pool_pre_ping=True)
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
    return _engine


def get_db():
    _get_engine()
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()


class ReferencePriceResponse(BaseModel):
    sku_model_normalized: str
    sample_count: int
    weighted_avg_price: Optional[Decimal] = None
    p25_price: Optional[Decimal] = None
    median_price: Optional[Decimal] = None
    p75_price: Optional[Decimal] = None
    min_price: Optional[Decimal] = None
    max_price: Optional[Decimal] = None
    low_confidence: bool
    calculation_formula_version: str
    calculation_timestamp: datetime
    disclaimer: str = Field(
        default=UI_DISCLAIMER,
        description="Must be displayed verbatim in the product UI.",
    )


class HealthResponse(BaseModel):
    status: str
    db_reachable: bool


@app.get("/health", response_model=HealthResponse)
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
    return HealthResponse(status="ok" if db_ok else "degraded", db_reachable=db_ok)


@app.get(
    "/reference-price/{sku_model_normalized}",
    response_model=ReferencePriceResponse,
    summary="查询 SKU 市场参考价格区间",
    description=(
        "返回指定 SKU 的市场参考价格区间。"
        "**注意：此价格仅供参考，不得直接写入 GPM 定价参数。**"
    ),
)
def get_reference_price(
    sku_model_normalized: str, db: Session = Depends(get_db)
) -> ReferencePriceResponse:
    row = db.execute(
        text(
            "SELECT * FROM market_reference.sku_reference_price "
            "WHERE sku_model_normalized = :sku"
        ),
        {"sku": sku_model_normalized},
    ).fetchone()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail=f"SKU '{sku_model_normalized}' 暂无市场参考价格数据",
        )

    return ReferencePriceResponse(**dict(row._mapping))


@app.get(
    "/reference-price/",
    response_model=list[ReferencePriceResponse],
    summary="搜索 SKU 市场参考价格",
)
def search_reference_prices(
    prefix: str = Query(..., min_length=2, description="SKU 前缀搜索（至少 2 个字符）"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[ReferencePriceResponse]:
    rows = db.execute(
        text(
            "SELECT * FROM market_reference.sku_reference_price "
            "WHERE sku_model_normalized LIKE :prefix "
            "ORDER BY sku_model_normalized LIMIT :limit"
        ),
        {"prefix": f"{prefix}%", "limit": limit},
    ).fetchall()

    return [ReferencePriceResponse(**dict(row._mapping)) for row in rows]
