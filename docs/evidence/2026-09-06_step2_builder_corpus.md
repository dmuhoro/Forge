# Forge Step 2 — Builder corpus + citation verification (2026-09-06)

## What shipped

The **feeding base for the Builder role** (build-brief step 2: "Wire in Builder"). Before the
Builder executor or the Docker sandbox exists, the corpus grounds the Builder's first pass:
patterns that already worked on the exact same class of problem, each one **extracted from the
verified Daftari sprint-24 production-readiness diffs** — not paraphrased knowledge.

- `docs/corpus/builder-corpus.json` — 10 patterns (P-01…P-10) extracted from Daftari commits
  `4ea952c..36eaf82` (A1 orphan adoption, B1 realtime live updates, B2 trust & privacy, live-probe
  tooling). Every pattern has: `id`, `name`, `trigger`, `source` (real commit), `boundary`
  (real `file:line` citations), `recipe`, `acceptance`, `guardrail`.
- `forge/corpus.py` — stdlib-only, deterministic:
  - `load()` — schema-validating loader; any malformed entry is a hard refusal, never a skip
    (fail-closed).
  - `validate()` — returns problems (duplicate ids, empty recipe/acceptance/boundary,
    non-citation boundary strings, missing guardrail).
  - `match()` — deterministic keyword ranker with a tiny fixed-suffix stemmer
    (`orphan/orphans/orphaned`, `adopt/adoption` collapse); **no usable overlap => no result,
    never a guess**.
  - `verify_citations()` — boundary proof: every `file:line` citation must exist in a real
    checkout at that exact line.
- `forge/corpus_cli.py` + dispatcher — `python -m forge corpus match "…"` and
  `python -m forge corpus verify [--repo-root PATH]`; refuse exit codes 1/2 matching `forge-task`
  conventions. The existing task CLI is untouched (`python -m forge new|to|show|list|verify`).

## Evidence

- **Suite: 37 tests, 0 failures** (`python3 -m unittest discover -s tests`). 21 new corpus tests
  incl. real subprocess boundary (`python -m forge corpus …`), fail-closed empties, deterministic
  ranking, citation problems reported.
- **Citation boundary proof (the real path):**
  `python3 -m forge corpus verify --repo-root /tmp/opencode/Daftari-check`
  → `references: ok — all 14 citations exist at their cited lines`
  against Daftari HEAD `36eaf8231c234a92124751c1a4770e9c980c3d4a`.
  The verifier caught one real error before ship: P-03 cited migration line 19, the file has 18
  lines; corrected to the actual ALTER at line 17, re-verified.
- **Matcher demo:** `forge corpus match "adopt orphaned records missed user_id"` → top hit P-01
  `adopt-before-load` citing `src/features/sync/adoptOrphans.ts:32` + `src/App.tsx:91`.

## Honest boundaries

- The **Builder executor + Docker sandbox** (brief §6: never host-direct) and the
  **Planner→Reviewer loop + evals** are NOT wired yet — they are the next phases, each gated on its
  brief §9 exit criterion. This commit is the corpus the Builder consumes, deliberately first.
- The corpus is a **single real data slice** (Daftari sprint-24). More verified slices (ShrinkMedia,
  DataBank) expand it; the schema + verifier already encforce the "citation must be real" rule.
- No AI, no network, no dependencies added (AGENTS §6). Version bumped `0.1.0 → 0.2.0`.