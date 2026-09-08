"""Abstract LLM interface."""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Message:
    role: str
    content: str


@dataclass
class LLMResponse:
    content: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0


class BaseLLM(ABC):
    @abstractmethod
    async def complete(
        self,
        messages: list[Message],
        system: str = "",
        max_tokens: int = 4096,
        temperature: float = 0.2,
    ) -> LLMResponse:
        ...

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> "BaseLLM":
        provider = config.get("model", {}).get("provider", "anthropic")
        if provider == "anthropic":
            from patchsmith.models.anthropic import AnthropicLLM
            return AnthropicLLM(config)
        elif provider == "openai":
            from patchsmith.models.openai import OpenAILLM
            return OpenAILLM(config)
        raise ValueError(f"Unknown provider: {provider}")
