"""Plan step executor - runs shell commands and file edits."""
from __future__ import annotations
import asyncio
import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class StepResult:
    step: str
    output: str
    success: bool


class Executor:
    def __init__(self, config: dict[str, Any]):
        self.config = config

    async def run_step(self, step: str, repo_path: str) -> StepResult:
        """Execute a single plan step description as a shell command if applicable."""
        if any(kw in step.lower() for kw in ["run test", "pytest", "run suite"]):
            out = await self._run_cmd(["python", "-m", "pytest", "-x", "-q"], cwd=repo_path)
            return StepResult(step=step, output=out, success="passed" in out or "no tests" in out)
        return StepResult(step=step, output=f"(non-executable step: {step})", success=True)

    async def _run_cmd(self, cmd: list[str], cwd: str, timeout: int = 60) -> str:
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd, cwd=cwd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            return stdout.decode(errors="replace")[:2000]
        except asyncio.TimeoutError:
            return "TIMEOUT"
        except Exception as e:
            return f"ERROR: {e}"
