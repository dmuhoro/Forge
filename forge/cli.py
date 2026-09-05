"""Forge CLI — drive tasks WITHOUT an AI: an operator (owner or a future agent host)
moves a task through the deterministic engine. The journal is the single source of truth.

Commands:
  forge-task new          --repo R --title T [--prd X] [--arch Y] [--scope a,b] [--accept "c1| c2"]
  forge-task to ID STATUS [--via ROLE] [--note TEXT]
  forge-task show ID
  forge-task list [--repo R] [--status S]
  forge-task verify                       (journal parses + hydrates)
"""

from __future__ import annotations

import argparse
import os
import sys

from .engine import engine, valid_from
from .journal import Journal
from .task import Status, StatusRefusal, Task, TaskInput


def default_journal() -> str:
    return os.environ.get("FORGE_JOURNAL", os.path.expanduser("~/.forge/tasks.jsonl"))


def _journal() -> Journal:
    path = default_journal()
    if not os.path.isdir(os.path.dirname(path) or "."):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    return Journal(path)


def _maybe_hydrate_verbose(journal: Journal, task_id: str) -> Task:
    task = journal.latest(task_id)
    if task is None:
        raise StatusRefusal(f"task not found: {task_id}")
    return task


def cmd_new(args) -> int:
    j = _journal()
    task = Task.new(TaskInput(
        repo=args.repo,
        title=args.title,
        prd_ref=args.prd,
        architecture_ref=args.arch,
        file_scope=[s for s in (args.scope or "").split(",") if s],
        acceptance_criteria=[s for s in (args.accept or "").split(";") if s],
        review_checklist_ref=args.checklist,
    ), created_by=args.by)
    j.append(task)
    print(f"queued {task.task_id} [{task.repo}] {task.title}")
    print(f"  journal: {default_journal()}")
    return 0


def cmd_to(args) -> int:
    j = _journal()
    task = _maybe_hydrate_verbose(j, args.task_id)
    try:
        to = Status(args.status)
    except ValueError:
        print(f"REFUSED: unknown status {args.status}", file=sys.stderr)
        return 2
    try:
        engine(task, to, via=args.via or "operator", note=args.note or "")
    except StatusRefusal as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    j.append(task)
    print(f"{args.task_id}: {task.status.value} (attempts {task.attempts}/{task.max_attempts})")
    if to is Status.BLOCKED:
        print(f"  blocked_reason: {task.blocked_reason}")
    return 0


def cmd_show(args) -> int:
    j = _journal()
    task = _maybe_hydrate_verbose(j, args.task_id)
    print(f"{task.task_id} [{task.repo}] status={task.status.value} attempts={task.attempts}/{task.max_attempts}")
    print(f"  {task.title}")
    if task.blocked_reason:
        print(f"  blocked: {task.blocked_reason}")
    for e in task.events:
        print(f"  {e['t']} {e['from']} -> {e['to']} via {e['via']}" + (f" - {e['note']}" if e["note"] else ""))
    return 0


def cmd_list(args) -> int:
    j = _journal()
    latest: dict[str, Task] = {}
    for task in j.read():
        latest[task.task_id] = task  # journal is chronological; last wins
    tasks = list(latest.values())
    if args.repo:
        tasks = [t for t in tasks if t.repo == args.repo]
    if args.status:
        tasks = [t for t in tasks if t.status.value == args.status]
    if not tasks:
        print("no tasks")
        return 0
    for t in tasks:
        marker = " " if t.status.value in (Status.MERGED.value, Status.BLOCKED.value) else "*"
        print(f"{marker} {t.task_id} {t.status.value:<17} {t.repo:<12} {t.title}")
    return 0


def cmd_verify(args) -> int:
    j = _journal()
    try:
        info = j.verify()
    except StatusRefusal as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 1
    print(f"journal ok: {info['lines']} task(s), all lines parses + hydrates")
    return 0


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="forge-task", description="Forge orchestrator task CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("new", help="create a queued task")
    p.add_argument("--repo", required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--prd")
    p.add_argument("--arch")
    p.add_argument("--scope")
    p.add_argument("--accept")
    p.add_argument("--checklist")
    p.add_argument("--by", default="owner")
    p.set_defaults(func=cmd_new)

    p = sub.add_parser("to", help="apply a transition")
    p.add_argument("task_id")
    p.add_argument("status")
    p.add_argument("--via", default="operator")
    p.add_argument("--note")
    p.set_defaults(func=cmd_to)

    p = sub.add_parser("show", help="full lifecycle of a task")
    p.add_argument("task_id")
    p.set_defaults(func=cmd_show)

    p = sub.add_parser("list", help="list tasks")
    p.add_argument("--repo")
    p.add_argument("--status")
    p.set_defaults(func=cmd_list)

    sub.add_parser("verify", help="journal integrity self-proof").set_defaults(func=cmd_verify)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except StatusRefusal as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2


def main() -> None:
    sys.exit(run())


if __name__ == "__main__":
    main()