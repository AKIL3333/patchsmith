"""Multi-candidate orchestration."""
from __future__ import annotations
import asyncio
import logging
from typing import Any

from patchsmith.patching.generator import PatchGenerator, Candidate

logger = logging.getLogger(__name__)
STRATEGIES = ["minimal", "defensive", "refactor"]


class CandidateManager:
    def __init__(self, config: dict[str, Any]):
        self.generator = PatchGenerator(config)

    async def generate(
        self,
        plan: Any,
        context: Any,
        task: Any,
        n: int = 3,
    ) -> list[Candidate]:
        strategies = STRATEGIES[:n]
        tasks = [
            self.generator.generate(strategy=s, plan=plan, context=context, task=task)
            for s in strategies
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        candidates = []
        for s, r in zip(strategies, results):
            if isinstance(r, Exception):
                logger.warning("Candidate generation failed for %s: %s", s, r)
            elif r is not None:
                candidates.append(r)
        return candidates
