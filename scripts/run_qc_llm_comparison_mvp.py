#!/usr/bin/env python
"""
QC LLM Comparison MVP — verifies end-to-end QC flow with mock provider.
Always passes without real API key. Used in CI.

Run: uv run python scripts/run_qc_llm_comparison_mvp.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.merchandiser.qc.qc_comparison_engine import compare_media_against_standard
from src.merchandiser.qc.qc_models import QCComparisonReport
from src.llm.provider_registry import get_llm_provider
from src.llm.provider_config import DEFAULT_LLM_PROVIDER, DEFAULT_QC_PROVIDER
from src.llm.mock_provider import MockLLMProvider

passed = 0
failed = 0

def check(name, condition, detail=""):
    global passed, failed
    if condition:
        print(f"  ✓ {name}")
        passed += 1
    else:
        print(f"  ✗ {name}" + (f": {detail}" if detail else ""))
        failed += 1


print("=" * 70)
print("QC LLM COMPARISON MVP")
print("=" * 70)

print("\n--- Step 1: Provider config defaults ---")
check("DEFAULT_LLM_PROVIDER is qwen", DEFAULT_LLM_PROVIDER == "qwen")
check("DEFAULT_QC_PROVIDER is qwen", DEFAULT_QC_PROVIDER == "qwen")

print("\n--- Step 2: Qwen without key falls back to mock ---")
os.environ.pop("DASHSCOPE_API_KEY", None)
os.environ.pop("QWEN_API_KEY", None)
os.environ["LLM_ENABLE_REAL_CALLS"] = "false"
provider = get_llm_provider("qwen")
check("Qwen fallback returns MockLLMProvider", isinstance(provider, MockLLMProvider))
check("provider.provider_name == mock", provider.provider_name == "mock")

print("\n--- Step 3: Mock provider text completion ---")
result = provider.complete_text("Test prompt")
check("complete_text returns text", bool(result.text))
check("complete_text provider_name == mock", result.provider_name == "mock")

print("\n--- Step 4: Mock provider extract_json ---")
json_result = provider.extract_json("Extract QC data")
check("extract_json returns dict", isinstance(json_result.data, dict))
check("json_result has overall_result", "overall_result" in json_result.data)

print("\n--- Step 5: Mock provider image comparison ---")
img_result = provider.compare_images(
    images=["tests/fixtures/multimodal/red_square.png", "tests/fixtures/multimodal/red_square_with_dot.png"],
    question="Are these images identical?",
)
check("compare_images returns result", img_result is not None)
check("result has m_side_feedback_zh", bool(img_result.result_json.get("m_side_feedback_zh")))
check("Chinese feedback present", any(ord(c) > 127 for c in img_result.result_json.get("m_side_feedback_zh", "")))

print("\n--- Step 6: Mock provider video frame comparison ---")
vid_result = provider.compare_video_frames(
    frames=["tests/fixtures/multimodal/red_square.png", "tests/fixtures/multimodal/red_square_with_dot.png"],
    question="Compare these video frames for QC",
)
check("compare_video_frames returns result", vid_result is not None)
check("frames_used == 2", vid_result.frames_used == 2)

print("\n--- Step 7: QC comparison engine (no images) ---")
report = compare_media_against_standard(
    project_id="PROJ-QC-MVP-01",
    milestone_id="MILE-QC-MVP-01",
    production_images=[],
    provider_name="mock",
)
check("report is QCComparisonReport", isinstance(report, QCComparisonReport))
check("report.provider_name == mock", report.provider_name == "mock")
check("report.requested_provider == mock", report.requested_provider == "mock")
check("fallback_used is False (explicit mock)", report.fallback_used is False)

print("\n--- Step 8: QC engine with images ---")
report2 = compare_media_against_standard(
    project_id="PROJ-QC-MVP-02",
    milestone_id="MILE-QC-MVP-02",
    production_images=["tests/fixtures/multimodal/red_square_with_dot.png"],
    standard_images=["tests/fixtures/multimodal/red_square.png"],
    milestone_type="final_qc",
    order_requirements="Red square product, no defects",
    process_card_notes="Surface must be uniform colour, no dots",
    provider_name="mock",
)
check("report2.image_count == 2", report2.image_count == 2)
check("report2.m_side_feedback_zh not empty", bool(report2.m_side_feedback_zh))
check("report2.m_side_feedback_en not empty", bool(report2.m_side_feedback_en))
check("report2.b_side_summary is str", isinstance(report2.b_side_summary, str))

print("\n--- Step 9: QC engine defaults to qwen as requested_provider ---")
os.environ.pop("DASHSCOPE_API_KEY", None)
os.environ.pop("QC_AUTO_COMPARE_PROVIDER", None)
os.environ["LLM_ENABLE_REAL_CALLS"] = "false"
report3 = compare_media_against_standard(
    project_id="PROJ-QC-MVP-03",
    milestone_id="MILE-QC-MVP-03",
    production_images=[],
)
check("requested_provider == qwen by default", report3.requested_provider == "qwen")
check("fallback_used == True (no key)", report3.fallback_used is True)
check("fallback_reason mentions qwen or disabled", "qwen" in (report3.fallback_reason or "") or "disabled" in (report3.fallback_reason or ""))

print("\n--- Step 10: Video frame QC flow ---")
report4 = compare_media_against_standard(
    project_id="PROJ-QC-MVP-04",
    milestone_id="MILE-QC-MVP-04",
    production_images=[],
    video_frames=[
        "tests/fixtures/multimodal/red_square.png",
        "tests/fixtures/multimodal/red_square_with_dot.png",
    ],
    milestone_type="in_process_qc",
    provider_name="mock",
)
check("frames_used == 2", report4.frames_used == 2)
check("video report has chinese feedback", any(ord(c) > 127 for c in report4.m_side_feedback_zh))

print("\n" + "=" * 70)
print(f"QC LLM COMPARISON MVP COMPLETE: {passed} passed, {failed} failed")
print("=" * 70)

if failed:
    sys.exit(1)
