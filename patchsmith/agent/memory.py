"""In-session observation memory (ephemeral, not persisted)."""
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class Observation:
    step: str
    output: str
    relevant: bool = True


class AgentMemory:
    def __init__(self, max_size: int = 50):
        self._observations: list[Observation] = []
        self.max_size = max_size

    def add(self, obs: Observation) -> None:
        self._observations.append(obs)
        if len(self._observations) > self.max_size:
            self._observations.pop(0)

    def recent(self, n: int = 10) -> list[Observation]:
        return self._observations[-n:]

    def format(self, n: int = 10) -> str:
        return "\n".join(
            f"[{o.step}]: {o.output[:200]}" for o in self.recent(n)
        )
