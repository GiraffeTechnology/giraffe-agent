"""Tests for Qwen provider configuration."""
import os
import pytest
from src.llm.provider_config import (
    DEFAULT_LLM_PROVIDER, DEFAULT_QC_PROVIDER,
    DEFAULT_QWEN_TEXT_MODEL, DEFAULT_QWEN_VISION_MODEL, DEFAULT_QWEN_VIDEO_MODEL,
    get_qwen_api_key,
)


def test_default_llm_provider_is_qwen():
    assert DEFAULT_LLM_PROVIDER == "qwen"


def test_default_qc_provider_is_qwen():
    assert DEFAULT_QC_PROVIDER == "qwen"


def test_default_text_model_is_string():
    assert isinstance(DEFAULT_QWEN_TEXT_MODEL, str)
    assert len(DEFAULT_QWEN_TEXT_MODEL) > 0


def test_default_vision_model_is_string():
    assert isinstance(DEFAULT_QWEN_VISION_MODEL, str)
    assert len(DEFAULT_QWEN_VISION_MODEL) > 0


def test_default_video_model_is_string():
    assert isinstance(DEFAULT_QWEN_VIDEO_MODEL, str)
    assert len(DEFAULT_QWEN_VIDEO_MODEL) > 0


def test_get_qwen_api_key_returns_none_when_not_set(monkeypatch):
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    monkeypatch.delenv("QWEN_API_KEY", raising=False)
    from src.llm import provider_config
    key = provider_config.get_qwen_api_key()
    assert not key


def test_get_qwen_api_key_returns_dashscope_key(monkeypatch):
    monkeypatch.setenv("DASHSCOPE_API_KEY", "sk-dashscope-test")
    monkeypatch.delenv("QWEN_API_KEY", raising=False)
    from src.llm import provider_config
    key = provider_config.get_qwen_api_key()
    assert key == "sk-dashscope-test"


def test_get_qwen_api_key_fallback_to_qwen_key(monkeypatch):
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    monkeypatch.setenv("QWEN_API_KEY", "sk-qwen-test")
    from src.llm import provider_config
    key = provider_config.get_qwen_api_key()
    assert key == "sk-qwen-test"


def test_model_names_configurable_via_env(monkeypatch):
    monkeypatch.setenv("QWEN_TEXT_MODEL", "qwen-turbo-custom")
    assert os.getenv("QWEN_TEXT_MODEL") == "qwen-turbo-custom"
