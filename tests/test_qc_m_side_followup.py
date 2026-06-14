"""Tests for M-side QC follow-up."""
import pytest
from src.merchandiser.m_side.m_qc_followup import send_qc_comparison_feedback_to_m_side
from src.merchandiser.qc.qc_models import QCComparisonReport

def _make_report(**kwargs) -> QCComparisonReport:
    defaults = dict(
        overall_result="pass",
        overall_score=0.9,
        severity="low",
        provider_name="mock",
        model_name="mock",
        requested_provider="qwen",
        m_side_feedback_zh="质检通过",
        m_side_feedback_en="QC passed",
    )
    defaults.update(kwargs)
    return QCComparisonReport(**defaults)

def test_send_qc_feedback_returns_sent_true():
    report = _make_report()
    result = send_qc_comparison_feedback_to_m_side(
        project_id="PROJ-MFEEDBACK-01",
        milestone_id="MILE-001",
        report=report,
        supplier_actor_id="SUPP-001",
    )
    assert result["sent"] is True

def test_send_qc_feedback_has_feedback_dict():
    report = _make_report()
    result = send_qc_comparison_feedback_to_m_side("PROJ-MFEEDBACK-02", "MILE-002", report)
    assert "feedback" in result
    assert "feedback_zh" in result["feedback"]

def test_send_critical_qc_feedback_does_not_raise():
    report = _make_report(overall_result="reject", severity="critical", buyer_confirmation_required=True)
    result = send_qc_comparison_feedback_to_m_side("PROJ-MFEEDBACK-CRIT-01", "MILE-CRIT-01", report)
    assert result["sent"] is True
