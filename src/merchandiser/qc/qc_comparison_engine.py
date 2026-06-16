"""
QC comparison engine — AI-assisted milestone media review.
Default provider: Qwen (Chinese-first, DashScope vision).

Usage:
    from src.merchandiser.qc.qc_comparison_engine import compare_media_against_standard

    report = compare_media_against_standard(
        project_id="PROJ-001",
        milestone_id="MILE-001",
        milestone_type="final_qc",
        production_images=["path/to/prod1.jpg", "path/to/prod2.jpg"],
        standard_images=["path/to/standard1.jpg"],
    )
"""
import os
from src.llm.provider_registry import get_llm_provider
from src.llm.mock_provider import MockLLMProvider
from src.merchandiser.qc.qc_models import QCComparisonReport, QCDeviation
from src.merchandiser.qc.qc_prompt_builder import build_qc_system_prompt, build_qc_user_prompt
from src.m_side.m_event_logger import log_m_event


def _parse_deviations(raw: list) -> list[QCDeviation]:
    result = []
    for item in raw:
        if isinstance(item, dict):
            result.append(QCDeviation(
                field=item.get("field", ""),
                expected=item.get("expected"),
                actual=item.get("actual"),
                severity=item.get("severity", "medium"),
                note=item.get("note"),
            ))
    return result


def compare_media_against_standard(
    project_id: str,
    milestone_id: str,
    production_images: list[str],
    standard_images: list[str] | None = None,
    milestone_type: str | None = None,
    order_requirements: str | None = None,
    process_card_notes: str | None = None,
    provider_name: str | None = None,
    video_frames: list[str] | None = None,
) -> QCComparisonReport:
    """
    Run AI QC comparison of production media against standard images.

    Args:
        project_id: Project identifier (for logging).
        milestone_id: Milestone being reviewed.
        production_images: Paths/URLs of supplier-uploaded images.
        standard_images: Paths/URLs of approved sample / golden sample images.
        milestone_type: e.g. "final_qc", "cutting", "packaging".
        order_requirements: Free-text order requirements.
        process_card_notes: Process card details.
        provider_name: Override provider (defaults to QC_AUTO_COMPARE_PROVIDER or "qwen").
        video_frames: Sampled video frames (if video QC, pass instead of/alongside images).

    Returns:
        QCComparisonReport with structured result and Chinese M-side feedback.
    """
    requested_provider = provider_name or os.getenv("QC_AUTO_COMPARE_PROVIDER", "qwen")
    provider = get_llm_provider(requested_provider)

    fallback_used = isinstance(provider, MockLLMProvider) and requested_provider != "mock"
    fallback_reason: str | None = None
    if fallback_used:
        fallback_reason = "missing_qwen_api_key_or_real_calls_disabled"

    std_images = standard_images or []
    all_images = std_images + production_images

    system_prompt = build_qc_system_prompt()
    user_prompt = build_qc_user_prompt(
        milestone_type=milestone_type,
        order_requirements=order_requirements,
        process_card_notes=process_card_notes,
        standard_image_count=len(std_images),
        production_image_count=len(production_images),
    )

    log_m_event(
        event_type="QC_COMPARISON_STARTED",
        b_workspace_id=project_id,
        payload={
            "milestone_id": milestone_id,
            "provider": requested_provider,
            "image_count": len(all_images),
            "video_frames": len(video_frames or []),
            "fallback_used": fallback_used,
        },
    )

    frames = video_frames or []
    try:
        if frames:
            llm_result = provider.compare_video_frames(frames, user_prompt, system_prompt=system_prompt)
            raw = llm_result.result_json
            raw_text = llm_result.raw_text
            model_name = llm_result.model_name
            frames_used = llm_result.frames_used
            image_count = len(all_images)
        elif all_images:
            llm_result = provider.compare_images(all_images, user_prompt, system_prompt=system_prompt)
            raw = llm_result.result_json
            raw_text = llm_result.raw_text
            model_name = llm_result.model_name
            frames_used = 0
            image_count = len(all_images)
        else:
            from src.llm.provider_base import LLMJsonResult
            json_result = provider.extract_json(user_prompt, system_prompt=system_prompt)
            raw = json_result.data
            raw_text = json_result.raw_text
            model_name = json_result.model_name
            frames_used = 0
            image_count = 0
    except Exception as exc:
        error_msg = str(exc)
        return QCComparisonReport(
            overall_result="unknown",
            overall_score=0.0,
            severity="critical",
            detected_deviations=[],
            process_card_violations=[],
            buyer_confirmation_required=False,
            human_review_required=True,
            m_side_feedback_zh=f"QC比对失败，图片处理或API调用出错：{error_msg}",
            m_side_feedback_en=f"QC comparison failed due to image processing or API error: {error_msg}",
            b_side_summary=f"QC comparison could not be completed: {error_msg}",
            provider_name=provider.provider_name,
            model_name=getattr(provider, "vision_model", "unknown"),
            requested_provider=requested_provider,
            fallback_used=fallback_used,
            fallback_reason=error_msg,
            image_count=len(all_images),
            frames_used=0,
            raw_llm_text=error_msg,
        )

    report = QCComparisonReport(
        overall_result=raw.get("overall_result", "unknown"),
        overall_score=float(raw.get("overall_score", 0.0)),
        severity=raw.get("severity", "unknown"),
        detected_deviations=_parse_deviations(raw.get("detected_deviations", [])),
        process_card_violations=raw.get("process_card_violations", []),
        buyer_confirmation_required=bool(raw.get("buyer_confirmation_required", False)),
        human_review_required=bool(raw.get("human_review_required", False)),
        m_side_feedback_zh=raw.get("m_side_feedback_zh", ""),
        m_side_feedback_en=raw.get("m_side_feedback_en", ""),
        b_side_summary=raw.get("b_side_summary", ""),
        provider_name=provider.provider_name,
        model_name=model_name,
        requested_provider=requested_provider,
        fallback_used=fallback_used,
        fallback_reason=fallback_reason,
        image_count=image_count,
        frames_used=frames_used,
        raw_llm_text=raw_text,
    )

    log_m_event(
        event_type="QC_COMPARISON_COMPLETED",
        b_workspace_id=project_id,
        payload={
            "milestone_id": milestone_id,
            "overall_result": report.overall_result,
            "provider": provider.provider_name,
            "model": model_name,
            "fallback_used": fallback_used,
        },
    )

    return report
