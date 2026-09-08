"""
PatchSmith Orchestrator

Coordinates the full repair pipeline:
  Issue -> Repository Analysis -> Retrieval -> Planning
        -> Patch Generation -> Verification -> Critic -> Memory
"""
from __future__ import annotations
import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

from patchsmith.agent.planner import Planner, RepairPlan
from patchsmith.agent.executor import Executor
from patchsmith.agent.critic import Critic
from patchsmith.repository.analyzer import RepositoryAnalyzer
from patchsmith.retrieval.hybrid import HybridRetriever
from patchsmith.patching.candidates import CandidateManager
from patchsmith.verification.scorer import PatchScorer
from patchsmith.memory.store import MemoryStore

logger = logging.getLogger(__name__)


@dataclass
class RepairTask:
    issue_title: str
    issue_body: str
    repo_path: str
    issue_number: int | None = None
    github_repo: str | None = None
    max_candidates: int = 3
    max_planner_retries: int = 3


@dataclass
class RepairResult:
    success: bool
    patch: str | None = None
    patch_score: float | None = None
    plan: RepairPlan | None = None
    candidates_tried: int = 0
    error: str | None = None
    trajectory: list[dict] = field(default_factory=list)


class Orchestrator:
    """
    Top-level pipeline coordinator.

    Retry/critic loop:
      issue -> analyze -> retrieve -> plan -> generate N candidates
      -> verify each -> critic gates -> return best or loop back to planner.
    """

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.analyzer = RepositoryAnalyzer()
        self.retriever = HybridRetriever(
            top_k=config.get("retrieval", {}).get("top_k", 20),
            chunk_size=config.get("retrieval", {}).get("chunk_size", 40),
            chunk_stride=config.get("retrieval", {}).get("chunk_stride", 20),
        )
        self.planner = Planner(config)
        self.executor = Executor(config)
        self.critic = Critic(config)
        self.candidate_manager = CandidateManager(config)
        self.scorer = PatchScorer()
        self.memory_store = MemoryStore(config.get("memory_path", ".patchsmith_memory"))

    async def run(self, task: RepairTask) -> RepairResult:
        traj: list[dict] = []
        result = RepairResult(success=False, trajectory=traj)

        try:
            # Phase 1: Repository analysis
            traj.append({"phase": "analyze", "status": "start"})
            logger.info("Analyzing repository: %s", task.repo_path)
            repo_index = await self.analyzer.analyze(task.repo_path)
            traj.append({"phase": "analyze", "status": "done", "files": len(repo_index.files)})

            # Phase 2: Hybrid retrieval
            traj.append({"phase": "retrieve", "status": "start"})
            context = await self.retriever.retrieve(
                query=f"{task.issue_title}\n{task.issue_body}",
                repo_index=repo_index,
            )
            traj.append({"phase": "retrieve", "status": "done", "chunks": len(context.chunks)})
            logger.info("Retrieved %d context chunks", len(context.chunks))

            # Phase 3: Load relevant failure memories
            past_failures = await self.memory_store.get_relevant_failures(
                task.issue_title + " " + task.issue_body
            )
            if past_failures:
                logger.info("Found %d relevant past failures", len(past_failures))

            # Phase 4: Plan -> generate -> verify loop
            for attempt in range(task.max_planner_retries):
                logger.info("Planning attempt %d/%d", attempt + 1, task.max_planner_retries)
                plan = await self.planner.plan(
                    task=task,
                    context=context,
                    past_failures=past_failures,
                    attempt=attempt,
                )
                traj.append({"phase": "plan", "attempt": attempt,
                             "steps": len(plan.steps), "confidence": plan.confidence})

                candidates = await self.candidate_manager.generate(
                    plan=plan, context=context, task=task, n=task.max_candidates,
                )
                traj.append({"phase": "generate", "candidates": len(candidates)})
                logger.info("Generated %d candidates", len(candidates))

                best_patch = None
                best_score = -1.0

                for candidate in candidates:
                    score = await self.scorer.score(candidate=candidate, repo_path=task.repo_path)
                    logger.info("Candidate [%s]: score=%.3f passes=%s",
                                candidate.strategy, score.total, score.passes)
                    if score.passes and score.total > best_score:
                        best_score = score.total
                        best_patch = candidate

                if best_patch:
                    verdict = await self.critic.evaluate(plan=plan, patch=best_patch, task=task)
                    if verdict.accepted:
                        result.success = True
                        result.patch = best_patch.diff
                        result.patch_score = best_score
                        result.plan = plan
                        result.candidates_tried = len(candidates) * (attempt + 1)
                        await self.memory_store.record_success(plan, best_patch)
                        logger.info("Repair succeeded on attempt %d", attempt + 1)
                        break
                    else:
                        logger.info("Critic rejected: %s", verdict.rejection_reason)
                        await self.memory_store.record_failure(plan, verdict.rejection_reason)
                        past_failures.append(verdict.rejection_reason)
                else:
                    logger.info("No candidate passed verification on attempt %d", attempt + 1)
                    await self.memory_store.record_failure(plan, "no candidate passed verification")

        except Exception as exc:
            logger.exception("Orchestrator error: %s", exc)
            result.error = str(exc)

        return result
