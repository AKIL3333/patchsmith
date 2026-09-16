"""Apply a unified diff to a repository."""
from __future__ import annotations
import asyncio
import logging
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


async def apply_diff(diff: str, repo_path: str) -> tuple[bool, str]:
    """Apply unified diff via `patch`. Returns (success, output)."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".patch", delete=False) as f:
        f.write(diff)
        patch_file = f.name

    proc = await asyncio.create_subprocess_exec(
        "patch", "-p1", "--input", patch_file,
        cwd=repo_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    stdout, _ = await proc.communicate()
    output = stdout.decode(errors="replace")
    success = proc.returncode == 0

    Path(patch_file).unlink(missing_ok=True)
    return success, output


async def revert_diff(diff: str, repo_path: str) -> tuple[bool, str]:
    """Revert a previously applied patch."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".patch", delete=False) as f:
        f.write(diff)
        patch_file = f.name

    proc = await asyncio.create_subprocess_exec(
        "patch", "-p1", "--reverse", "--input", patch_file,
        cwd=repo_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    stdout, _ = await proc.communicate()
    Path(patch_file).unlink(missing_ok=True)
    return proc.returncode == 0, stdout.decode(errors="replace")
