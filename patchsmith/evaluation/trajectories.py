"""Trajectory recorder for replaying and analysing repair runs."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any


class TrajectoryRecorder:
    def __init__(self, output_path: str):
        self.output_path = Path(output_path)
        self._records: list[dict] = []

    def record(self, task_id: str, result: Any, trajectory: list[dict]) -> None:
        self._records.append({
            "task_id": task_id,
            "success": result.success,
            "patch_score": result.patch_score,
            "candidates_tried": result.candidates_tried,
            "error": result.error,
            "trajectory": trajectory,
        })

    def save(self) -> None:
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        with self.output_path.open("w") as f:
            for r in self._records:
                f.write(json.dumps(r) + "\n")
