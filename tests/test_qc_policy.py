"""Tests for QC policy engine."""
import pytest
from src.merchandiser.qc.qc_policy import decide_qc_action
from src.merchandiser.qc.qc_models import QCComparisonReport

def _make_report(**kwargs) -> QCComparisonReport:
    defaults = dict(
        overall_result="pass",
        overall_score=0.9,
        severity="low",
        provider_name="mock",
        model_name="mock",
        requested_provider="qwen",
    )
    defaults.update(kwargs)
    return QCComparisonReport(**defaults)

def test_high_score_pass_auto_approves():
    report = _make_report(overall_result="pass", overall_score=0.90)
    action = decide_qc_action(report)
    assert action["action"] == "auto_approve"
    assert action["block_progression"] is False

def test_needs_fix_requests_rework():
    report = _make_report(overall_result="needs_fix", severity="medium", overall_score=0.65)
    action = decide_qc_action(report)
    assert action["action"] == "request_rework"
    assert action["block_progression"] is True
    assert action["notify_m_side"] is True

def test_buyer_review_required_escalates():
    report = _make_report(
        overall_result="buyer_review_required",
        buyer_confirmation_required=True,
        severity="medium",
    )
    action = decide_qc_action(report)
    assert action["action"] == "escalate_to_buyer"
    assert action["notify_b_side"] is True

def test_critical_severity_rejects():
    report = _make_report(overall_result="reject", severity="critical")
    action = decide_qc_action(report)
    assert action["action"] == "reject"
    assert action["block_progression"] is True

def test_unknown_result_returns_review():
    report = _make_report(overall_result="unknown", overall_score=0.3)
    action = decide_qc_action(report)
    assert action["action"] == "review"
