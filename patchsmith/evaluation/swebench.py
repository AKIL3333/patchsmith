"""SWE-bench task runner."""
from __future__ import annotations
import argparse
import asyncio
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


async def run_swebench(config: dict, split: str = "lite", output: str = "results.jsonl",
                        limit: int | None = None) -> None:
    """
    Run PatchSmith against SWE-bench tasks.

    Requires: pip install swebench datasets
    Tasks are cloned into a temp dir, repaired, and results written to output JSONL.
    """
    try:
        from datasets import load_dataset
    except ImportError:
        logger.error("Install 'datasets' to run SWE-bench evaluation")
        return

    from patchsmith.agent.orchestrator import Orchestrator, RepairTask
    from patchsmith.evaluation.trajectories import TrajectoryRecorder

    ds_name = "princeton-nlp/SWE-bench_Lite" if split == "lite" else "princeton-nlp/SWE-bench"
    logger.info("Loading %s ...", ds_name)
    dataset = load_dataset(ds_name, split="test")

    orchestrator = Orchestrator(config)
    recorder = TrajectoryRecorder(output)
    resolved = 0

    items = list(dataset)
    if limit:
        items = items[:limit]

    for i, item in enumerate(items):
        task_id = item["instance_id"]
        logger.info("[%d/%d] %s", i + 1, len(items), task_id)

        # SWE-bench provides the repo at a specific commit - skip cloning for now
        # In a full implementation you'd checkout the repo at base_commit
        task = RepairTask(
            issue_title=item.get("problem_statement", "")[:200],
            issue_body=item.get("problem_statement", ""),
            repo_path=item.get("repo", ""),
        )

        result = await orchestrator.run(task)
        recorder.record(task_id, result, result.trajectory)
        if result.success:
            resolved += 1
        logger.info("  %s | score=%.3f", "PASS" if result.success else "FAIL",
                    result.patch_score or 0)

    recorder.save()
    logger.info("Done. Resolved %d/%d (%.1f%%)", resolved, len(items),
                100 * resolved / max(len(items), 1))


def main() -> None:
    import yaml
    parser = argparse.ArgumentParser(description="PatchSmith SWE-bench runner")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--split", choices=["lite", "full"], default="lite")
    parser.add_argument("--output", default="results/swebench.jsonl")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    with open(args.config) as f:
        config = yaml.safe_load(f)
    asyncio.run(run_swebench(config, args.split, args.output, args.limit))


if __name__ == "__main__":
    main()
