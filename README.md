# Forge — the Orchestrator

**Status: SCAFFOLD — the decision core is proven; the program is next.** Forge is "how the
eco-system gets built and maintained": an orchestrator that plans, builds, reviews, and ships the
ecosystem's products faster and **safer** under a governed loop — the codified SOP.

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
   truth until then). 2. **Planner→Reviewer loop + evals + sandbox** (CLI-first). 3. **DataBank
   RAG + ModelRouter transport** on owner hardware. 4. **Adapters** to each product.

Estimated focused size: server/CLI + evals + sandbox, ~6–10k LOC plus ~2–4 wk for adapters.
Full cross-repo estimates: `ShrinkMedia → docs/operations/ecosystem-roadmap.md`.

## Honest boundary

Forge does not yet autonomously build anything. The safe form of self-improvement is **gated**:
Forge proposes, a gate reviews, CI + tests referee, the owner decides. Unconstrained
self-modification is explicitly rejected (see `ShrinkMedia/docs/operations/ecosystem-orientation.md`).