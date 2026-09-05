"""Deterministic task state machine (brief §9 step 1, zero AI).

Rules (enforced at the real boundary, fail-closed):
  - every transition must be in the allowed table;
  - a terminal task (MERGED/BLOCKED) never resurrects;
  - reaching BUILDING always passes through REVIEWING→CHANGES_REQUESTED (attempts++);
  - BLOCKED is a route, not a drop: a reason is mandatory and the record is retained;
  - MERGED can only be reached from REVIEWING with a recorded review result.

The engine itself is pure (no storage); the Journal persists every event append-only.
"""

from __future__ import annotations

import time

from .task import Status, StatusRefusal, Task

def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def allowed_transitions() -> dict[Status, set[Status]]:
    return {
        Status.QUEUED: {Status.RETRIEVING},
        Status.RETRIEVING: {Status.BUILDING, Status.BLOCKED},
        Status.BUILDING: {Status.REVIEWING, Status.BLOCKED},
        Status.REVIEWING: {Status.MERGED, Status.CHANGES_REQUESTED, Status.BLOCKED},
        Status.CHANGES_REQUESTED: {Status.BUILDING, Status.BLOCKED},
        Status.MERGED: set(),
        Status.BLOCKED: set(),
    }


def valid_from(state: Status) -> set[Status]:
    """Forward edges for a given status (used by CLI completions / docs)."""
    return set(allowed_transitions()[state])


def engine(task: Task, to: Status, via: str, note: str = "") -> Task:
    """Apply a transition. Raises StatusRefusal (explicit reason) on any illegal move."""
    _assert_legal(task, to)
    if to is Status.BLOCKED and not note.strip():
        raise StatusRefusal(f"blocked requires an explicit reason (id={task.task_id})")
    if to is Status.MERGED and not (task.review_result or note.strip()):
        raise StatusRefusal(f"merged requires a recorded review result (id={task.task_id})")
    if to is Status.CHANGES_REQUESTED:
        if not note.strip():
            raise StatusRefusal(f"changes_requested requires a change note (id={task.task_id})")
    if to is Status.BUILDING and task.attempts >= task.max_attempts:
        raise StatusRefusal(
            f"attempts exhausted ({task.attempts}/{task.max_attempts}); task must route to BLOCKED "
            f"(id={task.task_id})"
        )

    previous = task.status
    task.status = to
    if to is Status.CHANGES_REQUESTED:
        task.attempts += 1
    if to is Status.MERGED:
        task.merged_at = _now()
        if note.strip():
            task.review_result = note.strip()
    if to is Status.BLOCKED:
        task.blocked_reason = note.strip() or task.blocked_reason
        task.blocked_at = _now()
    task.add_event(previous, via, note)
    return task


def _assert_legal(task: Task, to: Status) -> None:
    if task.status in (Status.MERGED, Status.BLOCKED):
        raise StatusRefusal(
            f"terminal state {task.status.value} cannot resurrect to {to.value} (id={task.task_id})"
        )
    if to not in allowed_transitions()[task.status]:
        raise StatusRefusal(
            f"illegal transition {task.status.value}->{to.value} (id={task.task_id})"
        )
    if to is not Status.BLOCKED and task.blocked_reason:
        raise StatusRefusal(
            f"blocked task cannot continue without explicit unblock (id={task.task_id})"
        )