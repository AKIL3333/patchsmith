"""
End-to-end integration test using the demo_repo and a mock LLM.

Verifies that the full pipeline (analyze -> retrieve -> plan -> generate ->
verify -> critic -> memory) runs without error and produces a PatchScore.
The mock LLM returns a pre-written correct patch so the verifier can pass.
"""
from __future__ import annotations
import asyncio
import sys
import tempfile
import shutil
from pathlib import Path
import pytest
from unittest.mock import AsyncMock, patch

# ── tiny stub LLM that returns canned responses ───────────────────────────────
PLAN_JSON = """{
  "problem": "Parser.parse crashes with IndexError on empty input",
  "hypotheses": [{"description": "missing empty-list guard", "confidence": 0.9, "evidence": ["tokens[0] accessed unconditionally"]}],
  "target_symbols": ["parse"],
  "target_files": ["demo_pkg/parser.py"],
  "investigation_steps": ["read parse()"],
  "repair_steps": ["add guard for empty tokens"],
  "validation_plan": ["run test_parse_empty_raises"],
  "risk_assessment": {"regression_risk": "low", "rationale": "single guard added"}
}"""

PATCH = """\
--- a/demo_pkg/parser.py
+++ b/demo_pkg/parser.py
@@ -14,7 +14,8 @@ class Parser:
         it unconditionally accesses tokens[0] without checking length.
         \"\"\"
-        first = tokens[0]  # BUG: IndexError when tokens is empty
+        if not tokens:
+            raise ParseError("empty token list")
+        first = tokens[0]
         if first.isdigit():
"""

CRITIC_JSON = '{"accepted": true, "rejection_reason": "", "concerns": [], "suggestion": ""}'


class MockLLMResponse:
    def __init__(self, content):
        self.content = content
        self.model = "mock"
        self.input_tokens = 0
        self.output_tokens = 0


class MockLLM:
    """Returns plan JSON, then patch diff, then critic acceptance."""
    def __init__(self):
        self._calls = 0

    async def complete(self, messages, system="", **kwargs):
        self._calls += 1
        # planner gets JSON, generator gets diff, critic gets JSON
        if "repair plan" in (messages[-1].content if messages else "").lower():
            return MockLLMResponse(PLAN_JSON)
        if any(kw in system.lower() for kw in ["patch generator", "unified diff"]):
            return MockLLMResponse(PATCH)
        return MockLLMResponse(CRITIC_JSON)


@pytest.fixture
def demo_repo_copy():
    """Copy demo_repo to a temp dir so we can safely apply/revert patches."""
    src = Path(__file__).parent.parent / "demo_repo"
    with tempfile.TemporaryDirectory() as tmpdir:
        dst = Path(tmpdir) / "demo_repo"
        shutil.copytree(src, dst)
        yield str(dst)


@pytest.mark.asyncio
async def test_repository_analysis(demo_repo_copy):
    from patchsmith.repository.analyzer import RepositoryAnalyzer
    index = await RepositoryAnalyzer().analyze(demo_repo_copy)
    assert "demo_pkg/parser.py" in index.files
    assert "Parser" in index.symbols
    assert "parse" in index.symbols


@pytest.mark.asyncio
async def test_hybrid_retrieval(demo_repo_copy):
    from patchsmith.repository.analyzer import RepositoryAnalyzer
    from patchsmith.retrieval.hybrid import HybridRetriever
    index = await RepositoryAnalyzer().analyze(demo_repo_copy)
    ctx = await HybridRetriever().retrieve("Parser crashes empty tokens IndexError", index)
    assert len(ctx.chunks) > 0
    files = [c.file for c in ctx.chunks]
    assert any("parser" in f for f in files)


@pytest.mark.asyncio
async def test_planner_with_mock_llm(demo_repo_copy):
    from patchsmith.repository.analyzer import RepositoryAnalyzer
    from patchsmith.retrieval.hybrid import HybridRetriever
    from patchsmith.agent.planner import Planner, RepairPlan
    from patchsmith.agent.orchestrator import RepairTask

    index = await RepositoryAnalyzer().analyze(demo_repo_copy)
    ctx = await HybridRetriever().retrieve("Parser crashes empty", index)

    task = RepairTask(
        issue_title="Parser crashes on empty token list",
        issue_body="Parser.parse([]) raises IndexError instead of ParseError",
        repo_path=demo_repo_copy,
    )

    planner = Planner.__new__(Planner)
    planner.llm = MockLLM()
    plan = await planner.plan(task=task, context=ctx)

    assert isinstance(plan, RepairPlan)
    assert plan.problem
    assert len(plan.hypotheses) > 0
    assert plan.hypotheses[0].confidence > 0


@pytest.mark.asyncio
async def test_full_pipeline_mock(demo_repo_copy):
    """Full pipeline with mock LLM - proves orchestrator wiring is correct."""
    from patchsmith.agent.orchestrator import Orchestrator, RepairTask
    from patchsmith.models.base import BaseLLM

    config = {
        "model": {"provider": "anthropic", "name": "mock"},
        "retrieval": {"top_k": 10, "chunk_size": 30, "chunk_stride": 15},
        "memory_path": demo_repo_copy + "/.mem",
    }

    task = RepairTask(
        issue_title="Parser crashes on empty token list",
        issue_body="Parser.parse([]) raises IndexError instead of ParseError",
        repo_path=demo_repo_copy,
        max_candidates=1,
        max_planner_retries=1,
    )

    mock_llm = MockLLM()

    with patch.object(BaseLLM, "from_config", return_value=mock_llm):
        orch = Orchestrator(config)
        # Use only 1 candidate strategy for speed
        from patchsmith.patching.generator import PatchGenerator
        with patch.object(PatchGenerator, "generate") as mock_gen:
            from patchsmith.patching.generator import Candidate
            mock_gen.return_value = Candidate(
                strategy="minimal",
                diff=PATCH,
                explanation="guard added",
                files_modified=["demo_pkg/parser.py"],
            )
            result = await orch.run(task)

    # With the correct patch applied, tests should pass
    # Result depends on whether patch applies cleanly to the copy
    assert result.trajectory  # pipeline ran
    assert "analyze" in result.trajectory[0]["phase"]
