"""Tests for LLM provider registry — Qwen-first, mock fallback."""
import os
import pytest
from src.llm.provider_registry import get_llm_provider
from src.llm.mock_provider import MockLLMProvider
from src.llm.qwen_provider import QwenProvider
from src.llm.provider_base import MultimodalLLMProviderBase
from src.llm.provider_config import DEFAULT_LLM_PROVIDER, DEFAULT_QC_PROVIDER


def test_default_provider_is_qwen_constant():
    assert DEFAULT_LLM_PROVIDER == "qwen"


def test_default_qc_provider_is_qwen_constant():
    assert DEFAULT_QC_PROVIDER == "qwen"


def test_qwen_without_key_falls_back_to_mock(monkeypatch):
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    monkeypatch.delenv("QWEN_API_KEY", raising=False)
    monkeypatch.setenv("LLM_ENABLE_REAL_CALLS", "false")
    provider = get_llm_provider("qwen")
    assert isinstance(provider, MockLLMProvider)


def test_qwen_with_real_calls_disabled_falls_back_to_mock(monkeypatch):
    monkeypatch.setenv("DASHSCOPE_API_KEY", "fake-key-for-test")
    monkeypatch.setenv("LLM_ENABLE_REAL_CALLS", "false")
    provider = get_llm_provider("qwen")
    assert isinstance(provider, MockLLMProvider)


def test_explicit_mock_returns_mock():
    provider = get_llm_provider("mock")
    assert isinstance(provider, MockLLMProvider)
    assert provider.provider_name == "mock"


def test_get_provider_returns_base_interface():
    provider = get_llm_provider("mock")
    assert isinstance(provider, MultimodalLLMProviderBase)


def test_get_provider_qwen_with_key_returns_qwen(monkeypatch):
    monkeypatch.setenv("DASHSCOPE_API_KEY", "sk-test-fake-key")
    monkeypatch.setenv("LLM_ENABLE_REAL_CALLS", "true")
    monkeypatch.setenv("GIRAFFE_ENV", "local")
    # Ensure the registry reads from env (not cached module constants)
    provider = get_llm_provider("qwen")
    assert isinstance(provider, QwenProvider)
    assert provider.provider_name == "qwen"
    assert provider.api_key == "sk-test-fake-key"


def test_production_mode_without_qwen_key_raises(monkeypatch):
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    monkeypatch.delenv("QWEN_API_KEY", raising=False)
    monkeypatch.setenv("LLM_ENABLE_REAL_CALLS", "true")
    monkeypatch.setenv("GIRAFFE_ENV", "production")
    with pytest.raises(RuntimeError, match="Qwen API key is required"):
        get_llm_provider("qwen")


def test_unknown_provider_falls_back_to_mock_in_local(monkeypatch):
    monkeypatch.setenv("GIRAFFE_ENV", "local")
    provider = get_llm_provider("totally_unknown_provider_xyz")
    assert isinstance(provider, MockLLMProvider)


def test_default_env_resolves_to_qwen_fallback(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "qwen")
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    monkeypatch.setenv("LLM_ENABLE_REAL_CALLS", "false")
    provider = get_llm_provider()
    assert isinstance(provider, MockLLMProvider)


def test_openai_provider_importable():
    from src.llm.openai_provider import OpenAIProvider
    p = OpenAIProvider(api_key="fake")
    assert p.provider_name == "openai"


def test_anthropic_provider_importable():
    from src.llm.anthropic_provider import AnthropicProvider
    p = AnthropicProvider(api_key="fake")
    assert p.provider_name == "anthropic"


def test_deepseek_provider_importable():
    from src.llm.deepseek_provider import DeepSeekProvider
    p = DeepSeekProvider(api_key="fake")
    assert p.provider_name == "deepseek"
