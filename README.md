# Forge — the Orchestrator

**Status: STEP 2 STARTED + DASHBOARDS + HTTP SURFACE + ECOSYSTEM HUB — Builder corpus shipped +
project/ecosystem health boards + ecosystem hub, now reachable in the browser via `forge serve`
(still zero AI) (`2026-09-08`).**
Forge is "how the eco-system gets built and maintained": an orchestrator that plans, builds,
reviews, and ships the ecosystem's products faster and **safer** under a governed loop — the
codified SOP.

## Present build phase (living record — updated on every directive, per build brief §9/README)

- **Step 1 (DONE):** pure-stdlib task schema + deterministic state machine + append-only JSONL
  journal + `forge-task` CLI. 16 tests, journal integrity verified, blocked surfaces with reason,
  terminal states never resurrect. `forge/task.py`, `forge/engine.py`, `forge/journal.py`,
  `forge/cli.py`. Evidence: `docs/evidence/2026-09-05_step1_state_machine.md`.
- **Step 1 EXIT (DONE, 2026-09-05):** brief §9 required *"hand-run 5 real Daftari tasks"* — done with
  the real Daftari v6.5.0 work items: all 5 walked to `merged`, blocked-requires-reason fired,
  terminal states never resurrected, journal verified at 28 lines.
  Evidence: `docs/evidence/2026-09-05_step1_exit_5_real_daftari_tasks.md`.
- **Step 2 / Builder corpus (DONE, 2026-09-06):** the feeding base for the Builder role —
  10 patterns extracted from the VERIFIED Daftari sprint-24 diffs (`4ea952c..36eaf82`) into
  `docs/corpus/builder-corpus.json`, each citing the real `file:line` boundary it protects;
  deterministic stdlib matcher (`forge/corpus.py`, fail-closed: no overlap => no guess) +
  citation verifier + `forge corpus match|verify` CLI. **21 new tests (37 total) green**; all 14
  corpus citations proven to exist at their cited lines against the Daftari checkout at
  `36eaf823`. Evidence: `docs/evidence/2026-09-06_step2_builder_corpus.md`.
- **Dashboards (DONE, 2026-09-07):** `forge dash project` (task-journal states + merged % +
  blocked-with-reason + corpus coverage, `--json` for machines) and `forge dash ecosystem`
  (per-repo board read from each repo's OWN pristine CHANGELOG, with a missing-CHANGELOG lane) —
  stdlib, offline, fail-closed. **12 new tests (49 total) green**; real-repo proof in
  `docs/evidence/2026-09-07_dashboards.md`.
- **HTTP surface (DONE, 2026-09-08):** `forge serve` — both boards over stdlib HTTP (HTML + JSON),
  bearer-token-gated with `hmac.compare_digest`, **fails closed on start** without `FORGE_TOKEN`
  and refuses `0.0.0.0` binds (tailnet exposure is an explicit bind); `Cache-Control: no-store`,
  corrupt journal ⇒ 503. **16 new tests (65 total) green**; real-repo HTTP smoke proof in
  `docs/evidence/2026-09-08_forge_http_surface.md`. This is the browser/phone surface the
  ecosystem dashboard directive (L1) asked for.
- **Ecosystem hub (DONE, 2026-09-08):** the `forge serve` landing now is `GET /` (alias `/hub`) —
  Services panel (DataBank vault live probe + hosted Daftari), Repos panel (all ecosystem repos,
  signed `G` heads), boards + plumbing links; `/board/vault` 302s to the DataBank dashboard.
  Server-side vault probe classifies reachable-ok / reachable-but-refused (auth gate) / unreachable
  and surfaces the reason — no silent drop (ADR-020). **6 new tests (71 total) green**.
- **Forge-driven Daftari diffs (DONE, 2026-09-08):** two real, shipped Daftari fixes driven through
  the task journal to `merged` — `parseKESInput` money fail-open (`f64acc5` G, suite 399→402) and
  the `check-i18n` DYNAMIC_KEYS whitelist drift (`0af9d0f` G, fail-closed on missing key).
  Each committed individually, SSH-signed, pushed, CHANGELOG'd in Daftari (own-it-first).
  Evidence: `docs/evidence/2026-09-08_L4_forge_driven_daftari_diffs.md`.
- **Not started (honestly):** the Builder executor + Docker sandbox wiring, Planner→Reviewer loop,
  evals, RAG/pgvector. (The HTTP surface now ships the boards; the Builder executor and the agent
  loop itself are still the next gate and need the sandbox phase.) The Builder consumes the corpus
  BEFORE touching code, so its first pass on low-risk tasks is grounded; the brief §9 step-2 exit
  ("5 clean diffs in a row without hand-holding") is the next gate and needs the sandbox phase.

## What is already proven (lives in ShrinkMedia, one source of truth)

The portable core is implemented and verified in `ShrinkMedia` (`ADR-014/015`):
`app/src/main/java/com/shrinkmedia/compressor/forge/*` —
- **`ForgeTask`** — deterministic state machine `queued → … → merged / blocked` (no silent drops,
  terminal states never resurrect). 12 tests.
- **`EcosystemIndex`** — offline keyword corpus for "search up the ecosystem". 11 tests.
- **`LessonBook`** — Phase-9 lessons capture. 6 tests.
- **`ModelRouter`** — free-open-source-AI seam (online → open-weight; offline → local fallback),
  OFF default, decision-only. 11 tests.
Plus the **Personal Intelligence** decision core (`personal/*`): vault categorisation, Image
Insight (clarify-or-proceed), and virtual-me routing. 25 tests.

These will be lifted/re-implemented into this program unchanged-in-behaviour (ADR-014), then the
real connected transport (RAG over DataBank, sandboxed builders, evals) is added — that is what
makes the stargate a live door.

## Pillars (ADR-013 §4)

1. **RAG (Retrieval)** — the corpus = Daftari `ai-context/` + every product's ADRs/PRDs + the vault.
2. **Agents** — Planner / Retriever / Builder / Reviewer / Ops; ShrinkMedia/SOP is the current
   builder; Forge.ai + Hermes-Forge are the future hosts.
3. **Evals** — Reviewer gate + judge/calibration loop; false-merge / false-block rates gate autonomy.
4. **Safety** — sandboxed builders, hard file-scope, prompt-injection defense, rate/cost caps,
   fail-closed gates (mirrors ShrinkMedia Constitution §1/§5).
5. **ML foundations** — reasoning core on owner hardware (RTX 3090+/Mac mini) behind ModelRouter.

## Invariants (inherited from ShrinkMedia AGENTS/Constitution)

Fail closed · enforcement at the real boundary · no silent drops · never weaken a test to pass ·
evidence over narrative · honesty over optimism · work sequentially in layers · one workspace at a
time · all main commits SSH-signed.

## Roadmap (sequential, honest)

1. **Lift decision core** into this program (behaviour-identical; keep ShrinkMedia one source of
   truth until then).  
2. **Planner→Reviewer loop + evals + sandbox** (CLI-first).  
3. **DataBank
   RAG + ModelRouter transport** on owner hardware.
4. **Adapters** to each product.

Estimated focused size: server/CLI + evals + sandbox, ~6–10k LOC plus ~2–4 wk for adapters.
Full cross-repo estimates: `ShrinkMedia → docs/operations/ecosystem-roadmap.md`.

## Honest boundary

Forge does not yet autonomously build anything. The safe form of self-improvement is **gated**:
Forge proposes, a gate reviews, CI + tests referee, the owner decides. Unconstrained
self-modification is explicitly rejected (see `ShrinkMedia/docs/operations/ecosystem-orientation.md`).
