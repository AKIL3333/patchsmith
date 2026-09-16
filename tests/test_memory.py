"""Tests for memory store."""
import tempfile
import pytest
from patchsmith.memory.store import MemoryStore
from patchsmith.agent.planner import RepairPlan
from patchsmith.patching.generator import Candidate


@pytest.mark.asyncio
async def test_failure_roundtrip():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = MemoryStore(tmpdir)
        plan = RepairPlan(
            problem="Parser crashes on None",
            hypothesis="missing guard",
            files=["parser.py"],
            steps=["add guard"],
        )
        await store.record_failure(plan, "no candidate passed")
        failures = await store.get_relevant_failures("parser crashes None")
        assert len(failures) > 0
        assert "Parser crashes" in failures[0]


@pytest.mark.asyncio
async def test_success_roundtrip():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = MemoryStore(tmpdir)
        plan = RepairPlan(
            problem="Off by one error",
            hypothesis="index boundary",
            files=["utils.py"],
            steps=["fix index"],
        )
        candidate = Candidate(
            strategy="minimal",
            diff="--- a/utils.py\n+++ b/utils.py\n@@ -1 +1 @@\n-x[n]\n+x[n-1]\n",
            explanation="fixed boundary",
            files_modified=["utils.py"],
        )
        await store.record_success(plan, candidate)
        # no assertion - just must not raise
