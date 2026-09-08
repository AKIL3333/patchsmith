"""Successful repair store utilities."""
from __future__ import annotations
import json
from pathlib import Path
from dataclasses import dataclass


@dataclass
class RepairRecord:
    problem: str
    hypothesis: str
    files: list[str]
    strategy: str
    diff_lines: int


def load_repairs(memory_path: str) -> list[RepairRecord]:
    p = Path(memory_path) / "successes.jsonl"
    if not p.exists():
        return []
    records = []
    with p.open() as f:
        for line in f:
            try:
                d = json.loads(line)
                records.append(RepairRecord(**d))
            except Exception:
                continue
    return records
