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
    if any(kw in msg for kw in ["material", "材料", "原料", "缺料", "shortage"]):
        return "material"
    if any(kw in msg for kw in ["delay", "延误", "延期", "推迟", "schedule", "交期"]):
        return "schedule"
    if any(kw in msg for kw in ["quality", "质量", "缺陷", "defect", "qc", "质检"]):
        return "quality"
    if any(kw in msg for kw in ["logistics", "物流", "shipping", "carrier", "运输"]):
        return "logistics"
    if any(kw in msg for kw in ["cost", "price", "成本", "涨价", "surcharge", "费用"]):
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
        "无法交货", "cannot deliver", "no material", "机器故障", "machine broken",
        "buyer must decide", "买家需要决定", "完全无法", "产能已满.*无法接单",
    ]
    for kw in blocking_kw:
        if re.search(kw, message, re.IGNORECASE):
            return "blocking"

    # High severity
    high_kw = [
        r"delay.*\d+\s*weeks?", r"延误.*\d+\s*周",
        "qc failed", "质量不合格", "涨价", "major cost",
        r"延误.*[7-9]\d?\s*天", r"delay.*[7-9]\d?\s*days?",
    ]
    for kw in high_kw:
        if re.search(kw, message, re.IGNORECASE):
            return "high"

    # Medium
    medium_kw = [
        r"delay.*[2-6]\s*天", r"延误.*[2-6]\s*天",
        "outsourc", "外协", "packaging issue", "包装问题",
        "延误", "delay",
    ]
    for kw in medium_kw:
        if re.search(kw, message, re.IGNORECASE):
            return "medium"

    return "low"


def _extract_proposed_options(message: str) -> list[str]:
    """Extract any proposed solutions from the message."""
    options = []

    # Look for numbered options
    numbered = re.findall(r"(?:方案|option|选项|建议)\s*[：:]\s*(.+?)(?:\n|$)", message)
    options.extend(numbered[:3])

    # Look for "can" / "能" suggestions
    suggestions = re.findall(r"(?:可以|能够|建议|suggest|can|recommend)\s*(.{5,40}?)(?:[。,，\n]|$)", message)
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
