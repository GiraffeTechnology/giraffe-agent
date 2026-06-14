"""
B-side QC review — escalates QC issues requiring buyer confirmation.
"""
from src.merchandiser.qc.qc_models import QCComparisonReport
from src.m_side.m_event_logger import log_m_event


def escalate_qc_to_buyer(
    project_id: str,
    milestone_id: str,
    report: QCComparisonReport,
    buyer_actor_id: str | None = None,
) -> dict:
    """
    Escalate a QC report to the buyer for review.

    Logs the escalation event and returns a summary for the buyer.
    """
    b_side_summary = report.b_side_summary or (
        f"QC result: {report.overall_result} (score: {report.overall_score:.0%}). "
        f"Severity: {report.severity}. Please review the attached QC report."
    )

    log_m_event(
        event_type="QC_ESCALATED_TO_BUYER",
        b_workspace_id=project_id,
        supplier_id=buyer_actor_id,
        payload={
            "milestone_id": milestone_id,
            "overall_result": report.overall_result,
            "severity": report.severity,
            "buyer_actor_id": buyer_actor_id,
        },
    )

    return {
        "escalated": True,
        "project_id": project_id,
        "milestone_id": milestone_id,
        "buyer_actor_id": buyer_actor_id,
        "b_side_summary": b_side_summary,
        "overall_result": report.overall_result,
        "severity": report.severity,
    }


def receive_buyer_qc_decision(
    project_id: str,
    milestone_id: str,
    buyer_actor_id: str,
    decision: str,
    notes: str = "",
) -> dict:
    """
    Record buyer's QC review decision.

    decision: "approve" | "reject" | "rework_required"
    """
    log_m_event(
        event_type="BUYER_QC_DECISION_RECEIVED",
        b_workspace_id=project_id,
        supplier_id=buyer_actor_id,
        payload={
            "milestone_id": milestone_id,
            "decision": decision,
            "notes": notes[:200] if notes else "",
        },
    )
    return {
        "project_id": project_id,
        "milestone_id": milestone_id,
        "buyer_actor_id": buyer_actor_id,
        "decision": decision,
        "notes": notes,
    }
