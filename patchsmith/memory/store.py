"""Unified memory store - persists failures and successes across runs."""
from __future__ import annotations
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class MemoryStore:
    def __init__(self, memory_path: str):
        self.path = Path(memory_path)
        self.path.mkdir(parents=True, exist_ok=True)
        self._failures_file = self.path / "failures.jsonl"
        self._successes_file = self.path / "successes.jsonl"

    async def record_failure(self, plan: Any, reason: str) -> None:
        entry = {
            "problem": plan.problem,
            "hypothesis": plan.hypothesis,
            "files": plan.files,
            "reason": reason,
        }
        with self._failures_file.open("a") as f:
            f.write(json.dumps(entry) + "\n")

    async def record_success(self, plan: Any, candidate: Any) -> None:
        entry = {
            "problem": plan.problem,
            "hypothesis": plan.hypothesis,
            "files": plan.files,
            "strategy": candidate.strategy,
            "diff_lines": len(candidate.diff.splitlines()),
        }
        with self._successes_file.open("a") as f:
            f.write(json.dumps(entry) + "\n")

    async def get_relevant_failures(self, query: str, max_results: int = 5) -> list[str]:
        if not self._failures_file.exists():
            return []
        query_words = set(query.lower().split())
        scored: list[tuple[float, str]] = []
        with self._failures_file.open() as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    text = f"{entry['problem']} {entry['hypothesis']} {entry['reason']}"
                    overlap = len(query_words & set(text.lower().split()))
                    if overlap > 0:
                        scored.append((overlap, f"{entry['problem']}: {entry['reason']}"))
                except (json.JSONDecodeError, KeyError):
                    continue
        scored.sort(reverse=True)
        return [s for _, s in scored[:max_results]]
