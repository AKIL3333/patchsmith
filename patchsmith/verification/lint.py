"""flake8 lint checker."""
from __future__ import annotations
import asyncio
import logging

logger = logging.getLogger(__name__)


async def run_lint(repo_path: str, files: list[str] | None = None) -> tuple[float, str]:
    """Returns (score 0-1, output). 1.0 = no errors."""
    cmd = ["python", "-m", "flake8", "--max-line-length=100", "--statistics"]
    if files:
        cmd.extend(files)
    else:
        cmd.append(".")

    proc = await asyncio.create_subprocess_exec(
        *cmd, cwd=repo_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    stdout, _ = await proc.communicate()
    output = stdout.decode(errors="replace")
    n_errors = output.count("\n")
    score = max(0.0, 1.0 - n_errors * 0.05)
    return score, output[:1000]
