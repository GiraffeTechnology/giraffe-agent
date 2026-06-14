"""
Qwen / Tongyi Qianwen provider — default LLM for Giraffe Agent QC.
Uses DashScope REST API via httpx (no SDK required).

Environment variables:
  DASHSCOPE_API_KEY or QWEN_API_KEY  — required for real calls
  QWEN_TEXT_MODEL                    — defaults to qwen-turbo
  QWEN_VISION_MODEL                  — defaults to qwen-vl-plus
  QWEN_VIDEO_MODEL                   — defaults to qwen-vl-plus (frame-based)
  QWEN_BASE_URL                      — defaults to DashScope production endpoint
  LLM_TIMEOUT_SECONDS                — default 60
"""
import base64
import json
import re
import time
from pathlib import Path

import httpx

from src.llm.provider_base import (
    MultimodalLLMProviderBase,
    LLMTextResult, LLMJsonResult, LLMImageCompareResult, LLMVideoCompareResult,
)
from src.llm.provider_config import (
    DEFAULT_QWEN_TEXT_MODEL, DEFAULT_QWEN_VISION_MODEL, DEFAULT_QWEN_VIDEO_MODEL,
    QWEN_TEXT_ENDPOINT, QWEN_VISION_ENDPOINT,
    LLM_TIMEOUT_SECONDS, LLM_MAX_RETRIES,
    get_qwen_api_key,
)
from src.m_side.m_event_logger import log_m_event


def _encode_image(image_ref: str) -> str:
    """Return base64 data URI or URL as-is."""
    if image_ref.startswith("data:") or image_ref.startswith("http"):
        return image_ref
    path = Path(image_ref)
    if path.exists():
        mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
        b64 = base64.b64encode(path.read_bytes()).decode()
        return f"data:{mime};base64,{b64}"
    return image_ref


def _extract_json_from_text(text: str) -> dict:
    """Extract JSON object from LLM output, stripping markdown fences."""
    text = re.sub(r"```(?:json)?", "", text).strip().rstrip("`").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass
    return {"raw_text": text}


class QwenProvider(MultimodalLLMProviderBase):
    provider_name = "qwen"

    def __init__(
        self,
        api_key: str | None = None,
        text_model: str | None = None,
        vision_model: str | None = None,
        video_model: str | None = None,
    ):
        self.api_key = api_key or get_qwen_api_key() or ""
        self.text_model = text_model or DEFAULT_QWEN_TEXT_MODEL
        self.vision_model = vision_model or DEFAULT_QWEN_VISION_MODEL
        self.video_model = video_model or DEFAULT_QWEN_VIDEO_MODEL

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _post_with_retry(self, url: str, payload: dict) -> dict:
        last_exc: Exception | None = None
        for attempt in range(LLM_MAX_RETRIES + 1):
            try:
                resp = httpx.post(
                    url,
                    headers=self._headers(),
                    json=payload,
                    timeout=LLM_TIMEOUT_SECONDS,
                )
                resp.raise_for_status()
                return resp.json()
            except Exception as exc:
                last_exc = exc
                if attempt < LLM_MAX_RETRIES:
                    time.sleep(2 ** attempt)
        raise RuntimeError(f"Qwen API call failed after {LLM_MAX_RETRIES+1} attempts: {last_exc}")

    def complete_text(
        self,
        prompt: str,
        system_prompt: str | None = None,
        **kwargs,
    ) -> LLMTextResult:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.text_model,
            "input": {"messages": messages},
            "parameters": {"result_format": "message"},
        }
        log_m_event(event_type="LLM_API_CALL", payload={"provider": "qwen", "model": self.text_model, "endpoint": "text"})
        raw = self._post_with_retry(QWEN_TEXT_ENDPOINT, payload)
        text = raw.get("output", {}).get("choices", [{}])[0].get("message", {}).get("content", "")
        usage = raw.get("usage", {})
        return LLMTextResult(
            text=text,
            provider_name=self.provider_name,
            model_name=self.text_model,
            usage=usage,
            raw_response=raw,
        )

    def extract_json(
        self,
        prompt: str,
        schema_hint: str | None = None,
        system_prompt: str | None = None,
        **kwargs,
    ) -> LLMJsonResult:
        full_prompt = prompt
        if schema_hint:
            full_prompt = f"{prompt}\n\n请严格按以下 JSON schema 输出，不要添加额外文字：\n{schema_hint}"
        result = self.complete_text(full_prompt, system_prompt=system_prompt)
        data = _extract_json_from_text(result.text)
        return LLMJsonResult(
            data=data,
            provider_name=self.provider_name,
            model_name=self.text_model,
            raw_text=result.text,
            usage=result.usage,
        )

    def compare_images(
        self,
        images: list[str],
        question: str,
        system_prompt: str | None = None,
        **kwargs,
    ) -> LLMImageCompareResult:
        content = []
        for img in images:
            content.append({"image": _encode_image(img)})
        content.append({"text": question})

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": content})

        payload = {
            "model": self.vision_model,
            "input": {"messages": messages},
        }
        log_m_event(event_type="LLM_API_CALL", payload={"provider": "qwen", "model": self.vision_model, "endpoint": "vision", "image_count": len(images)})
        raw = self._post_with_retry(QWEN_VISION_ENDPOINT, payload)
        text = raw.get("output", {}).get("choices", [{}])[0].get("message", {}).get("content", "")
        if isinstance(text, list):
            text = " ".join(c.get("text", "") for c in text if isinstance(c, dict))
        data = _extract_json_from_text(text)
        return LLMImageCompareResult(
            result_json=data,
            provider_name=self.provider_name,
            model_name=self.vision_model,
            raw_text=str(text),
            usage=raw.get("usage", {}),
        )

    def compare_video_frames(
        self,
        frames: list[str],
        question: str,
        system_prompt: str | None = None,
        **kwargs,
    ) -> LLMVideoCompareResult:
        # Frame-based: treat frames as images and send to vision model
        result = self.compare_images(frames, question, system_prompt=system_prompt)
        return LLMVideoCompareResult(
            result_json=result.result_json,
            provider_name=self.provider_name,
            model_name=self.video_model,
            frames_used=len(frames),
            raw_text=result.raw_text,
            usage=result.usage,
        )
