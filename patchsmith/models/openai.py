"""OpenAI (GPT-4o) backend."""
from __future__ import annotations
import os
from typing import Any
import openai
from patchsmith.models.base import BaseLLM, Message, LLMResponse


class OpenAILLM(BaseLLM):
    def __init__(self, config: dict[str, Any]):
        api_key = config.get("model", {}).get("openai_api_key") or os.environ.get("OPENAI_API_KEY", "")
        self.client = openai.AsyncOpenAI(api_key=api_key)
        self.model = config.get("model", {}).get("name", "gpt-4o")

    async def complete(
        self,
        messages: list[Message],
        system: str = "",
        max_tokens: int = 4096,
        temperature: float = 0.2,
    ) -> LLMResponse:
        api_msgs = []
        if system:
            api_msgs.append({"role": "system", "content": system})
        api_msgs.extend({"role": m.role, "content": m.content} for m in messages)

        resp = await self.client.chat.completions.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=api_msgs,
        )
        return LLMResponse(
            content=resp.choices[0].message.content or "",
            model=resp.model,
            input_tokens=resp.usage.prompt_tokens if resp.usage else 0,
            output_tokens=resp.usage.completion_tokens if resp.usage else 0,
        )
