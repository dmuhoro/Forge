# Forge — Changelog

All notable changes to Forge are documented here, following
[Semantic Versioning](https://semver.org/). Sections: **Added**, **Changed**,
**Fixed**, **Removed**. The per-phase narrative lives in `docs/kickoff.md`;
proofs in `docs/evidence/`. The ecosystem's cross-repo record is a Citation at
ShrinkMedia `docs/sprint-cross-reference.md` (documentation doctrine AGENTS.md §15).

## [0.4.0] — 2026-09-08 — Step 3 (part 3): HTTP surface (browser access, L1)

### Added

- **`forge serve`** (`forge/serve.py`) — the two health boards over stdlib HTTP
  (`ThreadingHTTPServer`, no new dependencies). Routes: `/` landing, `/project`
  + `/ecosystem` (HTML), `/project.json` + `/ecosystem.json` (machine JSON),
  `/healthz` (liveness, open). Offline, deterministic, no AI.
- **Fail-closed by construction**: a server configured without `FORGE_TOKEN`
  (or `--token`) **refuses to start**; a `0.0.0.0`/`::` broadcast bind is
  refused (CLI binds loopback by default; a specific tailnet/interface address
  must be passed explicitly). Every content route demands `Authorization:
  Bearer <token>` compared with `hmac.compare_digest` (no timing oracle);
  responses carry `Cache-Control: no-store`. A board that refuses to build →
  HTTP 503 with the refusal text, never a guessed row.
- **HTML renderers** `_html_project` / `_html_ecosystem` (XSS-escaped) wrapping
  the existing boards; README-table equivalence to the Markdown/JSON faces.
- **16 new tests** (`tests/test_serve.py`): live `ThreadingHTTPServer` on an
  ephemeral socket asserting the real auth boundary (401 without/with wrong
  token, 200 with token, 404 unknown route, 503 on corrupt journal), plus the
  refuse-to-start construction rules via CLI subprocess; suite 49 → **65**.
- **Real-repo smoke proof** (CLI, tailnet-ready): `/ecosystem.json` over HTTP
  reported DataBank `8440958` G, Forge `6baf75a` G, ShrinkMedia `aaf9015` G.
  See `docs/evidence/2026-09-08_forge_http_surface.md`.

### Changed

- `forge/__version__` 0.3.0 → 0.4.0.
- `python -m forge serve` dispatched from `__main__` (alongside `corpus`, `dash`).

### Honest

- Bearer-token auth is the fail-closed seam for browser access; TLS sits in
  front at the tailnet/VPS boundary, not inside Forge (consistent with dvault).
- Explicitly **not** opened to `0.0.0.0` on purpose — no public ingress yet.

## [0.3.0] — 2026-09-07 — Step 3 (part 2): project + ecosystem dashboards

### Added

- **`forge dash project`** — task-journal board from the single source of truth
  (`FORGE_JOURNAL`/`~/.forge/tasks.jsonl`): counts by every state, merged %,
  **blocked-with-reason** (never resurrect; reason surfaced, not dropped), plus Builder corpus
  patterns + citation proof-read coverage when `--repo-root` is given. Deterministic, stdlib,
  no AI; corrupt journal or malformed corpus ⇒ `REFUSED` (fail-closed, no guessed rows).
- **`forge dash ecosystem --roots A B C`** — cross-repo board read from each repo's **own
  pristine `CHANGELOG.md`** (documentation doctrine): top release version + feature-section
  names, git HEAD (`%G?` signature), and a **missing-CHANGELOG/missing-README lane** (doctrine
  rule 5 — reported, never silently skipped).
- **`--json`** on both commands for machine consumption.
- **12 new tests** (`tests/test_dash.py`), incl. real subprocess boundary + real repo checkout
  (HEAD short-sha + signed `G`); suite 37 → **49**.

### Changed

- `forge/__version__` 0.2.0 → 0.3.0.
- `forge dash`/`forge corpus` dispatched from `python -m forge`.

### Honest

- No AI, no web UI: the boards are stdlib decision surfaces an operator reads; the dashboard
  remains local + offline (consistent with the ecosystem's decision-only layer). "Ecosystem
  dashboard" reads sibling repos only when given their local checkout paths — it is not a
  network service.

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