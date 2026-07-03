"""
Logistics IM message parser — extracts carrier and tracking number from free-text IM messages.
Supports Chinese (SF Express, 顺丰, etc.) and English formats.
"""
from __future__ import annotations
import re
from dataclasses import dataclass

from src.logistics.providers.carrier_mapping import CARRIER_NAME_TO_CODE, normalize_carrier_name


@dataclass
class LogisticsInfoExtract:
    carrier_name: str | None
    carrier_code: str | None
    tracking_number: str | None
    shipping_date_text: str | None
    confidence_score: float
    evidence_text: str


_TRACKING_PATTERNS = [
    # SF Express: SF + 12 digits
    r'\bSF\d{12}\b',
    # ZTO, YTO, etc.: letters + 10-20 digits
    r'\b[A-Z]{2,6}\d{10,20}\b',
    # Pure digit tracking numbers: 10-20 digits
    r'\b\d{10,20}\b',
    # DHL, UPS: mixed alphanumeric
    r'\b[A-Z0-9]{10,25}\b',
]

_KEYWORDS_ZH = {
    "已发": "shipped",
    "发出": "shipped",
    "寄出": "shipped",
    "单号": "tracking",
    "运单": "tracking",
    "快递": "express",
}

_DATE_PATTERNS = [
    r'今天',
    r'today',
    r'\d{4}-\d{2}-\d{2}',
    r'\d{1,2}/\d{1,2}',
]


def extract_logistics_info_from_im(raw_message: str) -> LogisticsInfoExtract:
    carrier_name = None
    carrier_code = None
    tracking_number = None
    shipping_date_text = None
    confidence = 0.0

    # Try to find carrier name
    for name, code in CARRIER_NAME_TO_CODE.items():
        if name.lower() in raw_message.lower() or name in raw_message:
            carrier_name_raw = name
            carrier_name, carrier_code = normalize_carrier_name(name)
            confidence += 0.3
            break

    # Try to find tracking number
    for pattern in _TRACKING_PATTERNS:
        matches = re.findall(pattern, raw_message, re.IGNORECASE)
        if matches:
            # Prefer longer matches, filter out short noise
            valid = [m for m in matches if len(m) >= 8]
            if valid:
                tracking_number = max(valid, key=len)
                confidence += 0.4
                break

    # Look for shipping date
    for dp in _DATE_PATTERNS:
        dm = re.search(dp, raw_message)
        if dm:
            shipping_date_text = dm.group(0)
            confidence += 0.1
            break

    # Boost confidence if Chinese logistics keywords present
    for kw in _KEYWORDS_ZH:
        if kw in raw_message:
            confidence = min(confidence + 0.1, 1.0)
            break

    confidence = min(round(confidence, 2), 1.0)
    if tracking_number and carrier_code:
        confidence = max(confidence, 0.85)
    elif tracking_number:
        confidence = max(confidence, 0.6)

    return LogisticsInfoExtract(
        carrier_name=carrier_name,
        carrier_code=carrier_code,
        tracking_number=tracking_number,
        shipping_date_text=shipping_date_text,
        confidence_score=confidence,
        evidence_text=raw_message[:200],
    )
