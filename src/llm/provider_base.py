"""Abstract base class for multimodal LLM providers."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class LLMTextResult:
    text: str
    provider_name: str
    model_name: str
    usage: dict = field(default_factory=dict)
    raw_response: dict = field(default_factory=dict)


@dataclass
class LLMJsonResult:
    data: dict
    provider_name: str
    model_name: str
    raw_text: str = ""
    usage: dict = field(default_factory=dict)


@dataclass
class LLMImageCompareResult:
    result_json: dict
    provider_name: str
    model_name: str
    raw_text: str = ""
    usage: dict = field(default_factory=dict)


@dataclass
class LLMVideoCompareResult:
    result_json: dict
    provider_name: str
    model_name: str
    frames_used: int = 0
    raw_text: str = ""
    usage: dict = field(default_factory=dict)


class MultimodalLLMProviderBase(ABC):
    provider_name: str = "base"

    @abstractmethod
    def complete_text(
        self,
        prompt: str,
        system_prompt: str | None = None,
        **kwargs,
    ) -> LLMTextResult:
        ...

    @abstractmethod
    def extract_json(
        self,
        prompt: str,
        schema_hint: str | None = None,
        system_prompt: str | None = None,
        **kwargs,
    ) -> LLMJsonResult:
        ...

    @abstractmethod
    def compare_images(
        self,
        images: list[str],
        question: str,
        system_prompt: str | None = None,
        **kwargs,
    ) -> LLMImageCompareResult:
        """
        Compare one or more images.
        `images` is a list of file paths, URLs, or base64 data URIs.
        """
        ...

    @abstractmethod
    def compare_video_frames(
        self,
        frames: list[str],
        question: str,
        system_prompt: str | None = None,
        **kwargs,
    ) -> LLMVideoCompareResult:
        """
        Compare sampled video frames.
        `frames` is a list of file paths or base64 data URIs.
        """
        ...
