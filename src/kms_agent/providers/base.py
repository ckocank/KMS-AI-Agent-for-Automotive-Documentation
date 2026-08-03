from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class GenerationResult:
    content: str
    usage: dict[str, Any] = field(default_factory=dict)


class InferenceProvider(Protocol):
    dimension: int

    def embed(self, texts: list[str]) -> list[list[float]]: ...

    def rerank(self, query: str, documents: list[str]) -> list[float]: ...

    def generate(self, system_prompt: str, user_prompt: str) -> GenerationResult: ...

    def describe_image(self, image: bytes, media_type: str, prompt: str) -> GenerationResult: ...

