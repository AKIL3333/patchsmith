# PatchSmith

**Autonomous Code Repair & Software Engineering Research Platform**

PatchSmith is an autonomous software-engineering agent that repairs bugs at the repository level.
It combines repository-aware retrieval, explicit structured planning, multi-candidate patch
generation, execution-based verification, and cross-run failure memory.

---

## Research Questions

PatchSmith is designed as an experimental platform for answering these questions:

| # | Question |
|---|---------|
| RQ1 | Does repository-aware retrieval improve repair success vs. naive file-dumping? |
| RQ2 | Does explicit structured planning reduce tool calls and improve repair rate? |
| RQ3 | Does multi-candidate patch generation improve patch validity? |
| RQ4 | Does critic-based verification reduce incorrect or regressive patches? |
| RQ5 | Does persistent failure memory improve performance on recurring failure patterns? |
| RQ6 | What is the cost/latency tradeoff of each component? |

The ablation framework in `benchmarks/` measures each component's contribution independently.

---

## Architecture

```
                       GitHub Issue
                            |
                            v
                  Task Understanding
                            |
                            v
               Repository Analyzer          <-- files, classes, functions,
              /        |         \              call graphs, git history
           Files    Symbols     Tests
              \        |         /
                       v
               Hybrid Retriever             <-- BM25 + symbol + embedding
          (lexical + symbol + semantic)         source-weighted re-ranking
                       |
                       v
                    Planner                 <-- structured RepairPlan with
                       |                        hypotheses + evidence
                  Repair Plan
                       |
         .-------------|-------------.
         v             v             v
     Candidate A   Candidate B   Candidate C
     (minimal)    (defensive)   (refactor)
         |             |             |
         '-------------|-------------'
                       v
              Patch Verifier              <-- apply -> pytest + flake8
           (tests + lint + regression)       structured PatchEvidence
                       |
              .--------+--------.
              v                 v
            FAIL              PASS
              |                 v
              v            Critic Agent   <-- LLM review gate
           Memory               |
              |          .------+------.
              v          v             v
           Planner     Reject        Accept
                         |             |
                         v             v
                      Planner      Final Patch
```

Memory feeds both retrieval (past failures surface relevant context) and the
planner (failed strategies are passed explicitly to avoid repetition).

---

## Key Components

| Module | Purpose |
|--------|---------|
| `repository/analyzer.py` | AST-based repo indexer: files, classes, functions, call graphs |
| `repository/git_history.py` | git log/blame/show queries as additional evidence |
| `retrieval/hybrid.py` | BM25 + symbol + embedding retrieval, merged and re-ranked |
| `agent/planner.py` | Structured `RepairPlan`: hypotheses with confidence + evidence, target symbols, validation plan |
| `patching/candidates.py` | Generates 3 candidates per plan: minimal / defensive / refactor |
| `verification/scorer.py` | Applies patch, runs tests + lint, produces structured `PatchEvidence` |
| `agent/critic.py` | LLM review gate: does this actually fix the issue? |
| `memory/store.py` | JSONL-based cross-run failure/success store with relevance lookup |
| `models/anthropic.py` | Claude backend with prompt caching |
| `evaluation/swebench.py` | SWE-bench runner + ablation framework |

---

## The RepairPlan

The planner produces a structured plan rather than a flat list of steps:

```json
{
  "problem": "Parser.parse crashes with IndexError on empty input",
  "hypotheses": [
    {
      "description": "parse() accesses tokens[0] without checking length",
      "confidence": 0.92,
      "evidence": ["line 18: first = tokens[0]  # unconditional"]
    }
  ],
  "target_symbols": ["parse"],
  "target_files": ["demo_pkg/parser.py"],
  "investigation_steps": ["Read Parser.parse()", "Confirm no upstream guard"],
  "repair_steps": ["Add empty-list check before tokens[0] access"],
  "validation_plan": ["test_parse_empty_raises must pass", "existing tests must not regress"],
  "risk_assessment": {"regression_risk": "low", "rationale": "single guard added"}
}
```

---

## Verification Evidence

The verifier returns structured evidence, not just a pass/fail:

```python
PatchEvidence(
    tests=TestEvidence(passed=4, failed=0, pass_rate=1.0),
    lint=LintEvidence(errors=0, score=1.0),
    diff=DiffEvidence(files_changed=1, lines_added=3, lines_removed=1),
    regression_risk=0.05,
)
```

The scorer computes: `0.40*test_rate + 0.20*lint + 0.25*(1-regression_risk) + 0.15*size_bonus`

---

## Quick Start

```bash
git clone https://github.com/AKIL3333/patchsmith
cd patchsmith
pip install -e .
export ANTHROPIC_API_KEY=sk-ant-...

# Analyze a repository
patchsmith analyze --repo /path/to/repo --symbols

# Repair a bug
patchsmith repair \
  --repo /path/to/repo \
  --issue-title "Parser crashes on empty objects" \
  --issue-body "Passing {} raises AttributeError in Parser.parse()" \
  --output patch.diff
```

---

## Demo

The `demo_repo/` directory contains a minimal broken Python package with a known bug
(`IndexError` on empty input instead of `ParseError`). Use it to verify the pipeline works
before running against real repositories:

```bash
# Confirm the bug exists
cd demo_repo && pytest tests/ -v
# 1 FAILED: test_parse_empty_raises (IndexError)

# Run PatchSmith against it
cd ..
patchsmith repair \
  --repo demo_repo \
  --issue-title "Parser crashes on empty token list" \
  --issue-body "Parser.parse([]) raises IndexError; should raise ParseError" \
  --output demo.diff
```

---

## Evaluation (SWE-bench)

```bash
pip install -e ".[eval]"
python -m patchsmith.evaluation.swebench --split lite --output results/run_001.jsonl
```

Ablation matrix - each row enables one more component:

| System | Retrieval | Planner | Critic | Memory | Resolved |
|--------|-----------|---------|--------|--------|----------|
| Baseline | - | - | - | - | ? |
| +Retrieval | YES | - | - | - | ? |
| +Planner | YES | YES | - | - | ? |
| +Critic | YES | YES | YES | - | ? |
| PatchSmith-Full | YES | YES | YES | YES | ? |

Results will be filled in as experiments are run.

---

## Project Structure

```
patchsmith/
├── patchsmith/
│   ├── agent/          # orchestrator, planner, executor, critic, memory
│   ├── repository/     # analyzer, git history, dependency graph
│   ├── retrieval/      # lexical, semantic, symbol, hybrid, reranker
│   ├── patching/       # generator, candidates, applier, diff
│   ├── verification/   # tests, lint, typecheck, regression, scorer
│   ├── memory/         # failures, repairs, store
│   ├── models/         # anthropic, openai backends
│   └── evaluation/     # swebench, metrics, trajectories
├── demo_repo/          # minimal broken package for end-to-end testing
├── benchmarks/         # ablation experiment scripts
├── configs/
├── tests/
└── config.yaml
```

---

## Multi-model support

PatchSmith is model-agnostic. Set `provider` in `config.yaml`:

```yaml
model:
  provider: anthropic   # or: openai
  name: claude-sonnet-4-6
```

This enables experiments comparing repair success across models.

---

## Origins

PatchSmith began as a fork of [SWE-agent](https://github.com/princeton-nlp/SWE-agent).
The core agent architecture - retrieval, planning, multi-candidate generation, verification,
and memory - is a complete reimplementation. SWE-agent code remains in `sweagent/` as
reference infrastructure and for attribution.

## License

MIT
