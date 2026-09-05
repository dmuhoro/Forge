"""Append-only JSONL journal for task lifecycle events.

Design mirrors the DataBank vault journal: every transition is a line appended
under an os-level append write; nothing is ever rewritten in place. Reopening an
old journal replays events; a corrupt line is a *fail-closed refusal*, never a
silent skip — the operator must see the damaged file, exactly like the vault.
"""

from __future__ import annotations

import json
import os

from .task import Status, StatusRefusal, Task


class Journal:
    def __init__(self, path: str) -> None:
        self._path = path
        os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)

    def append(self, task: Task) -> None:
        """Persist the full task state as one append-only JSON line."""
        line = json.dumps({
            "task_id": task.task_id,
            "repo": task.repo,
            "title": task.title,
            "status": task.status.value,
            "created_by": task.created_by,
            "attempts": task.attempts,
            "max_attempts": task.max_attempts,
            "prd_ref": task.prd_ref,
            "architecture_ref": task.architecture_ref,
            "file_scope": task.file_scope,
            "acceptance_criteria": task.acceptance_criteria,
            "review_checklist_ref": task.review_checklist_ref,
            "review_result": task.review_result,
            "merged_at": task.merged_at,
            "blocked_at": task.blocked_at,
            "blocked_reason": task.blocked_reason,
            "events": task.events,
        }, ensure_ascii=False)
        with open(self._path, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
            fh.flush()
            os.fsync(fh.fileno())

    def read(self) -> list[Task]:
        """Replay all tasks. A missing file = empty journal; a corrupt line = refusal."""
        if not os.path.exists(self._path):
            return []
        tasks: list[Task] = []
        with open(self._path, "r", encoding="utf-8") as fh:
            for line_no, line in enumerate(fh, start=1):
                text = line.strip()
                if not text:
                    continue
                try:
                    data = json.loads(text)
                    task = Task.hydrate(data)
                except (ValueError, KeyError, TypeError) as exc:
                    raise StatusRefusal(
                        f"corrupt-journal line {line_no}: {exc}"
                    ) from exc
                tasks.append(task)
        return tasks

    def latest(self, task_id: str) -> Task | None:
        for task in reversed(self.read()):
            if task.task_id == task_id:
                return task
        return None

    def verify(self) -> dict:
        """Self-proof: every line parses and hydrates; nothing silently dropped."""
        tasks = self.read()
        return {"lines": len(tasks), "tasks": len(tasks), "ok": True}

    def __len__(self) -> int:
        return len(self.read())