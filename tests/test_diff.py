"""Tests for diff utilities."""
from patchsmith.patching.diff import generate_diff, parse_diff, validate_diff


def test_generate_diff():
    diff = generate_diff("x = 1\ny = 2\n", "x = 1\ny = 3\n", "test.py")
    assert "-y = 2" in diff
    assert "+y = 3" in diff


def test_validate_diff_valid():
    diff = (
        "--- a/test.py\n+++ b/test.py\n"
        "@@ -1,2 +1,2 @@\n"
        " x = 1\n-y = 2\n+y = 3\n"
    )
    ok, msg = validate_diff(diff)
    assert ok, msg


def test_validate_diff_empty():
    ok, msg = validate_diff("")
    assert not ok
    assert "Empty" in msg


def test_parse_diff_hunks():
    diff = (
        "--- a/f.py\n+++ b/f.py\n"
        "@@ -1,3 +1,3 @@\n"
        " a = 1\n-b = 2\n+b = 99\n c = 3\n"
    )
    hunks = parse_diff(diff)
    assert len(hunks) == 1
    assert hunks[0]["old_start"] == 1
