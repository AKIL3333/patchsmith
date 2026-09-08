"""Evaluation metrics dataclass."""
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class EvalMetrics:
    total: int = 0
    resolved: int = 0
    failed: int = 0
    errors: int = 0
    avg_score: float = 0.0
    avg_candidates: float = 0.0
    component_flags: dict[str, bool] = field(default_factory=dict)

    @property
    def resolve_rate(self) -> float:
        return self.resolved / max(self.total, 1)

    def summary(self) -> str:
        return (
            f"Total: {self.total} | Resolved: {self.resolved} "
            f"({self.resolve_rate:.1%}) | Failed: {self.failed} | "
            f"Avg score: {self.avg_score:.3f}"
        )
