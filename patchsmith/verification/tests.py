"""pytest runner for candidate verification."""
from __future__ import annotations
import asyncio
import logging

logger = logging.getLogger(__name__)


async def run_tests(repo_path: str, timeout: int = 120) -> tuple[bool, float, str]:
    """Returns (any_passed, pass_rate, output)."""
    proc = await asyncio.create_subprocess_exec(
        "python", "-m", "pytest", "-x", "-q", "--tb=short",
        cwd=repo_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    try:
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        return False, 0.0, "TIMEOUT"

    output = stdout.decode(errors="replace")
    pass_rate = _parse_pass_rate(output)
    passed = proc.returncode == 0
    return passed, pass_rate, output[:2000]


def _parse_pass_rate(output: str) -> float:
    import re
    m = re.search(r"(\d+) passed", output)
    f = re.search(r"(\d+) failed", output)
    passed = int(m.group(1)) if m else 0
    failed = int(f.group(1)) if f else 0
    total = passed + failed
    if total == 0:
        return 1.0  # no tests = not a failure
    return passed / total
