"""
DeepSeek provider — optional fallback (OpenAI-compatible API).
Requires DEEPSEEK_API_KEY. Uses httpx with OpenAI-compatible endpoint.
"""
import json
import httpx
from src.llm.provider_base import (
    MultimodalLLMProviderBase,
    LLMTextResult, LLMJsonResult, LLMImageCompareResult, LLMVideoCompareResult,
)
from src.llm.provider_config import DEFAULT_DEEPSEEK_TEXT_MODEL, LLM_TIMEOUT_SECONDS, get_deepseek_api_key

_DEEPSEEK_BASE = "https://api.deepseek.com/v1"


class DeepSeekProvider(MultimodalLLMProviderBase):
    provider_name = "deepseek"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or get_deepseek_api_key() or ""
        self.text_model = DEFAULT_DEEPSEEK_TEXT_MODEL

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def complete_text(self, prompt: str, system_prompt: str | None = None, **kwargs) -> LLMTextResult:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        resp = httpx.post(
            f"{_DEEPSEEK_BASE}/chat/completions",
            headers=self._headers(),
            json={"model": self.text_model, "messages": messages},
            timeout=LLM_TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        text = resp.json()["choices"][0]["message"]["content"]
        return LLMTextResult(text=text, provider_name=self.provider_name, model_name=self.text_model)

    def extract_json(self, prompt: str, schema_hint: str | None = None, system_prompt: str | None = None, **kwargs) -> LLMJsonResult:
        result = self.complete_text(prompt, system_prompt=system_prompt)
        try:
            data = json.loads(result.text)
        except Exception:
            data = {"raw_text": result.text}
        return LLMJsonResult(data=data, provider_name=self.provider_name, model_name=self.text_model, raw_text=result.text)

    def compare_images(self, images: list[str], question: str, system_prompt: str | None = None, **kwargs) -> LLMImageCompareResult:
        raise NotImplementedError("DeepSeek does not support image comparison in this provider")

    def compare_video_frames(self, frames: list[str], question: str, system_prompt: str | None = None, **kwargs) -> LLMVideoCompareResult:
        raise NotImplementedError("DeepSeek does not support video comparison")
