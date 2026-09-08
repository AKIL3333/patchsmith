"""Structured repair planner."""
from __future__ import annotations
import json
import logging
from dataclasses import dataclass, field
from typing import Any

from patchsmith.models.base import BaseLLM, Message

logger = logging.getLogger(__name__)

PLAN_SYSTEM = """You are PatchSmith's repair planner.
Given a bug report and repository context, produce a structured JSON repair plan.
Return ONLY valid JSON with these fields:
{
  "problem": "one sentence description",
  "hypothesis": "root cause hypothesis",
  "files": ["list", "of", "relevant", "files"],
  "steps": ["ordered", "repair", "steps"],
  "confidence": 0.0
}
confidence is 0.0-1.0."""


@dataclass
class RepairPlan:
    problem: str
    hypothesis: str
    files: list[str]
    steps: list[str]
    confidence: float = 0.5


class Planner:
    def __init__(self, config: dict[str, Any]):
        self.llm = BaseLLM.from_config(config)

    async def plan(
        self,
        task: Any,
        context: Any,
        past_failures: list[str] | None = None,
        attempt: int = 0,
    ) -> RepairPlan:
        failures_text = ""
        if past_failures:
            failures_text = "\n\nPrevious failed approaches:\n" + "\n".join(
                f"- {f}" for f in past_failures[-3:]
            )

        user_msg = (
            f"Issue: {task.issue_title}\n\n"
            f"{task.issue_body}\n\n"
            f"Repository context:\n{context.format(max_chunks=8)}"
            f"{failures_text}\n\n"
            f"Attempt: {attempt + 1}. Produce a repair plan."
        )

        resp = await self.llm.complete(
            messages=[Message(role="user", content=user_msg)],
            system=PLAN_SYSTEM,
            max_tokens=1024,
            temperature=0.2 + attempt * 0.1,
        )

        try:
            data = json.loads(resp.content)
            return RepairPlan(
                problem=data.get("problem", task.issue_title),
                hypothesis=data.get("hypothesis", ""),
                files=data.get("files", []),
                steps=data.get("steps", []),
                confidence=float(data.get("confidence", 0.5)),
            )
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("Failed to parse plan JSON: %s", e)
            return RepairPlan(
                problem=task.issue_title,
                hypothesis="Unable to determine",
                files=[],
                steps=["Inspect relevant files", "Implement fix", "Run tests"],
                confidence=0.3,
            )
