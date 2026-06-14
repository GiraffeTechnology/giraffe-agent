"""
OpenAI / ChatGPT provider — optional fallback.
Requires OPENAI_API_KEY and openai SDK (not in default dependencies).
"""
import json
from src.llm.provider_base import (
    MultimodalLLMProviderBase,
    LLMTextResult, LLMJsonResult, LLMImageCompareResult, LLMVideoCompareResult,
)
from src.llm.provider_config import DEFAULT_OPENAI_TEXT_MODEL, DEFAULT_OPENAI_VISION_MODEL, get_openai_api_key


class OpenAIProvider(MultimodalLLMProviderBase):
    provider_name = "openai"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or get_openai_api_key() or ""
        self.text_model = DEFAULT_OPENAI_TEXT_MODEL
        self.vision_model = DEFAULT_OPENAI_VISION_MODEL

    def _client(self):
        try:
            import openai
            return openai.OpenAI(api_key=self.api_key)
        except ImportError:
            raise RuntimeError("openai SDK not installed. Add 'openai' to dependencies.")

    def complete_text(self, prompt: str, system_prompt: str | None = None, **kwargs) -> LLMTextResult:
        client = self._client()
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        resp = client.chat.completions.create(model=self.text_model, messages=messages)
        text = resp.choices[0].message.content or ""
        return LLMTextResult(text=text, provider_name=self.provider_name, model_name=self.text_model)

    def extract_json(self, prompt: str, schema_hint: str | None = None, system_prompt: str | None = None, **kwargs) -> LLMJsonResult:
        result = self.complete_text(prompt, system_prompt=system_prompt)
        try:
            data = json.loads(result.text)
        except Exception:
            data = {"raw_text": result.text}
        return LLMJsonResult(data=data, provider_name=self.provider_name, model_name=self.text_model, raw_text=result.text)

    def compare_images(self, images: list[str], question: str, system_prompt: str | None = None, **kwargs) -> LLMImageCompareResult:
        raise NotImplementedError("OpenAI image comparison requires openai SDK with vision support")

    def compare_video_frames(self, frames: list[str], question: str, system_prompt: str | None = None, **kwargs) -> LLMVideoCompareResult:
        raise NotImplementedError("OpenAI video comparison not implemented")
