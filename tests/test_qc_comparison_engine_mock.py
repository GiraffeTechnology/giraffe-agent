"""Tests for QC comparison engine — mock provider, no real API key required."""
import pytest
from src.merchandiser.qc.qc_comparison_engine import compare_media_against_standard
from src.merchandiser.qc.qc_models import QCComparisonReport
from src.llm.provider_config import DEFAULT_QC_PROVIDER


_PROJECT = "proj-qc-test-01"
_MILESTONE = "MILE-QC-TEST-001"


def test_default_qc_provider_is_qwen():
    assert DEFAULT_QC_PROVIDER == "qwen"


def test_compare_no_images_returns_report():
    report = compare_media_against_standard(
        project_id=_PROJECT,
        milestone_id=_MILESTONE,
        production_images=[],
        provider_name="mock",
    )
    assert isinstance(report, QCComparisonReport)


def test_compare_with_mock_returns_pass():
    report = compare_media_against_standard(
        project_id=_PROJECT,
        milestone_id=_MILESTONE,
        production_images=["tests/fixtures/multimodal/red_square.png"],
        standard_images=["tests/fixtures/multimodal/red_square.png"],
        provider_name="mock",
    )
    assert report.overall_result == "pass"
    assert report.provider_name == "mock"
    assert report.model_name is not None


def test_compare_records_requested_provider_qwen(monkeypatch):
    import os
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    monkeypatch.setenv("LLM_ENABLE_REAL_CALLS", "false")
    report = compare_media_against_standard(
        project_id=_PROJECT,
        milestone_id=_MILESTONE,
        production_images=[],
    )
    assert report.requested_provider == "qwen"


def test_compare_fallback_used_true_when_no_key(monkeypatch):
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    monkeypatch.delenv("QWEN_API_KEY", raising=False)
    monkeypatch.setenv("LLM_ENABLE_REAL_CALLS", "false")
    report = compare_media_against_standard(
        project_id=_PROJECT,
        milestone_id=_MILESTONE,
        production_images=[],
    )
    assert report.fallback_used is True
    assert report.fallback_reason is not None
    assert "qwen" in (report.fallback_reason or "").lower() or "disabled" in (report.fallback_reason or "").lower()


def test_compare_explicit_mock_fallback_used_false():
    report = compare_media_against_standard(
        project_id=_PROJECT,
        milestone_id=_MILESTONE,
        production_images=[],
        provider_name="mock",
    )
    assert report.fallback_used is False


def test_compare_image_count_recorded():
    report = compare_media_against_standard(
        project_id=_PROJECT,
        milestone_id=_MILESTONE,
        production_images=["tests/fixtures/multimodal/red_square.png", "tests/fixtures/multimodal/red_square_with_dot.png"],
        standard_images=["tests/fixtures/multimodal/red_square.png"],
        provider_name="mock",
    )
    assert report.image_count == 3


def test_compare_video_frames():
    report = compare_media_against_standard(
        project_id=_PROJECT,
        milestone_id=_MILESTONE,
        production_images=[],
        video_frames=["tests/fixtures/multimodal/red_square.png", "tests/fixtures/multimodal/red_square_with_dot.png"],
        provider_name="mock",
    )
    assert report.frames_used == 2
    assert isinstance(report, QCComparisonReport)


def test_compare_with_milestone_type():
    report = compare_media_against_standard(
        project_id=_PROJECT,
        milestone_id=_MILESTONE,
        production_images=[],
        milestone_type="final_qc",
        order_requirements="100 pcs polo shirt, white, size M/L/XL",
        process_card_notes="Collar stitching: 3mm. Button spacing: 6cm.",
        provider_name="mock",
    )
    assert isinstance(report, QCComparisonReport)
    assert report.overall_result in ("pass", "needs_fix", "buyer_review_required", "reject", "unknown")


def test_report_has_all_required_fields():
    report = compare_media_against_standard(
        project_id=_PROJECT,
        milestone_id=_MILESTONE,
        production_images=[],
        provider_name="mock",
    )
    assert hasattr(report, "overall_result")
    assert hasattr(report, "overall_score")
    assert hasattr(report, "severity")
    assert hasattr(report, "detected_deviations")
    assert hasattr(report, "process_card_violations")
    assert hasattr(report, "buyer_confirmation_required")
    assert hasattr(report, "human_review_required")
    assert hasattr(report, "m_side_feedback_zh")
    assert hasattr(report, "m_side_feedback_en")
    assert hasattr(report, "b_side_summary")
    assert hasattr(report, "provider_name")
    assert hasattr(report, "model_name")
    assert hasattr(report, "requested_provider")
    assert hasattr(report, "fallback_used")
