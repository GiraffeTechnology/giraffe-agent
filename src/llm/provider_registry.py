"""
LLM provider registry — resolves provider by name, Qwen first.

Priority:
  1. qwen   (default — Chinese-first QC, DashScope vision)
  2. mock   (local/test fallback when Qwen key absent)
  3. openai
  4. anthropic
  5. deepseek

Fallback rules:
  local/test mode + qwen key missing → MockProvider + log warning
  production mode  + qwen key missing → RuntimeError
"""
import os

from src.llm.provider_base import MultimodalLLMProviderBase
from src.llm.provider_config import (
    DEFAULT_LLM_PROVIDER,
    get_qwen_api_key, get_openai_api_key, get_anthropic_api_key, get_deepseek_api_key,
)
from src.m_side.m_event_logger import log_m_event


def _is_production() -> bool:
    return os.getenv("GIRAFFE_ENV", "local").lower() == "production"


def _real_calls_enabled() -> bool:
    return os.getenv("LLM_ENABLE_REAL_CALLS", "false").lower() == "true"


def get_llm_provider(provider_name: str | None = None) -> MultimodalLLMProviderBase:
    name = provider_name or os.getenv("LLM_PROVIDER", DEFAULT_LLM_PROVIDER)

    if name == "qwen":
        key = get_qwen_api_key()
        real_calls = _real_calls_enabled()
        is_prod = _is_production()
        if not key and is_prod and real_calls:
            raise RuntimeError(
                "Qwen API key is required in production mode. "
                "Set DASHSCOPE_API_KEY or QWEN_API_KEY."
            )
        if not key or not real_calls:
            reason = "missing_qwen_api_key" if not key else "real_calls_disabled"
            log_m_event(
                event_type="LLM_PROVIDER_FALLBACK_TO_MOCK",
                payload={
                    "requested_provider": "qwen",
                    "fallback_reason": reason,
                    "message": f"Qwen unavailable ({reason}), using mock provider",
                },
            )
            from src.llm.mock_provider import MockLLMProvider
            return MockLLMProvider()
        from src.llm.qwen_provider import QwenProvider
        return QwenProvider(api_key=key)

    if name == "mock":
        from src.llm.mock_provider import MockLLMProvider
        return MockLLMProvider()

    if name == "openai":
        from src.llm.openai_provider import OpenAIProvider
        return OpenAIProvider()

    if name == "anthropic":
        from src.llm.anthropic_provider import AnthropicProvider
        return AnthropicProvider()

    if name == "deepseek":
        from src.llm.deepseek_provider import DeepSeekProvider
        return DeepSeekProvider()

    # Unknown provider — fallback to mock in local, error in production
    if _is_production():
        raise RuntimeError(f"Unknown LLM provider '{name}' in production mode.")
    log_m_event(
        event_type="LLM_PROVIDER_FALLBACK_TO_MOCK",
        payload={"requested_provider": name, "fallback_reason": "unknown_provider"},
    )
    from src.llm.mock_provider import MockLLMProvider
    return MockLLMProvider()
