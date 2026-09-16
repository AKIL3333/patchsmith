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

Return ONLY valid JSON with exactly these fields:
{
  "problem": "one sentence description of the observable failure",
  "hypotheses": [
    {
      "description": "root cause hypothesis",
      "confidence": 0.0,
      "evidence": ["supporting evidence from retrieved context"]
    }
  ],
  "target_symbols": ["list of function/class names to modify"],
  "target_files": ["list of files to modify"],
  "investigation_steps": ["steps to confirm the hypothesis"],
  "repair_steps": ["ordered steps to implement the fix"],
  "validation_plan": ["how to verify the fix is correct"],
  "risk_assessment": {
    "regression_risk": "low|medium|high",
    "rationale": "why"
  }
}
confidence is 0.0-1.0. Be concise. Return ONLY valid JSON."""


@dataclass
class Hypothesis:
    description: str
    confidence: float = 0.5
    evidence: list[str] = field(default_factory=list)


@dataclass
class RepairPlan:
    problem: str
    hypothesis: str          # primary hypothesis description (for compat)
    files: list[str]         # target files (for compat)
    steps: list[str]         # repair steps (for compat)
    hypotheses: list[Hypothesis] = field(default_factory=list)
    target_symbols: list[str] = field(default_factory=list)
    investigation_steps: list[str] = field(default_factory=list)
    validation_plan: list[str] = field(default_factory=list)
    regression_risk: str = "medium"
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
            failures_text = "\n\nPrevious failed approaches (avoid repeating):\n" + "\n".join(
                f"- {f}" for f in past_failures[-3:]
            )

        user_msg = (
            f"Issue: {task.issue_title}\n\n"
            f"{task.issue_body}\n\n"
            f"Repository context:\n{context.format(max_chunks=8)}"
            f"{failures_text}\n\n"
            f"Attempt: {attempt + 1}. Produce a structured repair plan as JSON."
        )

        resp = await self.llm.complete(
            messages=[Message(role="user", content=user_msg)],
            system=PLAN_SYSTEM,
            max_tokens=1500,
            temperature=0.2 + attempt * 0.1,
        )

        return _parse_plan(resp.content, task)


def _parse_plan(content: str, task: Any) -> RepairPlan:
    try:
        # Strip markdown fences if present
        text = content.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        data = json.loads(text)

        hypotheses = []
        for h in data.get("hypotheses", []):
            hypotheses.append(Hypothesis(
                description=h.get("description", ""),
                confidence=float(h.get("confidence", 0.5)),
                evidence=h.get("evidence", []),
            ))

        primary_h = hypotheses[0].description if hypotheses else ""
        primary_conf = hypotheses[0].confidence if hypotheses else 0.5

        return RepairPlan(
            problem=data.get("problem", task.issue_title),
            hypothesis=primary_h,
            files=data.get("target_files", []),
            steps=data.get("repair_steps", []),
            hypotheses=hypotheses,
            target_symbols=data.get("target_symbols", []),
            investigation_steps=data.get("investigation_steps", []),
            validation_plan=data.get("validation_plan", []),
            regression_risk=data.get("risk_assessment", {}).get("regression_risk", "medium"),
            confidence=primary_conf,
        )
    except (json.JSONDecodeError, KeyError, IndexError) as e:
        logger.warning("Failed to parse plan JSON (%s), using fallback", e)
        return RepairPlan(
            problem=task.issue_title,
            hypothesis="Unable to determine root cause",
            files=[],
            steps=["Inspect relevant files", "Implement fix", "Run tests"],
            confidence=0.3,
        )
