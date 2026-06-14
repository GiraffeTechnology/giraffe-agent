"""
QC policy engine — decide next action from QCComparisonReport.
"""
from src.merchandiser.qc.qc_models import QCComparisonReport


_SCORE_THRESHOLDS = {
    "auto_pass": 0.85,
    "needs_fix": 0.60,
    "buyer_review": 0.40,
}


def decide_qc_action(report: QCComparisonReport) -> dict:
    """
    Decide next action from QCComparisonReport.

    Returns:
        {
            "action": "auto_approve" | "request_rework" | "escalate_to_buyer" | "reject" | "review",
            "reason": str,
            "notify_m_side": bool,
            "notify_b_side": bool,
            "block_progression": bool,
        }
    """
    result = report.overall_result
    score = report.overall_score
    severity = report.severity

    if result == "pass" and score >= _SCORE_THRESHOLDS["auto_pass"]:
        return {
            "action": "auto_approve",
            "reason": "QC passed with high confidence score.",
            "notify_m_side": True,
            "notify_b_side": False,
            "block_progression": False,
        }

    if result == "reject" or severity == "critical":
        return {
            "action": "reject",
            "reason": f"QC result={result}, severity={severity}. Full rework required.",
            "notify_m_side": True,
            "notify_b_side": True,
            "block_progression": True,
        }

    if result == "buyer_review_required" or report.buyer_confirmation_required:
        return {
            "action": "escalate_to_buyer",
            "reason": "QC requires buyer confirmation before progression.",
            "notify_m_side": True,
            "notify_b_side": True,
            "block_progression": True,
        }

    if result == "needs_fix" or severity in ("high", "medium"):
        return {
            "action": "request_rework",
            "reason": f"QC found issues ({severity} severity). M-side rework requested.",
            "notify_m_side": True,
            "notify_b_side": False,
            "block_progression": True,
        }

    # Fallback / unknown
    return {
        "action": "review",
        "reason": f"QC result unclear (result={result}, score={score:.2f}). Human review required.",
        "notify_m_side": True,
        "notify_b_side": False,
        "block_progression": True,
    }
