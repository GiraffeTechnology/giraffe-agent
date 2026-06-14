"""
QC feedback generator — formats Chinese/English M-side feedback from QCComparisonReport.
"""
from src.merchandiser.qc.qc_models import QCComparisonReport


def generate_m_side_qc_feedback(report: QCComparisonReport, milestone_type: str | None = None) -> dict:
    """
    Generate structured M-side feedback dict from a QCComparisonReport.

    Returns:
        {
            "feedback_zh": str,   # Chinese-first
            "feedback_en": str,
            "action_required": bool,
            "escalate_to_buyer": bool,
            "severity": str,
        }
    """
    has_deviations = bool(report.detected_deviations)
    is_serious = report.severity in ("high", "critical")

    if report.overall_result == "pass":
        feedback_zh = report.m_side_feedback_zh or "质检通过，无需返工。"
        feedback_en = report.m_side_feedback_en or "QC passed. No rework required."
        action_required = False
    elif report.overall_result == "needs_fix":
        issues = "；".join(
            f"{d.field}（{d.severity}）" for d in report.detected_deviations
        ) if has_deviations else "请参见质检报告"
        feedback_zh = report.m_side_feedback_zh or f"发现需整改问题：{issues}。请整改后重新提交质检图片。"
        feedback_en = report.m_side_feedback_en or f"Issues found: {issues}. Please fix and resubmit QC images."
        action_required = True
    elif report.overall_result == "buyer_review_required":
        feedback_zh = report.m_side_feedback_zh or "质检发现偏差，已升级至买家确认。请等候买家反馈。"
        feedback_en = report.m_side_feedback_en or "Deviations found. Escalated to buyer for review."
        action_required = True
    elif report.overall_result == "reject":
        feedback_zh = report.m_side_feedback_zh or "质检未通过，需全面返工。请联系品控专员。"
        feedback_en = report.m_side_feedback_en or "QC failed. Full rework required. Contact QC team."
        action_required = True
    else:
        feedback_zh = report.m_side_feedback_zh or "质检结果待确认，请补充清晰图片以便复核。"
        feedback_en = report.m_side_feedback_en or "QC result unclear. Please submit clearer images for review."
        action_required = True

    return {
        "feedback_zh": feedback_zh,
        "feedback_en": feedback_en,
        "action_required": action_required,
        "escalate_to_buyer": report.buyer_confirmation_required or is_serious,
        "severity": report.severity,
        "overall_result": report.overall_result,
    }
