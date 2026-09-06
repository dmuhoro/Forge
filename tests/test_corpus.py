"""Forge Builder corpus tests — real production path, not mocks.

Exercises: the REAL corpus file (docs/corpus/builder-corpus.json), the schema
validator (fail-closed), the deterministic matcher (fail-closed on no match),
citation verification against a real checkout-shaped tree, and the `forge
corpus` CLI across the real subprocess boundary.
"""

import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from forge import (
    REPO_ROOT,
    CorpusRefusal,
    load,
    match,
    validate,
    verify_citations,
)

REAL_CORPUS = REPO_ROOT / "docs" / "corpus" / "builder-corpus.json"


def _entry(overrides=None) -> dict:
    entry = {
        "id": "P-99",
        "name": "probe pattern",
        "trigger": "keyword one, keyword two",
        "source": "some commit",
        "boundary": ["src/example.ts:10"],
        "recipe": ["step one", "step two"],
        "acceptance": ["it works"],
        "guardrail": "fail closed",
    }
    if overrides:
        entry.update(overrides)
    return entry


def _valid_corpus() -> list[dict]:
    return [_entry(), _entry({"id": "P-98", "name": "second pattern"})]


class CorpusLoadTest(unittest.TestCase):
    def test_real_corpus_loads_with_valid_schema(self) -> None:
        patterns = load(str(REAL_CORPUS))
        self.assertEqual(10, len(patterns))
        self.assertEqual([], validate(patterns))

    def test_missing_file_refused(self) -> None:
        missing = os.path.join(tempfile.mkdtemp(), "nope.json")
        with self.assertRaises(CorpusRefusal) as ctx:
            load(missing)
        self.assertIn("not found", str(ctx.exception))

    def test_invalid_json_refused(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
            fh.write("{not json")
            path = fh.name
        try:
            with self.assertRaises(CorpusRefusal) as ctx:
                load(path)
            self.assertIn("not valid json", str(ctx.exception))
        finally:
            os.unlink(path)

    def test_duplicate_id_refused(self) -> None:
        bad = [_entry(), _entry({"id": "P-99"})]
        errors = validate(bad)
        self.assertTrue(any("duplicate id" in e for e in errors))

    def test_empty_recipe_refused(self) -> None:
        errors = validate([_entry({"recipe": []})])
        self.assertTrue(any("recipe" in e for e in errors))

    def test_non_citation_boundary_refused(self) -> None:
        errors = validate([_entry({"boundary": ["src/no_description.guess"]})])
        self.assertTrue(any("boundary" in e for e in errors))

    def test_missing_guardrail_refused(self) -> None:
        entry = _entry()
        del entry["guardrail"]
        errors = validate([entry])
        self.assertTrue(any("guardrail" in e for e in errors))


class CorpusMatchTest(unittest.TestCase):
    def setUp(self) -> None:
        self.patterns = load(str(REAL_CORPUS))

    def test_empty_keywords_fail_closed(self) -> None:
        self.assertEqual([], match(self.patterns, ""))
        self.assertEqual([], match(self.patterns, "   "))

    def test_no_overlap_fail_closed_no_guess(self) -> None:
        self.assertEqual([], match(self.patterns, "zzzqqq unique nonce"))

    def test_orphan_keyword_ranks_adopt_first(self) -> None:
        results = match(self.patterns, "adopt orphaned records user_id")
        self.assertTrue(results)
        self.assertEqual("P-01", results[0]["id"])

    def test_realtime_keyword_ranks_realtime_patterns(self) -> None:
        results = match(self.patterns, "realtime postgres_changes delivery")
        self.assertTrue(results)
        self.assertEqual("P-03", results[0]["id"])

    def test_telemetry_consent_ranks_fail_closed_telemetry(self) -> None:
        results = match(self.patterns, "telemetry consent share usage stats")
        self.assertTrue(results)
        self.assertEqual("P-06", results[0]["id"])

    def test_result_is_deterministic_and_capped(self) -> None:
        a = match(self.patterns, "sync live session realtime delivery", top=3)
        b = match(self.patterns, "sync live session realtime delivery", top=3)
        self.assertEqual(a, b)
        self.assertLessEqual(len(a), 3)

    def test_results_carry_boundary_and_guardrail(self) -> None:
        results = match(self.patterns, "orphan adoption")
        self.assertEqual("src/features/sync/adoptOrphans.ts:32", results[0]["boundary"][0])
        self.assertIn("Fail closed", results[0]["guardrail"])


class CorpusCitationTest(unittest.TestCase):
    def test_all_ok_when_every_file_line_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / "src").mkdir(parents=True)
            (root / "src" / "example.ts").write_text("\n".join(f"line {i}" for i in range(1, 13)), encoding="utf-8")
            problems = verify_citations([_entry()], root)
            self.assertEqual([], problems)

    def test_missing_file_reported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            problems = verify_citations([_entry()], tmp)
            self.assertEqual(1, len(problems))
            self.assertIn("file not found", problems[0]["error"])

    def test_line_beyond_eof_reported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / "src").mkdir(parents=True)
            (root / "src" / "example.ts").write_text("a\n", encoding="utf-8")
            problems = verify_citations([_entry()], root)
            self.assertEqual(1, len(problems))
            self.assertIn("exceeds", problems[0]["error"])


class CorpusCliContractTest(unittest.TestCase):
    def test_real_corpus_verify_ok(self) -> None:
        r = subprocess.run(
            [sys.executable, "-m", "forge", "corpus", "verify"],
            capture_output=True, text=True)
        self.assertEqual(0, r.returncode, r.stderr)
        self.assertIn("corpus ok: 10 patterns", r.stdout)

    def test_match_through_the_real_boundary(self) -> None:
        r = subprocess.run(
            [sys.executable, "-m", "forge", "corpus", "match", "adopt", "orphaned", "records"],
            capture_output=True, text=True)
        self.assertEqual(0, r.returncode, r.stderr)
        self.assertIn("P-01", r.stdout)
        self.assertIn("boundary: src/features/sync/adoptOrphans.ts:32", r.stdout)

    def test_verify_fails_on_bad_reference_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            r = subprocess.run(
                [sys.executable, "-m", "forge", "corpus", "verify", "--repo-root", tmp],
                capture_output=True, text=True)
            self.assertEqual(1, r.returncode)
            self.assertIn("references: FAIL", r.stderr)

    def test_task_cli_still_dispatchs_under_corpus_main(self) -> None:
        env = dict(os.environ, FORGE_JOURNAL=tempfile.mktemp(suffix=".jsonl"))
        r = subprocess.run(
            [sys.executable, "-m", "forge", "new", "--repo", "Daftari", "--title", "t"],
            capture_output=True, text=True, env=env)
        self.assertEqual(0, r.returncode, r.stderr)
        self.assertIn("queued", r.stdout)


if __name__ == "__main__":
    unittest.main()