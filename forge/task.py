"""Task schema for the orchestrator (brief §2 — stdin, deterministic, no AI).

A Task is a fail-closed unit of work: it *never* leaves a transition ambiguous and a
terminal state never resurrects. Mirrors ShrinkMedia ADR-014 ``ForgeTask`` semantics.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import time
import uuid

MAX_ATTEMPTS = 3


class Status(str, Enum):
    QUEUED = "queued"
    RETRIEVING = "retrieving"
    BUILDING = "building"
    REVIEWING = "reviewing"
    CHANGES_REQUESTED = "changes_requested"
    MERGED = "merged"
    BLOCKED = "blocked"

    def __str__(self) -> str:
        return self.value


class StatusRefusal(Exception):
    """A fail-closed refusal with an explicit reason. Never a silent drop."""


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def new_id() -> str:
    return uuid.uuid4().hex[:16]


@dataclass(frozen=True)
class TaskInput:
    """The owner/agent shape of a task before it enters the journal."""

    repo: str
    title: str
    prd_ref: str | None = None
    architecture_ref: str | None = None
    file_scope: list[str] = field(default_factory=list)
    acceptance_criteria: list[str] = field(default_factory=list)
    review_checklist_ref: str | None = None  # points at the SOP checklist, not a copy


@dataclass
class Task:
    """Live task record. ``events`` is the append-only history we persist."""

    task_id: str
    repo: str
    title: str
    status: Status
    created_by: str
    created_at: str
    attempts: int
    max_attempts: int
    prd_ref: str | None
    architecture_ref: str | None
    file_scope: list[str]
    acceptance_criteria: list[str]
    review_checklist_ref: str | None
    review_result: str | None = None  # free-text human note on the last review
    merged_at: str | None = None
    blocked_at: str | None = None
    blocked_reason: str | None = None
    events: list[dict] = field(default_factory=list)

    def refusal(self, reason: str) -> StatusRefusal:
        reason = f"{reason} (id={self.task_id})"
        self.add_event(self.status, "had a fail-closed refusal; state {state}".format(state=self.status), reason)
        return StatusRefusal(reason)

    def add_event(self, previous: Status, via: str, note: str = "") -> None:
        now = _now()
        self.events.append({
            "t": now,
            "from": previous.value,
            "to": self.status.value,
            "via": via,
            "note": note,
            "attempts": self.attempts,
        })

    @classmethod
    def new(cls, inp: TaskInput, created_by: str = "owner") -> "Task":
        t = cls(
            task_id=new_id(),
            repo=inp.repo,
            title=inp.title,
            status=Status.QUEUED,
            created_by=created_by,
            created_at=_now(),
            attempts=0,
            max_attempts=MAX_ATTEMPTS,
            prd_ref=inp.prd_ref,
            architecture_ref=inp.architecture_ref,
            file_scope=list(inp.file_scope),
            acceptance_criteria=list(inp.acceptance_criteria),
            review_checklist_ref=inp.review_checklist_ref,
        )
        t.add_event(Status.QUEUED, "created")
        return t

    @classmethod
    def hydrate(cls, data: dict) -> "Task":
        """Rebuild a live task from a journal event without trusting the state field."""
        created = [e for e in data["events"] if e.get("via") == "created"]
        if not created:
            raise StatusRefusal("journal-first-line-must-be-created")
        first = created[0]
        t = cls(
            task_id=data["task_id"],
            repo=data["repo"],
            title=data["title"],
            status=Status(data["status"]),
            created_by=data["created_by"],
            created_at=first["t"],
            attempts=data.get("attempts", 0),
            max_attempts=data.get("max_attempts", MAX_ATTEMPTS),
            prd_ref=data.get("prd_ref"),
            architecture_ref=data.get("architecture_ref"),
            file_scope=data.get("file_scope", []),
            acceptance_criteria=data.get("acceptance_criteria", []),
            review_checklist_ref=data.get("review_checklist_ref"),
            review_result=data.get("review_result"),
            merged_at=data.get("merged_at"),
            blocked_at=data.get("blocked_at"),
            blocked_reason=data.get("blocked_reason"),
            events=list(data["events"]),
        )
        return t