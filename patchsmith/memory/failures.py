"""Failure pattern analysis utilities."""
from __future__ import annotations
import json
from pathlib import Path
from dataclasses import dataclass


@dataclass
class FailureRecord:
    problem: str
    hypothesis: str
    files: list[str]
    reason: str


def load_failures(memory_path: str) -> list[FailureRecord]:
    p = Path(memory_path) / "failures.jsonl"
    if not p.exists():
        return []
    records = []
    with p.open() as f:
        for line in f:
            try:
                d = json.loads(line)
                records.append(FailureRecord(**d))
            except Exception:
                continue
    return records
