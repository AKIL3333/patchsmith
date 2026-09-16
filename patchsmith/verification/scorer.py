"""Composite patch scorer with structured evidence."""
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
class TestEvidence:
    passed: int = 0
    failed: int = 0
    new_failures: int = 0
    pass_rate: float = 0.0
    output: str = ""


@dataclass
class LintEvidence:
    errors: int = 0
    score: float = 1.0
    output: str = ""


@dataclass
class DiffEvidence:
    files_changed: int = 0
    lines_added: int = 0
    lines_removed: int = 0


@dataclass
class PatchEvidence:
    tests: TestEvidence = field(default_factory=TestEvidence)
    lint: LintEvidence = field(default_factory=LintEvidence)
    diff: DiffEvidence = field(default_factory=DiffEvidence)
    regression_risk: float = 0.0


@dataclass
class PatchScore:
    total: float = 0.0
    passes: bool = False
    test_pass_rate: float = 0.0
    lint_score: float = 0.0
    regression_risk: float = 0.0
    evidence: PatchEvidence = field(default_factory=PatchEvidence)
    error: str = ""


def _parse_diff_evidence(diff: str) -> DiffEvidence:
    added = sum(1 for l in diff.splitlines() if l.startswith("+") and not l.startswith("+++"))
    removed = sum(1 for l in diff.splitlines() if l.startswith("-") and not l.startswith("---"))
    files = {l[6:] for l in diff.splitlines() if l.startswith("+++ b/")}
    return DiffEvidence(files_changed=len(files), lines_added=added, lines_removed=removed)


class PatchScorer:
    async def score(self, candidate: Any, repo_path: str) -> PatchScore:
        from patchsmith.patching.applier import apply_diff, revert_diff
        from patchsmith.patching.diff import validate_diff

        ok, msg = validate_diff(candidate.diff)
        if not ok:
            logger.warning("Invalid diff for %s: %s", candidate.strategy, msg)
            return PatchScore(error=msg)

        applied, apply_out = await apply_diff(candidate.diff, repo_path)
        if not applied:
            logger.info("Patch failed to apply (%s): %s", candidate.strategy, apply_out[:200])
            return PatchScore(error=f"apply failed: {apply_out[:200]}")

        evidence = PatchEvidence(diff=_parse_diff_evidence(candidate.diff))

        try:
            test_passed, test_rate, test_out = await run_tests(repo_path)
            lint_score, lint_out = await run_lint(repo_path, candidate.files_modified or None)
            regression_risk = estimate_regression_risk(candidate.diff, candidate.files_modified)

            # Parse test counts
            import re
            pm = re.search(r"(\d+) passed", test_out)
            fm = re.search(r"(\d+) failed", test_out)
            p = int(pm.group(1)) if pm else 0
            f = int(fm.group(1)) if fm else 0
            lint_errors = lint_out.count("\n") if lint_out.strip() else 0

            evidence.tests = TestEvidence(
                passed=p, failed=f, pass_rate=test_rate, output=test_out[:500]
            )
            evidence.lint = LintEvidence(
                errors=lint_errors, score=lint_score, output=lint_out[:200]
            )
            evidence.regression_risk = regression_risk

            total = (
                test_rate * 0.40
                + lint_score * 0.20
                + (1.0 - regression_risk) * 0.25
                + (0.15 if evidence.diff.lines_added + evidence.diff.lines_removed < 50 else 0.0)
            )

            return PatchScore(
                total=total,
                passes=test_passed,
                test_pass_rate=test_rate,
                lint_score=lint_score,
                regression_risk=regression_risk,
                evidence=evidence,
            )
        finally:
            await revert_diff(candidate.diff, repo_path)
