"""Forge dash CLI — project + ecosystem health boards WITHOUT an AI.

Commands:
  forge dash project [--journal PATH] [--corpus PATH] [--repo-root PATH] [--json]
       -> task-journal board (states, merged %, blocked-with-reason) + corpus
          coverage feed; emits Markdown (or JSON with --json)
  forge dash ecosystem --roots DIR [DIR ...] [--json]
       -> cross-repo board reading each repo's own CHANGELOG.md top release;
          repos without CHANGELOG/README are reported, not skipped

Exit codes: 0 ok, 1 refusal (corrupt/missing journal or corpus), 2 usage/config.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from .corpus import REPO_ROOT
from .dash import DashRefusal, ecosystem_board, project_board
from .task import StatusRefusal


def _print(board: dict, as_json: bool, md: str) -> None:
    if as_json:
        print(json.dumps(board, indent=2, sort_keys=True))
    else:
        print(md, end="")


def cmd_project(args: argparse.Namespace) -> int:
    journal = args.journal or os.environ.get("FORGE_JOURNAL",
                                             os.path.expanduser("~/.forge/tasks.jsonl"))
    try:
        board = project_board(journal_path=journal, corpus_path=args.corpus,
                              repo_root=args.repo_root)
    except (OSError, ValueError, StatusRefusal, DashRefusal) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 1
    from .dash import _md_project
    _print(board, args.json, _md_project(board))
    return 0


def cmd_ecosystem(args: argparse.Namespace) -> int:
    if not args.roots:
        print("REFUSED: --roots requires at least one repo checkout", file=sys.stderr)
        return 2
    try:
        board = ecosystem_board(args.roots)
    except (OSError, DashRefusal) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 1
    from .dash import _md_ecosystem
    _print(board, args.json, _md_ecosystem(board))
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="forge dash", description="Forge project + ecosystem boards")
    sub = p.add_subparsers(dest="command", required=True)

    pj = sub.add_parser("project", help="task journal + corpus board")
    pj.add_argument("--journal", help="path to tasks.jsonl (default FORGE_JOURNAL or ~/.forge)")
    pj.add_argument("--corpus", default=os.path.join(REPO_ROOT, "docs/corpus/builder-corpus.json"),
                    help="builder corpus path")
    pj.add_argument("--repo-root", help="repo checkout for citation proof-read (optional)")
    pj.add_argument("--json", action="store_true")
    pj.set_defaults(func=cmd_project)

    ec = sub.add_parser("ecosystem", help="cross-repo board from each repo's CHANGELOG")
    ec.add_argument("--roots", nargs="+", required=True, help="repo checkout dirs")
    ec.add_argument("--json", action="store_true")
    ec.set_defaults(func=cmd_ecosystem)

    args = p.parse_args(argv)
    return args.func(args)


def cli_main(argv: list[str] | None = None) -> int:
    """Entry point used from __main__ dispatch with the leading 'dash' consumed."""
    return main(argv)


if __name__ == "__main__":
    sys.exit(main())