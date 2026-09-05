"""Forge engine + journal contract tests — real production path, not mocks."""

import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from forge import Journal, MAX_ATTEMPTS, Status, StatusRefusal, Task, TaskInput, engine


def _task() -> Task:
    return Task.new(TaskInput(
        repo="Daftari",
        title="make the PWA installable",
        prd_ref="docs/prd/offline-first.md",
        architecture_ref="docs/architecture/pwa.md",
        file_scope=["src/lib/", "vite.config.ts"],
        acceptance_criteria=["manifest has PNG icons", "beforeinstallprompt fires"],
        review_checklist_ref="docs/operations/review-checklist.md",
    ))


class EngineContractTest(unittest.TestCase):
    def test_happy_path_reaches_merged_with_review_result(self) -> None:
        t = _task()
        engine(t, Status.RETRIEVING, via="planner")
        engine(t, Status.BUILDING, via="builder")
        engine(t, Status.REVIEWING, via="builder")
        engine(t, Status.MERGED, via="reviewer", note="all criteria met")
        self.assertEqual(Status.MERGED, t.status)
        self.assertIsNotNone(t.merged_at)
        self.assertEqual("all criteria met", t.review_result)

    def test_changes_requested_loops_back_building_and_counts_once(self) -> None:
        t = _task()
        engine(t, Status.RETRIEVING, via="planner")
        engine(t, Status.BUILDING, via="builder")
        engine(t, Status.REVIEWING, via="builder")
        engine(t, Status.CHANGES_REQUESTED, via="reviewer", note="uses a dup dependency")
        self.assertEqual(1, t.attempts)
        engine(t, Status.BUILDING, via="builder")
        engine(t, Status.REVIEWING, via="builder")
        engine(t, Status.MERGED, via="reviewer", note="gap fixed")
        self.assertEqual(Status.MERGED, t.status)
        self.assertEqual(1, t.attempts)

    def test_attempts_cap_forces_blocked_not_more_building(self) -> None:
        t = _task()
        engine(t, Status.RETRIEVING, via="planner")
        for _ in range(MAX_ATTEMPTS):
            engine(t, Status.BUILDING, via="builder")
            engine(t, Status.REVIEWING, via="builder")
            engine(t, Status.CHANGES_REQUESTED, via="reviewer", note="still wrong")
        self.assertEqual(MAX_ATTEMPTS, t.attempts)
        with self.assertRaises(StatusRefusal) as ctx:
            engine(t, Status.BUILDING, via="builder")
        self.assertIn("exhausted", str(ctx.exception))
        engine(t, Status.BLOCKED, via="owner", note="escalate to the owner")
        self.assertEqual(Status.BLOCKED, t.status)
        self.assertIsNotNone(t.blocked_at)
        self.assertIn("escalate", t.blocked_reason)

    def test_merged_never_resurrects(self) -> None:
        t = _task()
        for s in (Status.RETRIEVING, Status.BUILDING, Status.REVIEWING):
            engine(t, s, via="x")
        engine(t, Status.MERGED, via="reviewer", note="done")
        for s in (Status.BUILDING, Status.REVIEWING, Status.BLOCKED):
            with self.assertRaises(StatusRefusal) as ctx:
                engine(t, s, via="x", note="revive")
            self.assertIn("resurrect", str(ctx.exception))

    def test_blocked_never_resurrects(self) -> None:
        t = _task()
        engine(t, Status.RETRIEVING, via="planner")
        engine(t, Status.BLOCKED, via="owner", note="missing hardware")
        with self.assertRaises(StatusRefusal):
            engine(t, Status.RETRIEVING, via="planner")

    def test_blocked_requires_explicit_reason(self) -> None:
        t = _task()
        engine(t, Status.RETRIEVING, via="planner")
        with self.assertRaises(StatusRefusal) as ctx:
            engine(t, Status.BLOCKED, via="owner")
        self.assertIn("reason", str(ctx.exception))

    def test_merged_requires_review_result(self) -> None:
        t = _task()
        for s in (Status.RETRIEVING, Status.BUILDING, Status.REVIEWING):
            engine(t, s, via="x")
        with self.assertRaises(StatusRefusal) as ctx:
            engine(t, Status.MERGED, via="reviewer")
        self.assertIn("review result", str(ctx.exception))

    def test_illegal_jump_is_refused(self) -> None:
        t = _task()
        with self.assertRaises(StatusRefusal) as ctx:
            engine(t, Status.MERGED, via="builder")
        self.assertIn("illegal transition", str(ctx.exception))

    def test_unknown_status_refused(self) -> None:
        # enum parse fails fail-closed *before* the engine can act on it; the CLI
        # boundary catches this and exits 2 with REFUSED (see CliContractTest).
        with self.assertRaises(ValueError):
            Status("no_such_state")


class JournalContractTest(unittest.TestCase):
    def test_round_trip_preserves_full_lifecycle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "tasks.jsonl")
            j = Journal(path)
            t = _task()
            engine(t, Status.RETRIEVING, via="planner")
            engine(t, Status.BUILDING, via="builder")
            engine(t, Status.REVIEWING, via="builder")
            engine(t, Status.MERGED, via="reviewer", note="all criteria met")
            j.append(t)
            out = j.read()
            self.assertEqual(1, len(out))
            self.assertEqual(Status.MERGED, t.status)
            self.assertEqual(t.status, out[0].status)
            self.assertEqual(len(t.events), len(out[0].events))
            self.assertEqual(2, len(t.acceptance_criteria))
            self.assertEqual(0, out[0].attempts)

    def test_each_transition_appends_not_rewrites(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "tasks.jsonl")
            j = Journal(path)
            t = _task()
            for s, via in ((Status.RETRIEVING, "planner"), (Status.BUILDING, "builder")):
                engine(t, s, via=via)
                j.append(t)
            lines = [l for l in open(path, encoding="utf-8").read().splitlines() if l]
            self.assertEqual(2, len(lines))
            self.assertEqual(Status.BUILDING, j.latest(t.task_id).status)

    def test_corrupt_line_refused_not_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "tasks.jsonl")
            j = Journal(path)
            t = _task()
            j.append(t)
            with open(path, "a", encoding="utf-8") as fh:
                fh.write("{\n")
            with self.assertRaises(StatusRefusal) as ctx:
                j.read()
            self.assertIn("corrupt-journal", str(ctx.exception))

    def test_missing_journal_is_empty_not_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            j = Journal(os.path.join(tmp, "nope.jsonl"))
            self.assertEqual([], j.read())
            self.assertEqual(0, len(j))

    def test_unknown_task_latest_is_none(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            j = Journal(os.path.join(tmp, "t.jsonl"))
            self.assertIsNone(j.latest("missing"))


class CliContractTest(unittest.TestCase):
    def test_cli_lifecycle_through_the_real_boundary(self) -> None:
        env = dict(os.environ, FORGE_JOURNAL=tempfile.mktemp(suffix=".jsonl"))
        new = subprocess.run(
            [sys.executable, "-m", "forge", "new", "--repo", "Daftari",
             "--title", "pwa off skinned", "--accept", "a|b"],
            capture_output=True, text=True, env=env)
        self.assertEqual(0, new.returncode, new.stderr)
        task_id = new.stdout.strip().split()[1]
        for status, note in (("retrieving", ""), ("building", ""), ("reviewing", ""),
                             ("merged", "criteria met")):
            r = subprocess.run(
                [sys.executable, "-m", "forge", "to", task_id, status, "--via", "agent", "--note", note],
                capture_output=True, text=True, env=env)
            self.assertEqual(0, r.returncode, r.stderr)
            self.assertIn(status, r.stdout)
        verify = subprocess.run([sys.executable, "-m", "forge", "verify"],
                                capture_output=True, text=True, env=env)
        self.assertEqual(0, verify.returncode, verify.stderr)
        self.assertIn("journal ok", verify.stdout)

    def test_cli_refusal_exits_2_and_names_reason(self) -> None:
        env = dict(os.environ, FORGE_JOURNAL=tempfile.mktemp(suffix=".jsonl"))
        new = subprocess.run(
            [sys.executable, "-m", "forge", "new", "--repo", "X", "--title", "t"],
            capture_output=True, text=True, env=env)
        task_id = new.stdout.strip().split()[1]
        bad = subprocess.run(
            [sys.executable, "-m", "forge", "to", task_id, "merged", "--via", "agent"],
            capture_output=True, text=True, env=env)
        self.assertEqual(2, bad.returncode)
        self.assertIn("REFUSED", bad.stderr)


if __name__ == "__main__":
    unittest.main()