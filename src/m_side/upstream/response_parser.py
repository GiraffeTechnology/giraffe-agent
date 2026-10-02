# Unicode escapes preserve the original multilingual parser vocabulary.
# This source representation does not translate the accepted input values.
"""
Upstream Response Parser — parses raw supplier messages into structured UpstreamResponse.
Uses deterministic regex parsing; no LLM required.
"""

from __future__ import annotations
import re
import uuid
from datetime import datetime, timezone
from typing import Any
from pydantic import BaseModel, Field

from src.m_side.m_event_logger import log_m_event


class UpstreamResponse(BaseModel):
    response_id: str
    inquiry_id: str
    project_id: str
    upstream_actor_id: str
    dependency_id: str
    dependency_type: str
    can_supply: bool
    matched_specs: dict = Field(default_factory=dict)
    price: float | None = None
    currency: str | None = None
    moq: int | float | None = None
    available_quantity: int | float | None = None
    lead_time_days: int | None = None
    earliest_dispatch_date: str | None = None
    quality_notes: str | None = None
    substitute_options: list[dict] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    confidence_score: float = 0.0
    completeness_score: float = 0.0
    raw_message: str = ""
    parsed_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ── Regex patterns ─────────────────────────────────────────────────────────────

_CAN_SUPPLY_YES = re.compile(
    '(\u53ef\u4ee5|\u80fd\u4f9b|\u6709\u8d27|in stock|can supply|can provide|yes|available|\u6211\u4eec\u53ef\u4ee5|\u6ca1\u95ee\u9898|\u80fd\u505a)',
    re.IGNORECASE,
)
_CAN_SUPPLY_NO = re.compile(
    "(\u65e0\u8d27|\u7f3a\u8d27|\u4e0d\u80fd|\u6ca1\u6709|cannot|can't|no stock|out of stock|unavailable|not available|\u6682\u65f6\u6ca1\u6709)",
    re.IGNORECASE,
)

_PRICE_PATTERNS = [
    re.compile(r"(?:usd|us\$|\$)\s*([\d,.]+)", re.IGNORECASE),
    re.compile(r"(?:rmb|cny|¥)\s*([\d,.]+)", re.IGNORECASE),
    re.compile('([\\d,.]+)\\s*(?:usd|rmb|cny|\\$|\u5143|\u7f8e\u5143)', re.IGNORECASE),
    re.compile('(?:price|\u4ef7\u683c|\u5355\u4ef7)[^\\d]*([\\d,.]+)', re.IGNORECASE),
    re.compile('(?:per meter|per piece|\u6bcf\u7c73|\u6bcf\u4ef6)[^\\d]*([\\d,.]+)', re.IGNORECASE),
]

_CURRENCY_PATTERNS = [
    (re.compile(r"\b(usd|us\$|\$)\b", re.IGNORECASE), "USD"),
    (re.compile('\\b(rmb|cny|\xa5|\u5143|\u4eba\u6c11\u5e01)\\b', re.IGNORECASE), "CNY"),
]

_LEAD_TIME_PATTERNS = [
    re.compile('(\\d+)\\s*(?:days?|\u5929|\u65e5)', re.IGNORECASE),
    re.compile(r"lead\s*time[^\d]*(\d+)", re.IGNORECASE),
    re.compile('\u4ea4\u8d27[^\\d]*(\\d+)', re.IGNORECASE),
    re.compile('\u4ea4\u671f[^\\d]*(\\d+)', re.IGNORECASE),
]

_MOQ_PATTERNS = [
    re.compile(r"moq[^\d]*([\d,]+)", re.IGNORECASE),
    re.compile(r"minimum[^\d]*([\d,]+)", re.IGNORECASE),
    re.compile('\u6700\u5c0f\u8d77\u8ba2[^\\d]*([\\d,]+)', re.IGNORECASE),
    re.compile('\u8d77\u8ba2\u91cf[^\\d]*([\\d,]+)', re.IGNORECASE),
    re.compile('\u6700\u4f4e[^\\d]*([\\d,]+)\\s*(?:\u7c73|\u4ef6|pcs|meters?|m\\b)', re.IGNORECASE),
]

_QTY_PATTERNS = [
    re.compile(r"stock[^\d]*([\d,]+)", re.IGNORECASE),
    re.compile(r"available[^\d]*([\d,]+)", re.IGNORECASE),
    re.compile('\u5e93\u5b58[^\\d]*([\\d,]+)', re.IGNORECASE),
    re.compile('\u73b0\u8d27[^\\d]*([\\d,]+)', re.IGNORECASE),
]

_DATE_PATTERNS = [
    re.compile(r"dispatch\s+(?:by\s+|on\s+)?(\d{4}-\d{2}-\d{2})", re.IGNORECASE),
    re.compile(r"ship\s+(?:by\s+|on\s+)?(\d{4}-\d{2}-\d{2})", re.IGNORECASE),
    re.compile('\u53d1\u8d27[\u65e5\u671f]*[\uff1a:\\s]*(\\d{4}[-/]\\d{1,2}[-/]\\d{1,2})', re.IGNORECASE),
    re.compile(r"(\d{4}-\d{2}-\d{2})", re.IGNORECASE),
]

_QUALITY_PATTERNS = [
    re.compile('(?:shrinkage|\u7f29\u6c34)[^.\u3002\\n]*([\\d.]+%?)', re.IGNORECASE),
    re.compile('(?:quality|\u54c1\u8d28|\u54c1\u7ea7)[\uff1a:\\s]*([^,\uff0c.\u3002\\n]{3,40})', re.IGNORECASE),
]

_SUBSTITUTE_PATTERN = re.compile(
    '(?:substitute|alternative|\u66ff\u4ee3\u54c1|\u66ff\u4ee3)[\uff1a:\\s]*([^,\uff0c.\u3002\\n]{3,60})',
    re.IGNORECASE,
)


def _parse_float(s: str) -> float | None:
    try:
        return float(s.replace(",", ""))
    except (ValueError, AttributeError):
        return None


def _parse_int(s: str) -> int | None:
    try:
        return int(s.replace(",", ""))
    except (ValueError, AttributeError):
        return None


def _extract_price(text: str) -> float | None:
    for pattern in _PRICE_PATTERNS:
        m = pattern.search(text)
        if m:
            v = _parse_float(m.group(1))
            if v and v > 0:
                return v
    return None


def _extract_currency(text: str) -> str | None:
    for pattern, currency in _CURRENCY_PATTERNS:
        if pattern.search(text):
            return currency
    return None


def _extract_lead_time(text: str) -> int | None:
    for pattern in _LEAD_TIME_PATTERNS:
        m = pattern.search(text)
        if m:
            v = _parse_int(m.group(1))
            if v and 1 <= v <= 365:
                return v
    return None


def _extract_moq(text: str) -> int | float | None:
    for pattern in _MOQ_PATTERNS:
        m = pattern.search(text)
        if m:
            v = _parse_int(m.group(1))
            if v and v > 0:
                return v
    return None


def _extract_quantity(text: str) -> int | float | None:
    for pattern in _QTY_PATTERNS:
        m = pattern.search(text)
        if m:
            v = _parse_int(m.group(1))
            if v and v > 0:
                return v
    return None


def _extract_date(text: str) -> str | None:
    for pattern in _DATE_PATTERNS:
        m = pattern.search(text)
        if m:
            return m.group(1).replace("/", "-")
    return None


def _extract_quality_notes(text: str) -> str | None:
    for pattern in _QUALITY_PATTERNS:
        m = pattern.search(text)
        if m:
            return m.group(1).strip()
    return None


def _extract_substitutes(text: str) -> list[dict]:
    results = []
    for m in _SUBSTITUTE_PATTERN.finditer(text):
        results.append({"description": m.group(1).strip()})
    return results


def _compute_completeness(
    can_supply: bool,
    price: float | None,
    lead_time: int | None,
    moq: int | float | None,
    currency: str | None,
) -> float:
    score = 0.0
    if can_supply:
        score += 0.3
    if price is not None:
        score += 0.2
    if lead_time is not None:
        score += 0.2
    if moq is not None:
        score += 0.15
    if currency is not None:
        score += 0.15
    return round(score, 2)


def _compute_confidence(completeness: float, risk_flags: list[str]) -> float:
    base = completeness
    penalty = len(risk_flags) * 0.08
    return round(max(0.0, min(1.0, base - penalty)), 2)


def parse_upstream_response(
    raw_message: str,
    inquiry_id: str,
    project_id: str,
    upstream_actor_id: str,
    dependency_id: str,
    dependency_type: str,
) -> UpstreamResponse:
    text = raw_message

    # can_supply
    can_supply = True
    if _CAN_SUPPLY_NO.search(text):
        can_supply = False
    elif _CAN_SUPPLY_YES.search(text):
        can_supply = True
    else:
        # default optimistic for parseable messages
        can_supply = True

    price = _extract_price(text)
    currency = _extract_currency(text)
    lead_time = _extract_lead_time(text)
    moq = _extract_moq(text)
    available_qty = _extract_quantity(text)
    dispatch_date = _extract_date(text)
    quality_notes = _extract_quality_notes(text)
    substitutes = _extract_substitutes(text)

    risk_flags: list[str] = []
    if not can_supply:
        risk_flags.append("supplier_cannot_supply")
    if lead_time and lead_time > 21:
        risk_flags.append(f"long_lead_time_{lead_time}d")
    if price is None:
        risk_flags.append("price_not_confirmed")
    if moq is None:
        risk_flags.append("moq_not_confirmed")
    if quality_notes and "shrinkage" in quality_notes.lower():
        risk_flags.append("shrinkage_risk_noted")

    completeness = _compute_completeness(can_supply, price, lead_time, moq, currency)
    confidence = _compute_confidence(completeness, risk_flags)

    matched_specs: dict[str, Any] = {}
    if price is not None:
        matched_specs["price"] = price
    if currency:
        matched_specs["currency"] = currency
    if lead_time is not None:
        matched_specs["lead_time_days"] = lead_time
    if moq is not None:
        matched_specs["moq"] = moq
    if available_qty is not None:
        matched_specs["available_quantity"] = available_qty
    if dispatch_date:
        matched_specs["dispatch_date"] = dispatch_date

    response = UpstreamResponse(
        response_id=f"UPR-{uuid.uuid4().hex[:10].upper()}",
        inquiry_id=inquiry_id,
        project_id=project_id,
        upstream_actor_id=upstream_actor_id,
        dependency_id=dependency_id,
        dependency_type=dependency_type,
        can_supply=can_supply,
        matched_specs=matched_specs,
        price=price,
        currency=currency,
        moq=moq,
        available_quantity=available_qty,
        lead_time_days=lead_time,
        earliest_dispatch_date=dispatch_date,
        quality_notes=quality_notes,
        substitute_options=substitutes,
        risk_flags=risk_flags,
        confidence_score=confidence,
        completeness_score=completeness,
        raw_message=raw_message,
    )

    log_m_event(
        event_type="UPSTREAM_RESPONSE_PARSED",
        b_workspace_id=project_id,
        supplier_id=upstream_actor_id,
        payload={
            "response_id": response.response_id,
            "inquiry_id": inquiry_id,
            "can_supply": can_supply,
            "price": price,
            "lead_time_days": lead_time,
            "completeness_score": completeness,
            "confidence_score": confidence,
            "risk_flags": risk_flags,
        },
    )

    return response
