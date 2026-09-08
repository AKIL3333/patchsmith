# PatchSmith

**Autonomous Code Repair & Software Engineering Research Platform**

PatchSmith combines repository-aware retrieval, explicit repair planning, multi-candidate patch generation, execution-based verification, and failure memory to repair bugs at the repository level.

> **Research question:** Can repository-aware planning, evidence-grounded retrieval, candidate patch generation, and execution-based verification make autonomous software-engineering agents more reliable than simple tool-using LLM loops?

---

## Architecture

```
                     GitHub Issue
                          |
                          v
                Task Understanding
                          |
                          v
             Repository Analyzer
            /        |         \
         Files    Symbols     Tests
            \        |         /
                     v
             Hybrid Retriever
          (lexical + semantic + symbol)
                     |
                     v
                  Planner
                     |
               Repair Plan
                     |
       .-------------|-------------.
       v             v             v
   Candidate A   Candidate B   Candidate C
   (minimal)    (defensive)   (refactor)
       |             |             |
       '-------------|-------------'
                     v
              Patch Verifier
        (tests + lint + regression risk)
                     |
            .--------+--------.
            v                 v
          FAIL              PASS
            |                 v
            v            Critic Agent
         Memory              |
            |         .------+------.
            v         v             v
         Planner    Reject        Accept
                      |             |
                      v             v
                   Planner      Final Patch
```

---

## Key Components

| Module | Purpose |
|--------|---------|
| `patchsmith/repository/` | AST-based indexer: files, classes, functions, call graphs, git history |
| `patchsmith/retrieval/` | Hybrid BM25 + embedding + symbol retrieval with re-ranking |
| `patchsmith/agent/planner.py` | Produces structured `RepairPlan` (hypothesis, target files, steps) |
| `patchsmith/patching/` | Generates 3 candidates per plan: minimal / defensive / refactor |
| `patchsmith/verification/` | Scores patches: test rate, lint, type errors, regression risk |
| `patchsmith/agent/critic.py` | LLM review: does this actually fix the issue? |
| `patchsmith/memory/` | Persists failures/successes; feeds past failures back to the planner |

---

## Quick Start

```bash
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

## Evaluation (SWE-bench)

```bash
pip install -e ".[eval]"
python -m patchsmith.evaluation.swebench --split lite --output results/run_001.jsonl
```

Ablation matrix - measure each component's contribution:

| System | Retrieval | Planner | Critic | Memory | Resolved |
|--------|-----------|---------|--------|--------|----------|
| Baseline | - | - | - | - | ? |
| +Retrieval | YES | - | - | - | ? |
| +Planner | YES | YES | - | - | ? |
| +Critic | YES | YES | YES | - | ? |
| PatchSmith-Full | YES | YES | YES | YES | ? |

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
├── benchmarks/
├── configs/
├── tests/
└── config.yaml
```

---

## Origins

PatchSmith began as a fork of [SWE-agent](https://github.com/princeton-nlp/SWE-agent) and uses its execution environment as reference infrastructure. The agent architecture - retrieval, planning, multi-candidate generation, verification, and memory - is a complete reimplementation.

## License

MIT
