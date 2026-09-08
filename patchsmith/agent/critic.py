"""LLM-based patch critic."""
from __future__ import annotations
import logging
from dataclasses import dataclass
from typing import Any

from patchsmith.models.base import BaseLLM, Message

logger = logging.getLogger(__name__)

CRITIC_SYSTEM = """You are a senior software engineer reviewing a patch.
Given a repair plan and a patch diff, answer with JSON:
{
  "accepted": true/false,
  "rejection_reason": "...",
  "concerns": ["..."],
  "suggestion": "..."
}
Accept the patch if it addresses the issue without introducing obvious regressions.
Reject if: unrelated files modified, issue not addressed, introduces syntax errors, or is trivially wrong.
Return ONLY valid JSON."""


@dataclass
class CriticVerdict:
    accepted: bool
    rejection_reason: str = ""
    concerns: list[str] = None
    suggestion: str = ""

    def __post_init__(self):
        if self.concerns is None:
            self.concerns = []


class Critic:
    def __init__(self, config: dict[str, Any]):
        self.llm = BaseLLM.from_config(config)

    async def evaluate(self, plan: Any, patch: Any, task: Any) -> CriticVerdict:
        import json
        user_msg = (
            f"Issue: {task.issue_title}\n{task.issue_body}\n\n"
            f"Repair plan:\n"
            f"  Problem: {plan.problem}\n"
            f"  Hypothesis: {plan.hypothesis}\n"
            f"  Steps: {', '.join(plan.steps)}\n\n"
            f"Patch ({patch.strategy} strategy):\n```diff\n{patch.diff[:3000]}\n```\n\n"
            f"Should this patch be accepted?"
        )
        resp = await self.llm.complete(
            messages=[Message(role="user", content=user_msg)],
            system=CRITIC_SYSTEM,
            max_tokens=512,
        )
        try:
            data = json.loads(resp.content)
            return CriticVerdict(
                accepted=bool(data.get("accepted", False)),
                rejection_reason=data.get("rejection_reason", ""),
                concerns=data.get("concerns", []),
                suggestion=data.get("suggestion", ""),
            )
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("Critic parse error: %s", e)
            # Default: accept if we couldn't parse
            return CriticVerdict(accepted=True, rejection_reason="", suggestion="")
