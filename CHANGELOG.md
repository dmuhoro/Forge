# Forge — Changelog

All notable changes to Forge are documented here, following
[Semantic Versioning](https://semver.org/). Sections: **Added**, **Changed**,
**Fixed**, **Removed**. The per-phase narrative lives in `docs/kickoff.md`;
proofs in `docs/evidence/`. The ecosystem's cross-repo record is a Citation at
ShrinkMedia `docs/sprint-cross-reference.md` (documentation doctrine AGENTS.md §15).

## [0.2.0] — 2026-09-06 — Step 2 (part 1): Builder corpus shipped

### Added

- **Builder corpus (`docs/corpus/builder-corpus.json`)** — 10 patterns (P-01…P-10) extracted from
  the VERIFIED Daftari sprint-24 production-readiness diffs (`dmuhoro/Daftari`, commits
  `4ea952c..36eaf82`). Every entry names a real `file:line` boundary; matching is deterministic,
  offline, stdlib-only.
- **`forge/corpus.py`** — schema-validating loader (`load`), `validate` (duplicate ids, empty
  recipe/acceptance/boundary, non-citation boundaries), deterministic keyword `match` with a tiny
  suffix stemmer (fail-closed: no overlap => no guess), `verify_citations` (file:line boundary
  proof against a real checkout).
- **`forge/corpus_cli.py` + `forge corpus` dispatch** — `python -m forge corpus match "…"`,
  `python -m forge corpus verify [--repo-root PATH]`; refusal exit codes 1/2 matching
  `forge-task` conventions. Task CLI unchanged.
- **21 new tests** (`tests/test_corpus.py`), incl. the real subprocess boundary; suite 16 → **37**.
- **Citation boundary proof**, see `docs/evidence/2026-09-06_step2_builder_corpus.md`.

### Changed

- `forge/__version__` 0.1.0 → 0.2.0.
- `README.md` / `docs/kickoff.md` status: step 2 started (Builder corpus shipped).

### Honest

- The Builder **executor + Docker sandbox** and the brief §9 step-2 exit ("5 clean diffs in a row
  without hand-holding") are NOT wired yet — a separate, gated phase.

## [0.1.0] — 2026-09-05 — Step 1 shipped + exit met

### Added

- **Step 1 (`forge/task.py`, `forge/engine.py`, `forge/journal.py`, `forge/cli.py`)** — task schema
  matching the owner build-brief §2; deterministic state machine
  `queued → … → merged / blocked` (terminal states never resurrect; `blocked` requires a reason;
  `merged` requires a recorded review result; attempts cap routes to the human); append-only,
  fsync'd, corrupt-refusing JSONL journal; `forge-task new|to|show|list|verify` CLI. Zero AI.
- **16 tests** (`tests/test_forge.py`) incl. the real CLI subprocess boundary.
- **Step 1 EXIT met (2026-09-05)** — 5 real Daftari v6.5.0 tasks hand-run through `forge-task`,
  all walked to `merged`, journal verified. Evidence `docs/evidence/2026-09-05_step1_exit_5_real_daftari_tasks.md`.

### Changed

- `docs/kickoff.md` (dependency justification + phasing + RSI alignment), owner build brief
  preserved (`docs/owner-build-brief-2026-09-05.md`), README phase tracking.

## [Unreleased] — 2026-09-05 scaffold (pre-0.1.0)

- `0d8b81a` docs: Forge scaffold (purpose, proven decision core, pillars, invariants, roadmap).
- `91b8ad0` README.md first pass.