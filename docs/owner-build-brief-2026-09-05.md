# Forge Orchestrator — Build Brief for OpenCode v0.2

**Status:** Executive directive — hand this to OpenCode as the working spec.
**Pilot repo:** Daftari (has `ai-context/`, CI, 54 tests, dev-playbook docs already in place).
**Stack:** Railway (orchestrator host + Postgres), Supabase (DB/auth — can double as task-queue store), Python (FastAPI), Docker (sandboxed execution), Vercel (dashboard frontend, Phase 6).
**Note on Daftari context:** Daftari has not yet reached real-world users at scale. Do not let Forge become another feature-building push on top of that risk — the first tasks routed through Forge once it's live should be validated, real, user-facing needs, not busywork invented to exercise the pipeline.

---

## 0. What this system is

Not a chatbot, not a single agent. A deterministic orchestration layer with specialized agent roles around it — your execution team. You (the human) stay the Planner/Approver/Architect. Everything else is delegated, gated, and logged.

Three things converge in this build: (1) a working 24/7 autonomous execution team, (2) practical AI/ML engineering skill — RAG, agents, orchestration, evals, safety — learned by building the real thing, not tutorials, and (3) a compounding asset, not a one-off tool.

---

## 1. Agent Roles

| Role | Model/Tool | Job | Autonomy |
|---|---|---|---|
| Planner | Claude | Turns a spec into a task graph using the 4-file playbook (PRD, Architecture, Agent Brief, Review Checklist) | Proposes only — human approves the task graph before queueing |
| Retriever | Embedding + vector store (new, see §3) | Feeds Planner/Builder relevant context: PRDs, ADRs, past reviewer notes, related code — instead of static file paths | Read-only, always-on support layer |
| Builder | Gemini / OpenCode | Executes one task: edits code, runs tests locally, returns a diff | Full autonomy inside the task's file scope only |
| Reviewer | Separate Claude instance, strict persona | Reviews diff against PRD + Architecture + Checklist; scored over time (see §5) | Blocking gate — nothing merges without a pass |
| Ops | Scripted, non-AI | CI, monitoring, dependency bumps, backups, uptime | Fully automated, deterministic |
| Orchestrator | Python/FastAPI service | Holds state, routes tasks, enforces the gate, feeds the dashboard | Deterministic code, not an agent |

Ops stays non-AI on purpose — uptime and monitoring are solved problems; don't introduce agent unpredictability where none is needed.

---

## 2. Task Schema

```json
{
  "task_id": "daftari-0042",
  "repo": "daftari",
  "created_by": "planner",
  "status": "queued",
  "title": "Add low-stock alert threshold to inventory settings",
  "prd_ref": "docs/prd/inventory-alerts.md",
  "architecture_ref": "docs/architecture/inventory-alerts.md",
  "file_scope": ["src/features/inventory/settings.tsx", "src/features/inventory/inventoryRepository.ts"],
  "acceptance_criteria": [
    "Threshold is per-product, stored via repository.ts pattern",
    "Existing 54 tests still pass",
    "New test covers threshold edit + alert trigger"
  ],
  "review_checklist_ref": "docs/review-checklist.md",
  "retrieved_context": [],
  "attempts": 0,
  "max_attempts": 2,
  "assigned_agent": null,
  "diff_url": null,
  "review_result": null,
  "eval_score": null,
  "history": []
}
```

`status`: `queued → retrieving → building → reviewing → changes_requested → merged` (or `blocked` after `max_attempts` — always routes to the human, never silently dropped).

---

## 3. Retrieval Layer (RAG) — new in this version

Purpose: stop hand-pasting file scope and context. Give Builder/Reviewer grounded, relevant material automatically.

- **Source corpus:** Daftari's `ai-context/` docs, PRDs, ADRs, past `review_result.notes` (so the Reviewer's own history becomes searchable precedent), and the codebase itself (chunked by function/module, not raw file dumps).
- **Pipeline:** chunking → embeddings → vector store (Supabase's `pgvector` extension — no new infra needed, it's already in your stack) → hybrid search (keyword + semantic) → rerank top results before injecting into the task's `retrieved_context`.
- **Where it plugs in:** a `retrieving` state between `queued` and `building` — orchestrator queries the vector store using the task title + acceptance criteria, attaches top-k results to the task object, then hands off to Builder.
- **Why this matters beyond convenience:** this is the actual AI engineering skill-building piece — chunking strategy, hybrid search, reranking — learned on real, load-bearing data instead of a toy dataset.

---

## 4. Orchestrator Flow

1. Human writes/approves a task, or Planner proposes a batch from a feature spec (human approves the batch).
2. Orchestrator sets `status: retrieving`, Retriever attaches context, `status: building`.
3. Builder receives task JSON + retrieved context, tool access scoped only to `file_scope`. Returns diff + test output.
4. Orchestrator sets `status: reviewing`, sends diff + task + checklist to Reviewer.
5. Reviewer returns `pass` or `changes_requested` with line-level notes, plus a self-reported confidence score.
   - `pass` → Ops runs CI → merge → `status: merged`.
   - `changes_requested` → back to Builder, `history` gets the notes, `attempts += 1`.
   - `attempts > max_attempts` → `status: blocked`, surfaced on dashboard, not auto-retried.
6. Every transition logged to `history` with timestamp — this is what dashboard and evals both read from.

State machine, not a chat loop — deterministic transitions are what make 24/7 operation debuggable instead of a black box.

---

## 5. Reviewer Gate + Evaluation Layer

**Reviewer system prompt:**
```
You are the Reviewer for [repo]. You did not write this code. Your only job is
to check the diff against the task's PRD, Architecture doc, and Review Checklist.

Rules:
- Reject if the diff touches files outside file_scope.
- Reject if any acceptance_criteria item is unmet.
- Reject if existing tests are weakened, skipped, or deleted without justification in history.
- Check for the specific failure modes in review_checklist_ref (e.g. Daftari's
  cross-tenant isolation, money.ts usage for all currency math, i18n key coverage).
- Do not rewrite the code yourself. Return pass/fail with specific, line-referenced notes only.
- If uncertain whether something violates architecture intent, fail with a
  question rather than guessing.

Output strict JSON: {"result": "pass"|"changes_requested", "notes": [...], "confidence": 0-1}
```

Run as a genuinely separate API session from Builder — never let the same context that wrote the code grade it.

**Evals (new in this version):** don't just trust the Reviewer — measure it.
- Log every Reviewer decision + outcome (did a `pass`'d task later need a hotfix? did a `changes_requested` turn out to be a false positive on manual check?).
- Weekly: sample 5–10 merged tasks, human-audit them against the checklist, compare to Reviewer's own confidence score. This is your LLM-as-a-judge calibration loop.
- Track false-merge rate and false-block rate over time — this number is your actual gate for widening autonomy in Phase 5, not a calendar date.

---

## 6. Safety & Guardrails

Non-negotiable before any autonomy widening:
- Builder's tool access is sandboxed in ephemeral Docker containers — never runs directly on the host.
- File scope enforcement happens at the orchestrator level (hard-coded check), not just as a Reviewer instruction — don't rely on prompts alone for a security boundary.
- Secrets via environment variables/secrets manager — never in task JSON, logs, or retrieved context.
- Guard against prompt injection from retrieved context: if a code comment or doc chunk contains instruction-like text (e.g. "ignore previous instructions"), the Retriever strips or flags it before it reaches Builder/Reviewer.
- Rate/cost caps per task (max API calls, max attempts) — prevents a stuck loop from burning budget silently.

---

## 7. Ops Layer

- CI: existing GitHub Actions (Daftari already has this) as the final merge gate.
- Monitoring: Uptime Kuma (self-hosted, free) on Railway alongside the orchestrator.
- Dependency updates: Dependabot.
- Backups: automated, scheduled, tested restores (untested backups don't count).
- Alerting: failures/downtime reach the human via Telegram/Slack — no polling required.

---

## 8. Dashboard (Phase 6, Vercel)

Thin, read-only view over the orchestrator's task log:
- Task queue by status.
- Blocked list — the only section needing daily human attention.
- Activity feed — what shipped overnight.
- Reviewer eval strip — running false-merge/false-block rate.
- PRI/completion strip, reusing the existing Finish Line Dashboard fields.

---

## 9. Build Order — do not parallelize

1. **Task schema + state machine, zero AI.** Hand-run 5 real Daftari tasks through it manually. *Exit: state machine never gets stuck, history logs correctly, blocked surfaces properly.*
2. **Wire in Builder.** Low-risk tasks only. *Exit: 5 clean diffs in a row without hand-holding.*
3. **Wire in Reviewer gate.** Deliberately feed it bad diffs to confirm it rejects them. *Exit: caught at least one real bad diff, zero false merges.*
4. **Retrieval layer (RAG).** Add pgvector corpus + hybrid search once the core loop is trustworthy. *Exit: retrieved context measurably improves Builder's first-pass accuracy vs. static file scope.*
5. **Ops automation.** Uptime Kuma, CI gate, backups, alerting. *Exit: an incident reaches the human without polling.*
6. **Evals + guardrails hardened.** Weekly audit cadence running, injection defenses tested. *Exit: false-merge rate tracked and trending down.*
7. **Widen the loop.** Increase `max_attempts` autonomy and batch size only as blocked-rate and false-merge-rate both stay low.
8. **Dashboard.** Build once you trust the pipeline enough to want a bird's-eye view instead of tailing logs.

**README requirement:** every directive handed to OpenCode for this project should end with a README-update instruction — keep `README.md` a current, living record of what Forge can do and its present build phase, not a snapshot of intent from day one.

Rough timeline: 3–4 weeks of focused work to a trustworthy loop on Daftari alone, steps 1–3. Steps 4–6 are the AI/ML engineering skill-building phase — do not start them before step 3's exit criterion is genuinely met.
