"""Composite patch scorer."""
from __future__ import annotations
import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

from patchsmith.verification.tests import run_tests
from patchsmith.verification.lint import run_lint
from patchsmith.verification.regression import estimate_regression_risk

logger = logging.getLogger(__name__)


@dataclass
class PatchScore:
    total: float = 0.0
    passes: bool = False
    test_pass_rate: float = 0.0
    lint_score: float = 0.0
    regression_risk: float = 0.0
    details: dict = field(default_factory=dict)


class PatchScorer:
    async def score(self, candidate: Any, repo_path: str) -> PatchScore:
        from patchsmith.patching.applier import apply_diff, revert_diff
        from patchsmith.patching.diff import validate_diff

        # Validate diff structure
        ok, msg = validate_diff(candidate.diff)
        if not ok:
            logger.warning("Invalid diff for %s: %s", candidate.strategy, msg)
            return PatchScore(total=0.0, passes=False, details={"error": msg})

        # Apply patch
        applied, apply_out = await apply_diff(candidate.diff, repo_path)
        if not applied:
            logger.info("Patch failed to apply (%s): %s", candidate.strategy, apply_out[:200])
            return PatchScore(total=0.0, passes=False, details={"apply": apply_out})

        try:
            # Run tests and lint in parallel
            test_passed, test_rate, test_out = await run_tests(repo_path)
            lint_score, lint_out = await run_lint(repo_path, candidate.files_modified or None)
            regression_risk = estimate_regression_risk(candidate.diff, candidate.files_modified)

            # Composite score
            total = (
                test_rate * 0.40
                + lint_score * 0.20
                + (1.0 - regression_risk) * 0.25
                + (0.15 if len(candidate.diff.splitlines()) < 50 else 0.0)
            )

            score = PatchScore(
                total=total,
                passes=test_passed,
                test_pass_rate=test_rate,
                lint_score=lint_score,
                regression_risk=regression_risk,
                details={"test_out": test_out[:500], "lint_out": lint_out[:200]},
            )
        finally:
            # Always revert the patch so repo is clean for next candidate
            await revert_diff(candidate.diff, repo_path)

        return score
