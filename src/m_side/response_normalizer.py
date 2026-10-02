# Unicode escapes preserve the original multilingual parser vocabulary.
# This source representation does not translate the accepted input values.
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
        '\u53ef\u4ee5\u505a', '\u53ef\u4ee5\u63a5', '\u80fd\u505a', '\u80fd\u63a5', '\u63a5\u5355', '\u53ef\u4ee5\u751f\u4ea7',
        r"\bcan make\b", r"\bwe can\b", r"\byes\b", r"\bconfirm\b",
        '\u53ef\u4ee5', '\u6ca1\u95ee\u9898',
    ]
    no_patterns = [
        '\u4e0d\u80fd\u505a', '\u65e0\u6cd5\u505a', '\u505a\u4e0d\u4e86', '\u4e0d\u63a5', '\u65e0\u6cd5\u63a5\u5355', '\u4ea7\u80fd\u5df2\u6ee1',
        r"\bcannot make\b", r"\bcan't make\b", r"\bno capacity\b",
        '\u62b1\u6b49.*\u65e0\u6cd5', '\u62b1\u6b49.*\u4e0d\u80fd', '\u5f53\u524d\u4ea7\u80fd\u5df2\u6ee1',
    ]
    for pat in no_patterns:
        if re.search(pat, text, re.IGNORECASE):
            return False
    for pat in yes_patterns:
        if re.search(pat, text, re.IGNORECASE):
            return True
    return None


def _parse_lead_time(text: str) -> int | None:
    """Extract lead time in days. Supports day/week units in English and Chinese."""
    # Look for "total X days" type patterns first
    total_patterns = [
        '\u603b\u4ea4\u671f\\s*(\\d+)\\s*\u5929',
        '\u603b\u5171\\s*(\\d+)\\s*\u5929',
        r"total.*?(\d+)\s*days?",
    ]
    for pat in total_patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return int(m.group(1))

    # Generic days pattern
    day_patterns = [
        '\u5927\u8d27\\s*(\\d+)\\s*\u5929',
        '(\\d+)\\s*\u5929\u4ea4\u8d27',
        '\u4ea4\u671f.*?(\\d+)\\s*\u5929',
        '(\\d+)\\s*(?:\u5929|days?|\u65e5)(?:\\s*\u4ea4\u8d27)?',
    ]
    for pat in day_patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            val = int(m.group(1))
            if 1 <= val <= 365:
                return val

    # Weeks pattern
    week_patterns = [
        '(\\d+)\\s*(?:\u5468|weeks?)',
    ]
    for pat in week_patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return int(m.group(1)) * 7

    return None


def _parse_sample_lead_time(text: str) -> int | None:
    """Extract sample/prototype lead time."""
    patterns = [
        '\u6837\u54c1\\s*(\\d+)\\s*\u5929',
        r"sample.*?(\d+)\s*days?",
        '\u6253\u6837\\s*(\\d+)\\s*\u5929',
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
        '(\\d+\\.?\\d*)\\s*\u7f8e\u5143',
        '\u5355\u4ef7\\s*USD\\s*(\\d+\\.?\\d*)',
        '\u5355\u4ef7\\s*(\\d+\\.?\\d*)\\s*(?:USD|\u7f8e\u5143)',
    ]
    for pat in usd_patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return float(m.group(1)), "USD"

    # RMB/CNY patterns
    rmb_patterns = [
        r"RMB\s*(\d+\.?\d*)",
        r"CNY\s*(\d+\.?\d*)",
        '(\\d+\\.?\\d*)\\s*(?:RMB|CNY|\u5143|\u4eba\u6c11\u5e01)',
        '\u5355\u4ef7\\s*(\\d+\\.?\\d*)\\s*\u5143',
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
        '\u6700\u4f4e.*?(\\d+)\\s*(?:\u4ef6|pcs|pieces)',
        '(\\d+)\\s*(?:\u4ef6|pcs).*MOQ',
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return int(m.group(1))
    return None


def _parse_material_available(text: str) -> bool | None:
    """Detect material availability."""
    available_patterns = [
        '\u6750\u6599.*?\u6709\u73b0\u8d27', '\u6709\u73b0\u8d27', '\u73b0\u8d27\u5145\u8db3',
        r"material.*?available", r"in stock",
        '\u6709\u8d27', '\u8d27\u5145\u8db3',
    ]
    unavailable_patterns = [
        '\u6750\u6599.*?\u7f3a', '\u7f3a\u6599', '\u6750\u6599\u77ed\u7f3a', '\u6750\u6599\u5728\u9014',
        r"material.*?shortage", r"out of stock",
        '\u65e0\u8d27', '\u7f3a\u8d27',
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
    outsource_patterns = ['\u5916\u534f', r"outsourc", r"third.?party"]
    delay_patterns = ['\u5ef6\u8bef', r"delay", '\u5ef6\u671f']
    shortage_patterns = ['\u7f3a\u6599', r"shortage", r"material.*unavailable"]
    capacity_patterns = ['\u4ea7\u80fd.*\u6ee1', '\u6392\u961f', r"backlog", r"over.?capac"]
    holiday_patterns = ['\u5047\u671f', r"holiday", r"spring festival", r"spring break"]

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
    patterns = [r"\bQC\b", '\u8d28\u68c0', '\u68c0\u9a8c', r"inspection", '\u7167\u7247', r"photo", '\u89c6\u9891', r"video"]
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
    if re.search('\u5feb\u9012|courier|express', text, re.IGNORECASE):
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
    start_match = re.search('(?:\u4e0b\u5468[\u4e00\u4e8c\u4e09\u56db\u4e94\u516d\u65e5]|\u4e0b\u5468|next week|Monday|Tuesday|Wednesday)', combined)
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
