"""Tests for QC feedback generator."""
import pytest
from src.merchandiser.qc.qc_feedback_generator import generate_m_side_qc_feedback
from src.merchandiser.qc.qc_models import QCComparisonReport, QCDeviation

def _make_report(**kwargs) -> QCComparisonReport:
    defaults = dict(
        overall_result="pass",
        overall_score=0.9,
        severity="low",
        provider_name="mock",
        model_name="mock",
        requested_provider="qwen",
        m_side_feedback_zh="【Mock】检验通过。",
        m_side_feedback_en="[Mock] QC passed.",
    )
    defaults.update(kwargs)
    return QCComparisonReport(**defaults)

def test_pass_report_no_action_required():
    report = _make_report(overall_result="pass", overall_score=0.9)
    fb = generate_m_side_qc_feedback(report)
    assert fb["action_required"] is False
    assert fb["overall_result"] == "pass"

def test_needs_fix_report_action_required():
    report = _make_report(
        overall_result="needs_fix",
        overall_score=0.6,
        severity="medium",
        detected_deviations=[QCDeviation(field="color", severity="medium")],
    )
    fb = generate_m_side_qc_feedback(report)
    assert fb["action_required"] is True

def test_reject_report_action_required():
    report = _make_report(overall_result="reject", severity="critical")
    fb = generate_m_side_qc_feedback(report)
    assert fb["action_required"] is True

def test_buyer_review_required_escalates():
    report = _make_report(
        overall_result="buyer_review_required",
        severity="high",
        buyer_confirmation_required=True,
    )
    fb = generate_m_side_qc_feedback(report)
    assert fb["escalate_to_buyer"] is True

def test_feedback_returns_chinese_text():
    report = _make_report(m_side_feedback_zh="质检通过，无需返工。")
    fb = generate_m_side_qc_feedback(report)
    assert any(ord(c) > 127 for c in fb["feedback_zh"])

def test_feedback_has_required_keys():
    report = _make_report()
    fb = generate_m_side_qc_feedback(report)
    assert "feedback_zh" in fb
    assert "feedback_en" in fb
    assert "action_required" in fb
    assert "escalate_to_buyer" in fb
    assert "severity" in fb
