"""PatchSmith CLI entry point."""
from __future__ import annotations
import argparse
import asyncio
import json
import logging
import os
import sys
from pathlib import Path


def setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        level=logging.DEBUG if verbose else logging.INFO,
    )


def load_config(config_path: str) -> dict:
    import yaml
    with open(config_path) as f:
        cfg = yaml.safe_load(f)
    if "ANTHROPIC_API_KEY" in os.environ:
        cfg.setdefault("model", {})["api_key"] = os.environ["ANTHROPIC_API_KEY"]
    if "OPENAI_API_KEY" in os.environ:
        cfg.setdefault("model", {})["openai_api_key"] = os.environ["OPENAI_API_KEY"]
    return cfg


async def run_repair(args: argparse.Namespace) -> int:
    from patchsmith.agent.orchestrator import Orchestrator, RepairTask
    config = load_config(args.config)
    orch = Orchestrator(config)
    task = RepairTask(
        issue_title=args.issue_title,
        issue_body=args.issue_body or "",
        repo_path=str(Path(args.repo).resolve()),
        max_candidates=args.candidates,
        max_planner_retries=args.retries,
    )
    print(f"PatchSmith - Repairing: {task.issue_title}")
    print(f"Repository : {task.repo_path}")
    print("-" * 60)
    result = await orch.run(task)
    if result.success:
        print(f"\nSUCCESS  score={result.patch_score:.3f}  candidates={result.candidates_tried}")
        if args.output:
            Path(args.output).write_text(result.patch)
            print(f"Patch written to: {args.output}")
        else:
            print("\n--- PATCH ---")
            print(result.patch)
        if args.trajectory:
            Path(args.trajectory).write_text(json.dumps(result.trajectory, indent=2))
        return 0
    print(f"\nFAILED: {result.error or 'No valid patch found'}")
    return 1


async def run_analyze(args: argparse.Namespace) -> int:
    from patchsmith.repository.analyzer import RepositoryAnalyzer
    analyzer = RepositoryAnalyzer()
    index = await analyzer.analyze(str(Path(args.repo).resolve()))
    print(index.summary())
    if args.symbols:
        print("\nTop symbols:")
        for sym, files in list(index.symbols.items())[:20]:
            print(f"  {sym}: {', '.join(files)}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="patchsmith",
                                description="PatchSmith - Autonomous Code Repair Platform")
    p.add_argument("-v", "--verbose", action="store_true")
    p.add_argument("--config", default="config.yaml")
    sub = p.add_subparsers(dest="command")

    r = sub.add_parser("repair", help="Repair a bug from an issue description")
    r.add_argument("--repo", required=True)
    r.add_argument("--issue-title", required=True)
    r.add_argument("--issue-body", default="")
    r.add_argument("--output", "-o")
    r.add_argument("--trajectory")
    r.add_argument("--candidates", type=int, default=3)
    r.add_argument("--retries", type=int, default=3)

    a = sub.add_parser("analyze", help="Index and summarize a repository")
    a.add_argument("--repo", required=True)
    a.add_argument("--symbols", action="store_true")
    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    setup_logging(args.verbose)
    if args.command == "repair":
        sys.exit(asyncio.run(run_repair(args)))
    elif args.command == "analyze":
        sys.exit(asyncio.run(run_analyze(args)))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
