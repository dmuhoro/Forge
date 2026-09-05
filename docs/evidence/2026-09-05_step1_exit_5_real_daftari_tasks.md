# Forge step-1 EXIT evidence — 5 real Daftari tasks hand-run through `forge-task` (2026-09-05)

> Brief §9 step-1 exit criterion: *"Hand-run 5 real Daftari tasks through it manually. Exit: state
> machine never gets stuck, history logs correctly, blocked surfaces properly."*

## The 5 real tasks (the actual Daftari v6.5.0 work, completed this directive)

Journal: `FORGE_JOURNAL=/tmp/opencode/forge-evidence/pilot-tasks.jsonl` (append-only, 28 lines at
verification time; each task's lifecycle is recorded as JSON events).

| task_id | Daftari v6.5.0 work item | status |
|---|---|---|
| `60637997f5804c4d` | Install banner + installability nudge | **merged** |
| `fdcfd45e17c54e14` | Real Supabase client into the production build | **merged** |
| `559693d81db64987` | Surface sync config in Settings | **merged** |
| `aa2c46434e91413d` | Bilingual install strings (en+sw, 226 keys) | **merged** |
| `f806a301ac754b7f` | supabase-wiring runbook + CHANGELOG 6.5.0 | **merged** |

## Commands + observed results

```
$ python3 -m forge.cli new --repo daftari --title "Install banner + installability nudge" ...
queued 60637997f5804c4d [daftari] ...          # 5 real tasks created, all queued
$ python3 -m forge.cli to <id> retrieving --via opencode-pilot --note "retrieved real Daftari v6.5.0 context"
$ python3 -m forge.cli to <id> building  --via opencode-pilot --note "built within daftari v6.5.0"
$ python3 -m forge.cli to <id> reviewing --via opencode-pilot --note "gates run locally"
$ python3 -m forge.cli to <id> merged    --via opencode-pilot --note "approved: tests+lint+typecheck+build green; signed; pushed"
  each → merged (attempts 0/3)                   # 5/5 reached MERGED; state machine never got stuck
$ python3 -m forge.cli to <merged-id> retrieving
REFUSED: terminal state merged cannot resurrect to retrieving (id=…)   # terminal never resurrects
$ python3 -m forge.cli to <fresh> blocked
REFUSED: blocked requires an explicit reason (id=…)                    # no silent drop
$ python3 -m forge.cli to <fresh> blocked --note "genuine blocker: needs owner's device"
  blocked (attempts 0/3)                                                # reason retained
$ python3 -m forge.cli to <blocked-id> reviewing
REFUSED: terminal state blocked cannot resurrect to reviewing (id=…)   # blocked is a route, not a drop
$ python3 -m forge.cli verify
journal ok: 28 task(s), all lines parses + hydrates
```

## Verdict

- **State machine never gets stuck:** 5/5 real tasks walked the full legal path to `merged`.
- **History logs correctly:** `verify` hydrates all 28 journal lines from events only (no trusting
  the tiny cached status), append-only, corrupt line = refusal.
- **Blocked surfaces properly:** reason mandatory, retained in `show`, terminal.
- **Honest boundary:** the pilot records *already-completed* Daftari work retroactively (the step-1
  machine has no Builder yet). It does **not** claim Forge built these tasks — it proves the
  journal+engine handle 5 real Daftari items end-to-end as required by brief §9 step 1. Step 2
  (wire in Builder) starts next, gated by this exit.