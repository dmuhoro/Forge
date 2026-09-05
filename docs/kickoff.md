# Forge kickoff — step 1 shipped (task schema + state machine, zero AI)

Status: **Step 1 of the owner's build brief (2026-09-05) is implemented and tested.**
Authoritative brief: `docs/owner-build-brief-2026-09-05.md` (preserved from the ShrinkMedia
`Assets/` copy so Forge is self-contained). This doc proves the earlier decisions and why the
steady full build is deferred, honestly.

## What shipped here

`forge/` + `tests/`, python-stdlib-only, no network, no AI:

| Piece | Behavior |
|---|---|
| `forge/task.py` | Task schema matching brief §2 (task_id, repo, created_by, status, prd_ref, architecture_ref, file_scope, acceptance_criteria, review_checklist_ref, attempts, max_attempts, review_result, events/history). Deterministic, fail-closed. |
| `forge/engine.py` | State machine `queued → retrieving → building → reviewing → changes_requested → building \| merged` (or `blocked`). Terminal states never resurrect; attempts cap → `blocked` routes to the human, never a silent drop; `merged` requires a recorded review result; `changes_requested` requires a note; `blocked` requires a reason. |
| `forge/journal.py` | Append-only JSONL journal, fsync per line, corrupt line = **refusal** (never skipped) — the same fail-closed contract as the DataBank vault journal. |
| `forge/cli.py` | `forge-task new/to/show/list/verify` — a human (or later an agent) drives the real boundary without AI. |
| `tests/test_forge.py` | 16 tests exercising the real production path (engine + journal + CLI subprocesses), including refusal/exit-code assertions. |

Run self-proof anywhere: `python3 -m unittest discover -s tests -v`.

## Dafari pilot & the "54 tests" claim

Brief says step 1's exit is *"Hand-run 5 real Daftari tasks through it"*. Not done yet —
**honest boundary**: step 1's exit is the owner's 5 real tasks, not our synthetic ones. The pilot
repo (Daftari) needs its own green sprint first (v6.4.0 — see Daftari repo), and the claim
"54 tests" there has to be verified against the real suite before we lean on it. We will not trust
the number; we will count it.

## Dependency justification (AGENTS §6 — why these when something else exists)

The brief's stack (Stack line, §0) is the **target endgame**, not this sprint:

| New thing at full build | Gap it fills that stdlib/CLI cannot | When |
|---|---|---|
| FastAPI + Railway | 24/7 horizontal orchestrator host + HTTP API + task-queue store — a CLI + JSONL cannot serve a dashboard or run unattended. | After step 1 exit criterion met |
| Supabase (Postgres + `pgvector`) | RAG vector store + auth; the brief's own §3 says pgvector avoids new infra (Supabase is already Daftari's DB/auth). | Step 4 (retrieval layer), gated by step 3 exit |
| Docker sandbox | brief §6: builder runs in ephemeral containers, never host-direct — a hard security boundary an LLM prompt cannot provide. | Step 2 (wire in Builder) |
| Embedding model | `retrieving` state needs semantic + hybrid search; ModelRouter (ShrinkMedia) already governs which open-weight model, OFF by default. | Step 4 |
| Vercel dashboard | brief §8, phase 6 — only when the pipeline is trustworthy enough to not tail logs. | Last, explicitly |

Nothing is added before its phase's **exit criterion** is met (brief §9). We are executing this
early, sequentially, with tests green — and intentionally NOT parallelizing the full stack now
(scoped to *should this ship now?* → no: first tasks must be validated real needs per brief's own
note, and Daftari is pre-scale).

## RSI alignment (ShrinkMedia governance)

- Forge is the **mechanism**, gated by the same Ownership rules: autonomy dial stays 0; the owner
  is Planner/Approver. Every merged task carries the human-approval event in its journal.
- Reviewer evals (brief §5) **are** measurement M10 (false-merge / false-block rate) from
  ShrinkMedia `docs/operations/measurement.md`; the journal's `review_result` + attempts fields
  are the data source. Forge does not self-authorize — it reports, gates, and logs.

## Security posture (from brief §6) — already reflected in the code

- File-scope is carried *on the task* and will be enforced by the orchestrator as a hard check,
  never as an LLM instruction, before any Builder is wired in.
- Secrets never live in task JSON; the schema has no secrets fields.
- Rate/cost caps are the `max_attempts` + `blocked` route — a stuck loop cannot burn budget silently;
  it must surface to the human.

## README requirement (brief, final line)

README.md is updated on every directive (kept current below: present phase = step 1 shipped,
next = owner hand-runs 5 real Daftari tasks → step 2).