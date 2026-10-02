# Unicode escapes preserve the original multilingual parser vocabulary.
# This source representation does not translate the accepted input values.
"""
M-side exception handler — classifies and structures exception reports from supplier messages.
"""

from __future__ import annotations
import re
import uuid
from datetime import datetime, timezone

from src.core_schema.m_side_types import ExceptionReport
from src.m_side.m_event_logger import log_m_event


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _classify_category(message: str) -> str:
    """Classify exception category from message keywords."""
    msg = message.lower()
    if any(kw in msg for kw in ["material", '\u6750\u6599', '\u539f\u6599', '\u7f3a\u6599', "shortage"]):
        return "material"
    if any(kw in msg for kw in ["delay", '\u5ef6\u8bef', '\u5ef6\u671f', '\u63a8\u8fdf', "schedule", '\u4ea4\u671f']):
        return "schedule"
    if any(kw in msg for kw in ["quality", '\u8d28\u91cf', '\u7f3a\u9677', "defect", "qc", '\u8d28\u68c0']):
        return "quality"
    if any(kw in msg for kw in ["logistics", '\u7269\u6d41', "shipping", "carrier", '\u8fd0\u8f93']):
        return "logistics"
    if any(kw in msg for kw in ["cost", "price", '\u6210\u672c', '\u6da8\u4ef7', "surcharge", '\u8d39\u7528']):
        return "cost"
    return "other"


def _classify_severity(message: str) -> str:
    """
    Classify exception severity from message keywords.
    blocking: cannot deliver / no material / machine broken / buyer must decide
    high: delay > 7 days / major cost increase / QC failed
    medium: delay 2-7 days / outsource risk / packaging issue
    low: minor note / informational
    """
    msg = message.lower()

    # Blocking
    blocking_kw = [
        '\u65e0\u6cd5\u4ea4\u8d27', "cannot deliver", "no material", '\u673a\u5668\u6545\u969c', "machine broken",
        "buyer must decide", '\u4e70\u5bb6\u9700\u8981\u51b3\u5b9a', '\u5b8c\u5168\u65e0\u6cd5', '\u4ea7\u80fd\u5df2\u6ee1.*\u65e0\u6cd5\u63a5\u5355',
    ]
    for kw in blocking_kw:
        if re.search(kw, message, re.IGNORECASE):
            return "blocking"

    # High severity
    high_kw = [
        r"delay.*\d+\s*weeks?", '\u5ef6\u8bef.*\\d+\\s*\u5468',
        "qc failed", '\u8d28\u91cf\u4e0d\u5408\u683c', '\u6da8\u4ef7', "major cost",
        '\u5ef6\u8bef.*[7-9]\\d?\\s*\u5929', r"delay.*[7-9]\d?\s*days?",
    ]
    for kw in high_kw:
        if re.search(kw, message, re.IGNORECASE):
            return "high"

    # Medium
    medium_kw = [
        'delay.*[2-6]\\s*\u5929', '\u5ef6\u8bef.*[2-6]\\s*\u5929',
        "outsourc", '\u5916\u534f', "packaging issue", '\u5305\u88c5\u95ee\u9898',
        '\u5ef6\u8bef', "delay",
    ]
    for kw in medium_kw:
        if re.search(kw, message, re.IGNORECASE):
            return "medium"

    return "low"


def _extract_proposed_options(message: str) -> list[str]:
    """Extract any proposed solutions from the message."""
    options = []

    # Look for numbered options
    numbered = re.findall('(?:\u65b9\u6848|option|\u9009\u9879|\u5efa\u8bae)\\s*[\uff1a:]\\s*(.+?)(?:\\n|$)', message)
    options.extend(numbered[:3])

    # Look for suggestions phrased with English or Chinese equivalents of "can".
    suggestions = re.findall('(?:\u53ef\u4ee5|\u80fd\u591f|\u5efa\u8bae|suggest|can|recommend)\\s*(.{5,40}?)(?:[\u3002,\uff0c\\n]|$)', message)
    for s in suggestions[:2]:
        if s not in options:
            options.append(s.strip())

    return options[:3]


def submit_exception_report(
    m_workspace_id: str,
    supplier_id: str,
    message: str,
    order_execution_id: str | None = None,
) -> ExceptionReport:
    """
    Create a structured exception report from a supplier message.
    Classifies severity and category automatically.
    """
    category = _classify_category(message)
    severity = _classify_severity(message)
    proposed_options = _extract_proposed_options(message)

    report = ExceptionReport(
        exception_id=f"EXC-{uuid.uuid4().hex[:8].upper()}",
        order_execution_id=order_execution_id,
        m_workspace_id=m_workspace_id,
        supplier_id=supplier_id,
        severity=severity,
        category=category,
        message=message,
        proposed_options=proposed_options,
        created_at=_utcnow(),
    )

    log_m_event(
        event_type="M_EXCEPTION_REPORTED",
        m_workspace_id=m_workspace_id,
        supplier_id=supplier_id,
        order_execution_id=order_execution_id,
        payload={
            "severity": severity,
            "category": category,
            "message": message[:300],
        },
    )

    return report
