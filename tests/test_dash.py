"""Tests for the Forge dashboards (forge/dash.py + forge/dash_cli.py).

Exercises the boards at the real boundary: real temp journals + real repo
checkouts, plus the CLI dispatch as a real subprocess. Fail-closed: corrupt
journal / missing roots / repo-without-CHANGELOG are all asserted.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

from forge import __version__
from forge.dash import DashRefusal, _md_ecosystem, _md_project, ecosystem_board, project_board
from forge.engine import engine
from forge.journal import Journal
from forge.task import Status, StatusRefusal, Task, TaskInput

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _task(journal_path: str, title: str, repo: str = "Daftari") -> Task:
    j = Journal(journal_path)
    task = Task.new(TaskInput(
        repo=repo,
        title=title,
        file_scope=[],
        acceptance_criteria=["works"],
    ), created_by="test")
    j.append(task)
    return task


def _to_merged(journal_path: str, task: Task) -> None:
    j = Journal(journal_path)
    for status, via in ((Status.RETRIEVING, "builder"), (Status.BUILDING, "builder"),
                        (Status.REVIEWING, "reviewer")):
        engine(task, status, via)
    engine(task, Status.MERGED, "reviewer", note="review ok")
    j.append(task)


def _to_blocked(journal_path: str, task: Task) -> None:
    j = Journal(journal_path)
    engine(task, Status.RETRIEVING, "builder")
    engine(task, Status.BLOCKED, "builder", note="scope not clear")
    j.append(task)


class ProjectBoardTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.mkdtemp(prefix="forge-dash-", dir="/tmp")
        self.addCleanup(lambda: __import__("shutil").rmtree(self._tmp, ignore_errors=True))
        self.journal = os.path.join(self._tmp, "tasks.jsonl")

    def test_aggregates_states_and_merged_pct(self) -> None:
        t1 = _task(self.journal, "merge me")
        _to_merged(self.journal, t1)
        t2 = _task(self.journal, "block me")
        _to_blocked(self.journal, t2)
        _task(self.journal, "still queued")
        board = project_board(self.journal)
        self.assertEqual(3, board["tasks"]["total"])
        self.assertEqual(1, board["tasks"]["merged"])
        self.assertAlmostEqual(33.3, board["tasks"]["merged_pct"], places=1)
        self.assertEqual([t2.task_id], board["tasks"]["blocked"])
        self.assertEqual("scope not clear", board["tasks"]["blockeds_with_reason"][0]["reason"])
        out = _md_project(board)
        self.assertIn("Forge Project Board", out)
        self.assertIn("scope not clear", out)

    def test_corrupt_journal_refuses(self) -> None:
        with open(self.journal, "w") as fh:
            fh.write("{not-json\n")
        with self.assertRaises(DashRefusal):
            project_board(self.journal)

    def test_malformed_corpus_refuses(self) -> None:
        _task(self.journal, "any")
        corpus = os.path.join(self._tmp, "bad.json")
        with open(corpus, "w") as fh:
            fh.write("[1, 2, 3]")  # not the corpus schema
        with self.assertRaises(DashRefusal):
            project_board(self.journal, corpus_path=corpus)


class EcosystemBoardTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.mkdtemp(prefix="forge-eco-", dir="/tmp")
        self.addCleanup(lambda: __import__("shutil").rmtree(self._tmp, ignore_errors=True))
        self.good = os.path.join(self._tmp, "goodrepo")
        self.naked = os.path.join(self._tmp, "nakedrepo")
        os.makedirs(self.good)
        os.makedirs(self.naked)
        with open(os.path.join(self.good, "CHANGELOG.md"), "w") as fh:
            fh.write("# C\n\n## [3.2.1] — 2026-09-07 — v\n\n### Added\n\n- x\n\n#### detail\n")
        with open(os.path.join(self.good, "README.md"), "w") as fh:
            fh.write("# goodrepo\n")

    def test_reads_own_changelog_head(self) -> None:
        board = ecosystem_board([self.good])
        repo = board["repos"][0]
        self.assertTrue(repo["has_changelog"])
        self.assertEqual("3.2.1", repo["version"])
        self.assertEqual("Added", repo["top_release_sections"])
        self.assertEqual([], repo["problems"])
        out = _md_ecosystem(board)
        self.assertIn("goodrepo", out)
        self.assertIn("3.2.1", out)

    def test_flags_repo_without_own_changelog(self) -> None:
        board = ecosystem_board([self.naked])
        repo = board["repos"][0]
        self.assertFalse(repo["has_changelog"])
        self.assertTrue(any("missing CHANGELOG" in p for p in repo["problems"]))
        out = _md_ecosystem(board)
        self.assertIn("missing CHANGELOG", out)

    def test_real_forge_checkout_signed_head(self) -> None:
        board = ecosystem_board([REPO])
        repo = board["repos"][0]
        self.assertTrue(repo["has_changelog"])
        self.assertRegex(repo["head"], r"^[0-9a-f]{7,}$")
        self.assertEqual("G", repo["signed"])


class CliSubprocessTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.mkdtemp(prefix="forge-dash-cli-", dir="/tmp")
        self.addCleanup(lambda: __import__("shutil").rmtree(self._tmp, ignore_errors=True))
        self.journal = os.path.join(self._tmp, "tasks.jsonl")
        t = _task(self.journal, "cli seed")
        _to_merged(self.journal, t)

    def _run(self, *argv: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "-m", "forge", "dash", *argv],
            capture_output=True, text=True, timeout=120,
            cwd=REPO,
        )

    def test_project_cli_emits_md(self) -> None:
        r = self._run("project", "--journal", self.journal)
        self.assertEqual(0, r.returncode, r.stderr)
        self.assertIn("Forge Project Board", r.stdout)
        self.assertIn("1", r.stdout)  # merged count row

    def test_project_cli_json(self) -> None:
        r = self._run("project", "--journal", self.journal, "--json")
        self.assertEqual(0, r.returncode, r.stderr)
        board = json.loads(r.stdout)
        self.assertEqual("project", board["type"])
        self.assertEqual(1, board["tasks"]["merged"])

    def test_project_cli_refuses_corrupt_journal(self) -> None:
        with open(self.journal, "w") as fh:
            fh.write("garbage\n")
        r = self._run("project", "--journal", self.journal)
        self.assertEqual(1, r.returncode)
        self.assertIn("REFUSED", r.stderr)

    def test_ecosystem_cli_missing_roots_is_usage_error(self) -> None:
        r = self._run("ecosystem")
        self.assertEqual(2, r.returncode)
        self.assertIn("--roots", r.stderr)

    def test_ecosystem_cli_real_repo(self) -> None:
        r = self._run("ecosystem", "--roots", REPO)
        self.assertEqual(0, r.returncode, r.stderr)
        self.assertIn("Forge Ecosystem Board", r.stdout)
        self.assertIn("forge" if os.path.basename(REPO) else "ecosystem", r.stdout)
        self.assertTrue(r.stdout.rstrip().endswith("|"))

    def test_version_is_030(self) -> None:
        self.assertGreaterEqual(tuple(int(x) for x in __version__.split(".")), (0, 3, 0))


if __name__ == "__main__":
    unittest.main()