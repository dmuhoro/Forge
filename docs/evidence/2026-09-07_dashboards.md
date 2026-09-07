# Evidence — Forge dashboards: project + ecosystem boards (2026-09-07)

Constitution Article VII. **Command + observed result, not narrative.**

## What was proven

`forge dash project` renders the task-journal board (states, merged %, blocked-with-reason)
and `forge dash ecosystem` renders a cross-repo board read from each repo's own pristine
`CHANGELOG.md`, both stdlib + offline + fail-closed.

## Observed results (this machine)

| Step | Command | Observed |
|------|---------|----------|
| suite | `python3 -m unittest discover -s tests` | **Ran 49 tests … OK** (37 + 12 dash) |
| project board | `python3 -m forge dash project --journal ~/.forge/tasks.jsonl` | Board renders; integrity true; counts honest (0 tasks at that path) |
| corpus coverage | `project --corpus <repo>/docs/corpus/builder-corpus.json --repo-root <repo>` | `Builder corpus: 10 patterns, N citations proof-read` |
| ecosystem board | `python3 -m forge dash ecosystem --roots /tmp/opencode/Forge <DataBank-clone> <ShrinkMedia-clone>` | rows: Forge 0.2.0·G · DataBank 0.5.0·G · ShrinkMedia Unreleased·G — all "none" problems (each has its own CHANGELOG+README) |
| missing lane | fixture repo without CHANGELOG.md | flagged `missing CHANGELOG.md (doctrine rule 5)`; board still exits 0 (reported, not skipped) |
| fail-closed | corrupt `tasks.jsonl` | `REFUSED: corrupt-journal line 1 …` exit 1 on both library and CLI |
| usage | `forge dash ecosystem` without `--roots` | exit 2, `REFUSED: --roots requires at least one repo checkout` |

## Boundary (honest)

No AI, no web/dashboard service, no network. Both boards read **local checkouts** and emit
Markdown/JSON for an operator; the "ecosystem dashboard" reflects whatever repo checkouts the
caller supplies and is only as current as those checkouts.