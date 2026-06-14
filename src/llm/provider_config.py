"""
LLM provider configuration — env-based, Qwen-first.

Production deployments MUST set explicit model names based on current
DashScope / Qwen availability. The constants below are conservative
defaults used only when env vars are absent.

Known stable model IDs (as of mid-2025):
  Text:   qwen-turbo, qwen-plus, qwen-max
  Vision: qwen-vl-plus, qwen-vl-max
  Video:  no native video model yet; frame-sampling fallback is used.
"""
import os

DEFAULT_LLM_PROVIDER = "qwen"
DEFAULT_QC_PROVIDER = "qwen"

# Qwen / DashScope
DEFAULT_QWEN_TEXT_MODEL = os.getenv("QWEN_TEXT_MODEL") or "qwen-turbo"
DEFAULT_QWEN_VISION_MODEL = os.getenv("QWEN_VISION_MODEL") or "qwen-vl-plus"
DEFAULT_QWEN_VIDEO_MODEL = os.getenv("QWEN_VIDEO_MODEL") or "qwen-vl-plus"
QWEN_BASE_URL = os.getenv("QWEN_BASE_URL") or "https://dashscope.aliyuncs.com/api/v1"
QWEN_TEXT_ENDPOINT = f"{QWEN_BASE_URL}/services/aigc/text-generation/generation"
QWEN_VISION_ENDPOINT = f"{QWEN_BASE_URL}/services/aigc/multimodal-generation/generation"

# Other providers
DEFAULT_OPENAI_TEXT_MODEL = os.getenv("OPENAI_TEXT_MODEL") or "gpt-4o"
DEFAULT_OPENAI_VISION_MODEL = os.getenv("OPENAI_VISION_MODEL") or "gpt-4o"
DEFAULT_ANTHROPIC_TEXT_MODEL = os.getenv("ANTHROPIC_TEXT_MODEL") or "claude-opus-4-8"
DEFAULT_ANTHROPIC_VISION_MODEL = os.getenv("ANTHROPIC_VISION_MODEL") or "claude-opus-4-8"
DEFAULT_DEEPSEEK_TEXT_MODEL = os.getenv("DEEPSEEK_TEXT_MODEL") or "deepseek-chat"
DEFAULT_DEEPSEEK_VISION_MODEL = os.getenv("DEEPSEEK_VISION_MODEL") or "deepseek-chat"

# Runtime flags
LLM_ENABLE_REAL_CALLS = os.getenv("LLM_ENABLE_REAL_CALLS", "false").lower() == "true"
QC_AUTO_COMPARE_ENABLED = os.getenv("QC_AUTO_COMPARE_ENABLED", "false").lower() == "true"
QC_ALLOW_EXTERNAL_LLM = os.getenv("QC_ALLOW_EXTERNAL_LLM", "false").lower() == "true"
LLM_TIMEOUT_SECONDS = int(os.getenv("LLM_TIMEOUT_SECONDS", "60"))
LLM_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "2"))
IS_PRODUCTION = os.getenv("GIRAFFE_ENV", "local").lower() == "production"


def get_qwen_api_key() -> str | None:
    return os.getenv("DASHSCOPE_API_KEY") or os.getenv("QWEN_API_KEY")


def get_openai_api_key() -> str | None:
    return os.getenv("OPENAI_API_KEY")


def get_anthropic_api_key() -> str | None:
    return os.getenv("ANTHROPIC_API_KEY")


def get_deepseek_api_key() -> str | None:
    return os.getenv("DEEPSEEK_API_KEY")
