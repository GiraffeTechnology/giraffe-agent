"""Tests for B-side QC review escalation."""
import pytest
from src.merchandiser.b_side.b_qc_review import escalate_qc_to_buyer, receive_buyer_qc_decision
from src.merchandiser.qc.qc_models import QCComparisonReport

def _make_report(**kwargs) -> QCComparisonReport:
    defaults = dict(
        overall_result="buyer_review_required",
        overall_score=0.6,
        severity="high",
        provider_name="mock",
        model_name="mock",
        requested_provider="qwen",
        b_side_summary="QC issue: color deviation detected.",
    )
    defaults.update(kwargs)
    return QCComparisonReport(**defaults)

def test_escalate_qc_to_buyer_returns_escalated_true():
    report = _make_report()
    result = escalate_qc_to_buyer(
        project_id="PROJ-BQCREV-01",
        milestone_id="MILE-001",
        report=report,
        buyer_actor_id="ACT-BUYER-001",
    )
    assert result["escalated"] is True

def test_escalate_qc_includes_b_side_summary():
    report = _make_report()
    result = escalate_qc_to_buyer("PROJ-BQCREV-02", "MILE-002", report)
    assert result["b_side_summary"] != ""

def test_receive_buyer_qc_decision_approve():
    result = receive_buyer_qc_decision(
        project_id="PROJ-BQCREV-03",
        milestone_id="MILE-003",
        buyer_actor_id="ACT-BUYER-001",
        decision="approve",
        notes="Acceptable for this batch",
    )
    assert result["decision"] == "approve"

def test_receive_buyer_qc_decision_reject():
    result = receive_buyer_qc_decision("PROJ-BQCREV-04", "MILE-004", "ACT-BUYER-001", "reject")
    assert result["decision"] == "reject"
