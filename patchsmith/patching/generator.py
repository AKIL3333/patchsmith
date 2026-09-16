"""LLM-driven patch generator for a single strategy."""
from __future__ import annotations
import logging
import re
from dataclasses import dataclass, field
from typing import Any

from patchsmith.models.base import BaseLLM, Message

logger = logging.getLogger(__name__)

GENERATOR_SYSTEM = """You are PatchSmith's patch generator.
Given a repair plan and repository context, generate a unified diff patch.

Strategy descriptions:
- minimal: the smallest possible correct fix, touching as few lines as possible
- defensive: fix plus add guards/validation to prevent the entire bug class
- refactor: fix while cleaning up the immediately surrounding code for clarity

Rules:
1. Output ONLY the unified diff (--- / +++ / @@ lines), no prose.
2. Use a/filename and b/filename headers.
3. Do not modify unrelated files.
4. Ensure the patch is syntactically valid Python.
"""


@dataclass
class Candidate:
    strategy: str
    diff: str
    explanation: str
    files_modified: list[str] = field(default_factory=list)


class PatchGenerator:
    def __init__(self, config: dict[str, Any]):
        self.llm = BaseLLM.from_config(config)

    async def generate(
        self,
        strategy: str,
        plan: Any,
        context: Any,
        task: Any,
    ) -> Candidate | None:
        user_msg = (
            f"Issue: {task.issue_title}\n{task.issue_body}\n\n"
            f"Repair plan:\n"
            f"  Problem: {plan.problem}\n"
            f"  Hypothesis: {plan.hypothesis}\n"
            f"  Target files: {', '.join(plan.files)}\n"
            f"  Steps: {chr(10).join(f'  {i+1}. {s}' for i,s in enumerate(plan.steps))}\n\n"
            f"Repository context:\n{context.format(max_chunks=6)}\n\n"
            f"Generate a {strategy} patch. Output unified diff only."
        )

        resp = await self.llm.complete(
            messages=[Message(role="user", content=user_msg)],
            system=GENERATOR_SYSTEM,
            max_tokens=2048,
            temperature=0.1 if strategy == "minimal" else 0.3,
        )

        diff = _extract_diff(resp.content)
        if not diff:
            logger.warning("Generator produced no diff for strategy=%s", strategy)
            return None

        files = _files_from_diff(diff)
        return Candidate(
            strategy=strategy,
            diff=diff,
            explanation=resp.content[:200],
            files_modified=files,
        )


def _extract_diff(text: str) -> str:
    # Try to extract a fenced diff block first
    m = re.search(r"```(?:diff)?\n(.*?)```", text, re.DOTALL)
    if m:
        return m.group(1).strip()
    # Otherwise return lines that look like a unified diff
    lines = [l for l in text.splitlines()
             if l.startswith(("---", "+++", "@@", " ", "+", "-")) or l == ""]
    return "\n".join(lines).strip()


def _files_from_diff(diff: str) -> list[str]:
    files = []
    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            files.append(line[6:])
    return list(set(files))
