"""Heuristic regression risk estimator."""
from __future__ import annotations


def estimate_regression_risk(diff: str, plan_files: list[str] | None = None) -> float:
    """Returns risk score 0-1. Higher = more risky."""
    if not diff:
        return 1.0

    lines = diff.splitlines()
    added = sum(1 for l in lines if l.startswith('+') and not l.startswith('+++'))
    removed = sum(1 for l in lines if l.startswith('-') and not l.startswith('---'))

    touched = {l[6:] for l in lines if l.startswith('+++ b/')}

    risk = 0.0
    risk += min(0.3, (added + removed) / 200)
    risk += min(0.3, len(touched) * 0.1)

    if plan_files:
        unrelated = [f for f in touched if f not in plan_files]
        risk += min(0.4, len(unrelated) * 0.2)

    return min(1.0, risk)
