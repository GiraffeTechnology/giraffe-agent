#!/usr/bin/env python
"""
Qwen QC smoke test — real API call (skipped if key absent or real calls disabled).

Run: uv run python scripts/run_qwen_qc_smoke_test.py

Expected output (no key / real calls off):
  QWEN REAL CALL SKIPPED: missing API key
  or
  QWEN REAL CALL SKIPPED: real calls disabled

Expected output (with key and LLM_ENABLE_REAL_CALLS=true):
  QWEN QC SMOKE TEST: PASS
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.llm.provider_config import get_qwen_api_key, LLM_ENABLE_REAL_CALLS

api_key = get_qwen_api_key()

if not api_key:
    print("QWEN REAL CALL SKIPPED: missing API key")
    print("  Set DASHSCOPE_API_KEY or QWEN_API_KEY to enable real Qwen calls.")
    sys.exit(0)

if not LLM_ENABLE_REAL_CALLS:
    print("QWEN REAL CALL SKIPPED: real calls disabled")
    print("  Set LLM_ENABLE_REAL_CALLS=true to enable real Qwen calls.")
    sys.exit(0)

print("QWEN API KEY: present")
print("LLM_ENABLE_REAL_CALLS: true")
print("Running real Qwen QC smoke test...")

try:
    from src.merchandiser.qc.qc_comparison_engine import compare_media_against_standard

    report = compare_media_against_standard(
        project_id="PROJ-QWEN-SMOKE",
        milestone_id="MILE-QWEN-SMOKE",
        production_images=["tests/fixtures/multimodal/red_square_with_dot.png"],
        standard_images=["tests/fixtures/multimodal/red_square.png"],
        milestone_type="final_qc",
        order_requirements="Red square, no defects, uniform colour",
        process_card_notes="Surface must be solid red, no dots or blemishes",
        provider_name="qwen",
    )

    assert report.provider_name == "qwen", f"Expected qwen, got {report.provider_name}"
    assert report.requested_provider == "qwen"
    assert report.fallback_used is False, "Expected real Qwen call, not mock"
    assert report.overall_result in ("pass", "needs_fix", "buyer_review_required", "reject", "unknown"), \
        f"Unexpected result: {report.overall_result}"
    assert isinstance(report.m_side_feedback_zh, str) and len(report.m_side_feedback_zh) > 0, \
        "Missing Chinese M-side feedback"
    assert isinstance(report.m_side_feedback_en, str), "Missing English M-side feedback"

    print(f"  overall_result:     {report.overall_result}")
    print(f"  overall_score:      {report.overall_score:.2f}")
    print(f"  severity:           {report.severity}")
    print(f"  provider:           {report.provider_name}")
    print(f"  model:              {report.model_name}")
    print(f"  m_side_feedback_zh: {report.m_side_feedback_zh[:120]}")
    print(f"  m_side_feedback_en: {report.m_side_feedback_en[:120]}")
    print(f"  b_side_summary:     {report.b_side_summary[:120]}")

    print("\nQWEN QC SMOKE TEST: PASS")

except Exception as e:
    print(f"\nQWEN QC SMOKE TEST: FAIL")
    print(f"  Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
