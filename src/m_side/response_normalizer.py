"""
M-side supplier response normalizer — deterministic regex-based parser.
Converts natural-language supplier replies into structured SupplierResponsePacket fields.
No LLM required for MVP.
"""

from __future__ import annotations
import re
import uuid
from datetime import datetime, timezone

from src.core_schema.m_side_types import (
    MSideWorkspace,
    SupplierResponsePacket,
    CapacitySignal,
    ScheduleSignal,
    MaterialAvailability,
    SupplierQuote,
    QCCommitment,
    LogisticsCommitment,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _combined_text(texts: list[str]) -> str:
    return " ".join(texts)


def _parse_can_make(text: str) -> bool | None:
    yes_patterns = [
        r"可以做", r"可以接", r"能做", r"能接", r"接单", r"可以生产",
        r"\bcan make\b", r"\bwe can\b", r"\byes\b", r"\bconfirm\b",
        r"可以", r"没问题",
    ]
    no_patterns = [
        r"不能做", r"无法做", r"做不了", r"不接", r"无法接单", r"产能已满",
        r"\bcannot make\b", r"\bcan't make\b", r"\bno capacity\b",
        r"抱歉.*无法", r"抱歉.*不能", r"当前产能已满",
    ]
    for pat in no_patterns:
        if re.search(pat, text, re.IGNORECASE):
            return False
    for pat in yes_patterns:
        if re.search(pat, text, re.IGNORECASE):
            return True
    return None


def _parse_lead_time(text: str) -> int | None:
    """Extract lead time in days. Supports days/weeks/天/周."""
    # Look for "total X days" type patterns first
    total_patterns = [
        r"总交期\s*(\d+)\s*天",
        r"总共\s*(\d+)\s*天",
        r"total.*?(\d+)\s*days?",
    ]
    for pat in total_patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return int(m.group(1))

    # Generic days pattern
    day_patterns = [
        r"大货\s*(\d+)\s*天",
        r"(\d+)\s*天交货",
        r"交期.*?(\d+)\s*天",
        r"(\d+)\s*(?:天|days?|日)(?:\s*交货)?",
    ]
    for pat in day_patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            val = int(m.group(1))
            if 1 <= val <= 365:
                return val

    # Weeks pattern
    week_patterns = [
        r"(\d+)\s*(?:周|weeks?)",
    ]
    for pat in week_patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return int(m.group(1)) * 7

    return None


def _parse_sample_lead_time(text: str) -> int | None:
    """Extract sample/prototype lead time."""
    patterns = [
        r"样品\s*(\d+)\s*天",
        r"sample.*?(\d+)\s*days?",
        r"打样\s*(\d+)\s*天",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return int(m.group(1))
    return None


def _parse_unit_price(text: str) -> tuple[float | None, str | None]:
    """Extract unit price and currency. Returns (price, currency)."""
    # USD patterns
    usd_patterns = [
        r"USD\s*(\d+\.?\d*)",
        r"\$\s*(\d+\.?\d*)",
        r"(\d+\.?\d*)\s*USD",
        r"(\d+\.?\d*)\s*美元",
        r"单价\s*USD\s*(\d+\.?\d*)",
        r"单价\s*(\d+\.?\d*)\s*(?:USD|美元)",
    ]
    for pat in usd_patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return float(m.group(1)), "USD"

    # RMB/CNY patterns
    rmb_patterns = [
        r"RMB\s*(\d+\.?\d*)",
        r"CNY\s*(\d+\.?\d*)",
        r"(\d+\.?\d*)\s*(?:RMB|CNY|元|人民币)",
        r"单价\s*(\d+\.?\d*)\s*元",
    ]
    for pat in rmb_patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return float(m.group(1)), "CNY"

    # EUR patterns
    eur_patterns = [
        r"EUR\s*(\d+\.?\d*)",
        r"€\s*(\d+\.?\d*)",
        r"(\d+\.?\d*)\s*EUR",
    ]
    for pat in eur_patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return float(m.group(1)), "EUR"

    return None, None


def _parse_moq(text: str) -> int | None:
    """Extract minimum order quantity."""
    patterns = [
        r"MOQ\s*[:：]?\s*(\d+)",
        r"最低.*?(\d+)\s*(?:件|pcs|pieces)",
        r"(\d+)\s*(?:件|pcs).*MOQ",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return int(m.group(1))
    return None


def _parse_material_available(text: str) -> bool | None:
    """Detect material availability."""
    available_patterns = [
        r"材料.*?有现货", r"有现货", r"现货充足",
        r"material.*?available", r"in stock",
        r"有货", r"货充足",
    ]
    unavailable_patterns = [
        r"材料.*?缺", r"缺料", r"材料短缺", r"材料在途",
        r"material.*?shortage", r"out of stock",
        r"无货", r"缺货",
    ]
    for pat in unavailable_patterns:
        if re.search(pat, text, re.IGNORECASE):
            return False
    for pat in available_patterns:
        if re.search(pat, text, re.IGNORECASE):
            return True
    return None


def _parse_red_flags(text: str) -> list[str]:
    """Detect risk flags from supplier message."""
    flags = []
    outsource_patterns = [r"外协", r"outsourc", r"third.?party"]
    delay_patterns = [r"延误", r"delay", r"延期"]
    shortage_patterns = [r"缺料", r"shortage", r"material.*unavailable"]
    capacity_patterns = [r"产能.*满", r"排队", r"backlog", r"over.?capac"]
    holiday_patterns = [r"假期", r"holiday", r"spring festival", r"spring break"]

    tl = text.lower()
    for pat in outsource_patterns:
        if re.search(pat, text, re.IGNORECASE):
            flags.append("outsourcing involved")
            break
    for pat in delay_patterns:
        if re.search(pat, text, re.IGNORECASE):
            flags.append("potential delay flagged")
            break
    for pat in shortage_patterns:
        if re.search(pat, text, re.IGNORECASE):
            flags.append("material shortage risk")
            break
    for pat in capacity_patterns:
        if re.search(pat, text, re.IGNORECASE):
            flags.append("capacity constraint")
            break
    for pat in holiday_patterns:
        if re.search(pat, text, re.IGNORECASE):
            flags.append("holiday delay risk")
            break

    return flags


def _parse_qc_available(text: str) -> bool | None:
    """Detect QC capability."""
    patterns = [r"\bQC\b", r"质检", r"检验", r"inspection", r"照片", r"photo", r"视频", r"video"]
    for pat in patterns:
        if re.search(pat, text, re.IGNORECASE):
            return True
    return None


def _parse_logistics(text: str) -> LogisticsCommitment:
    """Detect logistics terms (EXW/FOB/DDP)."""
    lc = LogisticsCommitment()
    if re.search(r"\bEXW\b", text, re.IGNORECASE):
        lc.exw_supported = True
        lc.logistics_notes = "EXW"
    if re.search(r"\bFOB\b", text, re.IGNORECASE):
        lc.fob_supported = True
        lc.logistics_notes = (lc.logistics_notes + "/FOB") if lc.logistics_notes else "FOB"
    if re.search(r"\bDDP\b", text, re.IGNORECASE):
        lc.ddp_supported = True
        lc.logistics_notes = (lc.logistics_notes + "/DDP") if lc.logistics_notes else "DDP"
    if re.search(r"快递|courier|express", text, re.IGNORECASE):
        lc.logistics_notes = (lc.logistics_notes + "/courier") if lc.logistics_notes else "courier"
    return lc


def _compute_completeness(
    can_make: bool | None,
    lead_time: int | None,
    unit_price: float | None,
    material_available: bool | None,
    moq: int | None,
    qc_available: bool | None,
    logistics: LogisticsCommitment,
) -> float:
    """Compute completeness score (0.0 to 1.0) based on filled key fields."""
    total = 7
    filled = sum([
        can_make is not None,
        lead_time is not None,
        unit_price is not None,
        material_available is not None,
        moq is not None,
        qc_available is not None,
        logistics.exw_supported or logistics.fob_supported or logistics.ddp_supported or False,
    ])
    return round(filled / total, 2)


def _generate_summary(
    supplier_name: str,
    can_make: bool | None,
    lead_time: int | None,
    unit_price: float | None,
    currency: str | None,
    material_available: bool | None,
    red_flags: list[str],
    moq: int | None,
) -> str:
    """Generate a buyer-facing supplier summary."""
    parts = [f"Supplier: {supplier_name}"]
    if can_make is not None:
        parts.append(f"Can make: {'Yes' if can_make else 'No'}")
    if lead_time is not None:
        parts.append(f"Lead time: {lead_time} days")
    if unit_price is not None:
        price_str = f"{currency} {unit_price}" if currency else str(unit_price)
        parts.append(f"Unit price: {price_str}")
    if material_available is not None:
        parts.append(f"Material available: {'Yes' if material_available else 'No (in transit)'}")
    if moq is not None:
        parts.append(f"MOQ: {moq}")
    if red_flags:
        parts.append(f"Red flags: {'; '.join(red_flags)}")
    return " | ".join(parts)


def normalize_supplier_response_text(
    texts: list[str],
    workspace: MSideWorkspace,
) -> SupplierResponsePacket:
    """
    Normalize natural-language supplier replies into a structured SupplierResponsePacket.
    Uses deterministic regex parsing — no LLM required.
    """
    combined = _combined_text(texts)

    can_make = _parse_can_make(combined)
    lead_time = _parse_lead_time(combined)
    sample_lead_time = _parse_sample_lead_time(combined)
    unit_price, currency = _parse_unit_price(combined)
    moq = _parse_moq(combined)
    material_available = _parse_material_available(combined)
    red_flags = _parse_red_flags(combined)
    qc_available = _parse_qc_available(combined)
    logistics = _parse_logistics(combined)

    # Compute total price if quantity available
    total_price = None
    if unit_price is not None and workspace.inquiry_context:
        # Try to get quantity from context - use a default of 500 for CNC
        total_price = unit_price * 500  # placeholder; ideally from BuyerRequirement

    capacity_signal = CapacitySignal(
        can_make=can_make,
        capacity_available=can_make,
        capacity_notes=combined[:200] if not can_make else None,
    )

    # Parse earliest start date
    start_match = re.search(r"(?:下周[一二三四五六日]|下周|next week|Monday|Tuesday|Wednesday)", combined)
    if start_match:
        capacity_signal.earliest_start_date = start_match.group(0)

    schedule_signal = ScheduleSignal(
        estimated_lead_time_days=lead_time,
        sample_lead_time_days=sample_lead_time,
        mass_production_lead_time_days=lead_time,
    )

    material_avail = MaterialAvailability(
        material_available=material_available,
        procurement_days=3 if material_available is False else None,
        material_notes="material in transit" if material_available is False else None,
    )

    quote = SupplierQuote(
        currency=currency,
        unit_price=unit_price,
        total_price=total_price,
        quote_notes=f"MOQ: {moq}" if moq else None,
    )

    qc_commitment = QCCommitment(
        qc_available=qc_available,
        photo_or_video_update_supported=qc_available or False,
    )

    completeness = _compute_completeness(
        can_make, lead_time, unit_price, material_available, moq, qc_available, logistics
    )

    # Confidence based on completeness + no red flags
    confidence = completeness * (0.8 if red_flags else 1.0)

    summary = _generate_summary(
        workspace.supplier_name, can_make, lead_time, unit_price, currency,
        material_available, red_flags, moq
    )

    packet = SupplierResponsePacket(
        response_id=f"RSP-{uuid.uuid4().hex[:8].upper()}",
        m_workspace_id=workspace.m_workspace_id,
        b_workspace_id=workspace.b_workspace_id,
        rfq_id=workspace.rfq_id,
        inquiry_id=workspace.inquiry_id,
        supplier_id=workspace.supplier_id,
        supplier_name=workspace.supplier_name,
        submitted_at=_utcnow(),
        raw_supplier_messages=texts,
        capacity_signal=capacity_signal,
        schedule_signal=schedule_signal,
        material_availability=material_avail,
        quote=quote,
        qc_commitment=qc_commitment,
        logistics_commitment=logistics,
        red_flags=red_flags,
        completeness_score=completeness,
        confidence_score=round(confidence, 2),
        supplier_summary_for_buyer=summary,
    )

    return packet
