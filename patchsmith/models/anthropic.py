"""Anthropic (Claude) backend with prompt caching."""
from __future__ import annotations
import os
from typing import Any
import anthropic
from patchsmith.models.base import BaseLLM, Message, LLMResponse


class AnthropicLLM(BaseLLM):
    def __init__(self, config: dict[str, Any]):
        api_key = config.get("model", {}).get("api_key") or os.environ.get("ANTHROPIC_API_KEY", "")
        self.client = anthropic.AsyncAnthropic(api_key=api_key)
        self.model = config.get("model", {}).get("name", "claude-sonnet-4-6")

    async def complete(
        self,
        messages: list[Message],
        system: str = "",
        max_tokens: int = 4096,
        temperature: float = 0.2,
    ) -> LLMResponse:
        system_blocks: list[dict] = []
        if system:
            # Enable prompt caching on long system prompts
            system_blocks = [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]

        api_msgs = [{"role": m.role, "content": m.content} for m in messages]

        resp = await self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_blocks if system_blocks else anthropic.NOT_GIVEN,
            messages=api_msgs,
        )
        return LLMResponse(
            content=resp.content[0].text,
            model=resp.model,
            input_tokens=resp.usage.input_tokens,
            output_tokens=resp.usage.output_tokens,
        )
