"""Tests for QC M-side feedback flow — Chinese-first output."""
import pytest
from src.merchandiser.qc.qc_comparison_engine import compare_media_against_standard
from src.merchandiser.qc.qc_prompt_builder import build_qc_system_prompt, build_qc_user_prompt
from src.llm.mock_provider import MockLLMProvider, _MOCK_QC_RESULT


_PROJECT = "proj-qc-feedback-01"
_MILESTONE = "MILE-QC-FEEDBACK-001"


def test_mock_qc_result_has_chinese_feedback():
    assert _MOCK_QC_RESULT["m_side_feedback_zh"] != ""
    assert any(ord(c) > 127 for c in _MOCK_QC_RESULT["m_side_feedback_zh"]), \
        "m_side_feedback_zh must contain Chinese characters"


def test_compare_returns_chinese_feedback():
    report = compare_media_against_standard(
        project_id=_PROJECT,
        milestone_id=_MILESTONE,
        production_images=[],
        provider_name="mock",
    )
    assert report.m_side_feedback_zh != ""
    assert any(ord(c) > 127 for c in report.m_side_feedback_zh), \
        "m_side_feedback_zh must contain Chinese characters"


def test_compare_returns_english_feedback():
    report = compare_media_against_standard(
        project_id=_PROJECT,
        milestone_id=_MILESTONE,
        production_images=[],
        provider_name="mock",
    )
    assert report.m_side_feedback_en != ""


def test_compare_returns_b_side_summary():
    report = compare_media_against_standard(
        project_id=_PROJECT,
        milestone_id=_MILESTONE,
        production_images=[],
        provider_name="mock",
    )
    assert isinstance(report.b_side_summary, str)


def test_system_prompt_is_chinese_first():
    prompt = build_qc_system_prompt()
    assert any(ord(c) > 127 for c in prompt), "System prompt must contain Chinese"
    assert "QC" in prompt or "qc" in prompt.lower() or "质检" in prompt or "助理" in prompt


def test_user_prompt_includes_milestone_type():
    prompt = build_qc_user_prompt(milestone_type="final_qc")
    assert "final_qc" in prompt


def test_user_prompt_includes_order_requirements():
    prompt = build_qc_user_prompt(order_requirements="100 pcs polo shirt")
    assert "polo shirt" in prompt


def test_user_prompt_includes_image_count():
    prompt = build_qc_user_prompt(standard_image_count=2, production_image_count=3)
    assert "2" in prompt
    assert "3" in prompt


def test_qc_result_severity_valid():
    report = compare_media_against_standard(
        project_id=_PROJECT,
        milestone_id=_MILESTONE,
        production_images=[],
        provider_name="mock",
    )
    assert report.severity in ("low", "medium", "high", "critical", "unknown")


def test_qc_result_score_range():
    report = compare_media_against_standard(
        project_id=_PROJECT,
        milestone_id=_MILESTONE,
        production_images=[],
        provider_name="mock",
    )
    assert 0.0 <= report.overall_score <= 1.0


def test_mock_provider_image_compare_returns_chinese_feedback():
    provider = MockLLMProvider()
    result = provider.compare_images(
        images=["tests/fixtures/multimodal/red_square.png"],
        question="质检对比",
    )
    assert result.result_json.get("m_side_feedback_zh", "") != ""


def test_qc_engine_image_comparison_uses_provider_interface():
    report = compare_media_against_standard(
        project_id=_PROJECT,
        milestone_id=_MILESTONE,
        production_images=["tests/fixtures/multimodal/red_square_with_dot.png"],
        standard_images=["tests/fixtures/multimodal/red_square.png"],
        provider_name="mock",
    )
    assert report.provider_name == "mock"
    assert report.image_count == 2


def test_qc_engine_video_frame_comparison_uses_provider_interface():
    report = compare_media_against_standard(
        project_id=_PROJECT,
        milestone_id=_MILESTONE,
        production_images=[],
        video_frames=[
            "tests/fixtures/multimodal/red_square.png",
            "tests/fixtures/multimodal/red_square_with_dot.png",
        ],
        provider_name="mock",
    )
    assert report.frames_used == 2
    assert report.m_side_feedback_zh != ""
