"""
Mock LLM provider — deterministic, no API key required.
Used in local/test mode when real provider key is absent or real calls disabled.
"""
import json
from src.llm.provider_base import (
    MultimodalLLMProviderBase,
    LLMTextResult, LLMJsonResult, LLMImageCompareResult, LLMVideoCompareResult,
)

_MOCK_QC_RESULT = {
    "overall_result": "pass",
    "overall_score": 0.85,
    "severity": "low",
    "detected_deviations": [],
    "process_card_violations": [],
    "buyer_confirmation_required": False,
    "human_review_required": False,
    "m_side_feedback_zh": "【Mock】图片已收到，外观检查通过，无明显异常。",
    "m_side_feedback_en": "[Mock] Images received. Visual check passed. No obvious deviations detected.",
    "b_side_summary": "[Mock] QC passed — production appears consistent with standard.",
}


class MockLLMProvider(MultimodalLLMProviderBase):
    provider_name = "mock"

    def complete_text(
        self,
        prompt: str,
        system_prompt: str | None = None,
        **kwargs,
    ) -> LLMTextResult:
        return LLMTextResult(
            text=f"[Mock response to: {prompt[:80]}]",
            provider_name=self.provider_name,
            model_name="mock-text-v1",
            usage={"prompt_tokens": 0, "completion_tokens": 0},
        )

    def extract_json(
        self,
        prompt: str,
        schema_hint: str | None = None,
        system_prompt: str | None = None,
        **kwargs,
    ) -> LLMJsonResult:
        data = dict(_MOCK_QC_RESULT)
        return LLMJsonResult(
            data=data,
            provider_name=self.provider_name,
            model_name="mock-json-v1",
            raw_text=json.dumps(data, ensure_ascii=False),
        )

    def compare_images(
        self,
        images: list[str],
        question: str,
        system_prompt: str | None = None,
        **kwargs,
    ) -> LLMImageCompareResult:
        data = dict(_MOCK_QC_RESULT)
        data["image_count"] = len(images)
        return LLMImageCompareResult(
            result_json=data,
            provider_name=self.provider_name,
            model_name="mock-vision-v1",
            raw_text=json.dumps(data, ensure_ascii=False),
        )

    def compare_video_frames(
        self,
        frames: list[str],
        question: str,
        system_prompt: str | None = None,
        **kwargs,
    ) -> LLMVideoCompareResult:
        data = dict(_MOCK_QC_RESULT)
        data["frames_sampled"] = len(frames)
        return LLMVideoCompareResult(
            result_json=data,
            provider_name=self.provider_name,
            model_name="mock-video-v1",
            frames_used=len(frames),
            raw_text=json.dumps(data, ensure_ascii=False),
        )
