"""Diff parse and validate utilities."""
from __future__ import annotations
import difflib
import re


def generate_diff(original: str, modified: str, filename: str) -> str:
    orig_lines = original.splitlines(keepends=True)
    mod_lines = modified.splitlines(keepends=True)
    diff = difflib.unified_diff(orig_lines, mod_lines,
                                 fromfile=f"a/{filename}", tofile=f"b/{filename}")
    return "".join(diff)


def validate_diff(diff: str) -> tuple[bool, str]:
    if not diff.strip():
        return False, "Empty diff"
    if "+++" not in diff or "---" not in diff:
        return False, "Missing diff headers"
    if "@@" not in diff:
        return False, "No hunks found"
    return True, "OK"


def parse_diff(diff: str) -> list[dict]:
    """Return list of hunks with old_start, old_count, new_start, new_count."""
    hunk_re = re.compile(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
    hunks = []
    for m in hunk_re.finditer(diff):
        hunks.append({
            "old_start": int(m.group(1)),
            "old_count": int(m.group(2) or 1),
            "new_start": int(m.group(3)),
            "new_count": int(m.group(4) or 1),
        })
    return hunks
