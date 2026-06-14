"""
Anthropic / Claude provider — optional fallback.
Requires ANTHROPIC_API_KEY and anthropic SDK (not in default dependencies).
"""
import json
from src.llm.provider_base import (
    MultimodalLLMProviderBase,
    LLMTextResult, LLMJsonResult, LLMImageCompareResult, LLMVideoCompareResult,
)
from src.llm.provider_config import DEFAULT_ANTHROPIC_TEXT_MODEL, DEFAULT_ANTHROPIC_VISION_MODEL, get_anthropic_api_key


class AnthropicProvider(MultimodalLLMProviderBase):
    provider_name = "anthropic"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or get_anthropic_api_key() or ""
        self.text_model = DEFAULT_ANTHROPIC_TEXT_MODEL
        self.vision_model = DEFAULT_ANTHROPIC_VISION_MODEL

    def _client(self):
        try:
            import anthropic
            return anthropic.Anthropic(api_key=self.api_key)
        except ImportError:
            raise RuntimeError("anthropic SDK not installed. Add 'anthropic' to dependencies.")

    def complete_text(self, prompt: str, system_prompt: str | None = None, **kwargs) -> LLMTextResult:
        client = self._client()
        kwargs_msg = {"model": self.text_model, "max_tokens": 2048, "messages": [{"role": "user", "content": prompt}]}
        if system_prompt:
            kwargs_msg["system"] = system_prompt
        resp = client.messages.create(**kwargs_msg)
        text = resp.content[0].text if resp.content else ""
        return LLMTextResult(text=text, provider_name=self.provider_name, model_name=self.text_model)

    def extract_json(self, prompt: str, schema_hint: str | None = None, system_prompt: str | None = None, **kwargs) -> LLMJsonResult:
        result = self.complete_text(prompt, system_prompt=system_prompt)
        try:
            data = json.loads(result.text)
        except Exception:
            data = {"raw_text": result.text}
        return LLMJsonResult(data=data, provider_name=self.provider_name, model_name=self.text_model, raw_text=result.text)

    def compare_images(self, images: list[str], question: str, system_prompt: str | None = None, **kwargs) -> LLMImageCompareResult:
        raise NotImplementedError("Anthropic image comparison requires anthropic SDK with vision support")

    def compare_video_frames(self, frames: list[str], question: str, system_prompt: str | None = None, **kwargs) -> LLMVideoCompareResult:
        raise NotImplementedError("Anthropic video comparison not implemented")
