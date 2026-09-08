"""Git history queries."""
from __future__ import annotations
import asyncio
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Commit:
    sha: str
    message: str
    author: str
    date: str
    files: list[str]


async def _run(cmd: list[str], cwd: str) -> str:
    proc = await asyncio.create_subprocess_exec(
        *cmd, cwd=cwd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
    )
    stdout, _ = await proc.communicate()
    return stdout.decode(errors="replace")


class GitHistory:
    def __init__(self, repo_path: str):
        self.repo_path = repo_path

    async def log(self, n: int = 20) -> list[Commit]:
        out = await _run(
            ["git", "log", f"-{n}", "--pretty=format:%H|%s|%an|%ai", "--name-only"],
            self.repo_path,
        )
        commits: list[Commit] = []
        current: dict = {}
        for line in out.splitlines():
            if "|" in line and len(line.split("|")) == 4:
                if current:
                    commits.append(Commit(**current))
                sha, msg, author, date = line.split("|", 3)
                current = {"sha": sha, "message": msg, "author": author, "date": date, "files": []}
            elif line.strip() and current:
                current["files"].append(line.strip())
        if current:
            commits.append(Commit(**current))
        return commits

    async def blame(self, file_path: str, line: int) -> str:
        out = await _run(
            ["git", "blame", "-L", f"{line},{line}", "--porcelain", file_path],
            self.repo_path,
        )
        return out[:500]

    async def show(self, sha: str) -> str:
        out = await _run(["git", "show", "--stat", sha], self.repo_path)
        return out[:2000]
