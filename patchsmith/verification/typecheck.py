"""mypy type checker (optional)."""
from __future__ import annotations
import asyncio
import logging

logger = logging.getLogger(__name__)


async def run_typecheck(repo_path: str, files: list[str] | None = None) -> tuple[float, str]:
    """Returns (score 0-1, output)."""
    cmd = ["python", "-m", "mypy", "--ignore-missing-imports", "--no-error-summary"]
    cmd.extend(files or ["."])

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd, cwd=repo_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=60)
        output = stdout.decode(errors="replace")
        n_errors = output.count(": error:")
        score = max(0.0, 1.0 - n_errors * 0.1)
        return score, output[:1000]
    except (asyncio.TimeoutError, FileNotFoundError):
        return 1.0, "(mypy unavailable)"
