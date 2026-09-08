"""Heuristic regression risk estimator."""
from __future__ import annotations
from patchsmith.patching.diff import parse_hunks


def estimate_regression_risk(diff: str, repo_files: list[str]) -> float:
    """Returns risk score 0-1. Higher = more risky."""
    if not diff:
        return 1.0

    lines = diff.splitlines()
    added = sum(1 for l in lines if l.startswith("+") and not l.startswith("+++"))
    removed = sum(1 for l in lines if l.startswith("-") and not l.startswith("---"))

    # Files touched
    touched = set()
    for l in lines:
        if l.startswith("+++ b/"):
            touched.add(l[6:])

    risk = 0.0
    # Large diffs are risky
    risk += min(0.3, (added + removed) / 200)
    # Touching many files is risky
    risk += min(0.3, len(touched) * 0.1)
    # Touching files not mentioned in the plan is risky
    unrelated = [f for f in touched if f not in repo_files]
    risk += min(0.4, len(unrelated) * 0.2)

    return min(1.0, risk)


def parse_hunks(diff: str) -> list[dict]:
    from patchsmith.patching.diff import parse_diff
    return parse_diff(diff)
