"""M-side QC follow-up — sends AI QC comparison feedback to supplier."""
from src.merchandiser.qc.qc_models import QCComparisonReport
from src.merchandiser.qc.qc_feedback_generator import generate_m_side_qc_feedback
from src.m_side.m_event_logger import log_m_event


def request_qc_update(project_id: str, supplier_actor_id: str, stage: str = "final_qc") -> dict:
    msg = f"请上传 {stage.replace('_', ' ')} 检验报告和合格证明。"
    log_m_event(
        event_type="M_QC_UPDATE_REQUESTED",
        b_workspace_id=project_id,
        supplier_id=supplier_actor_id,
        payload={"stage": stage, "message": msg},
    )
    return {"status": "requested", "message": msg}


def send_qc_comparison_feedback_to_m_side(
    project_id: str,
    milestone_id: str,
    report: QCComparisonReport,
    supplier_actor_id: str | None = None,
    milestone_type: str | None = None,
) -> dict:
    """
    Send QC comparison feedback to M-side (supplier).

    Generates Chinese-first feedback and logs the notification.
    OpenClaw message delivery is handled via the openclaw_skill layer.
    """
    feedback = generate_m_side_qc_feedback(report, milestone_type=milestone_type)

    log_m_event(
        event_type="M_SIDE_QC_FEEDBACK_SENT",
        b_workspace_id=project_id,
        supplier_id=supplier_actor_id,
        payload={
            "milestone_id": milestone_id,
            "overall_result": report.overall_result,
            "action_required": feedback["action_required"],
            "severity": report.severity,
            "feedback_zh_preview": feedback["feedback_zh"][:120],
        },
    )

    if feedback["escalate_to_buyer"] and report.severity in ("high", "critical"):
        try:
            from src.merchandiser.exception_manager import raise_exception
            raise_exception(
                project_id=project_id,
                exception_type="qc_failure_escalation",
                description=feedback["feedback_en"][:500],
                raised_by_actor_id=supplier_actor_id,
                severity=report.severity,
            )
        except Exception:
            pass

    return {
        "sent": True,
        "project_id": project_id,
        "milestone_id": milestone_id,
        "feedback": feedback,
    }
