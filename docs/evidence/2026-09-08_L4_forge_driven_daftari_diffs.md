# Forge-driven Daftari diffs — real-boundary proof (L4, 2026-09-08)

Two **real, shipped** Daftari fixes walked through the forge task engine end to
end. This is the L4 exit proof: the journal was the single source of truth, each
task carried acceptance criteria, each diff was committed individually,
SSH-signed (`%G?` = G) and pushed, and the reviewer gate was recorded.

## Journal (single source of truth)

`~/.forge/tasks.jsonl` — append-only, `forge verify` => `journal ok: 10 task(s)`.

| task_id | repo | title | status |
|---|---|---|---|
| `adce53bbfa964dc8` | Daftari | parseKESInput silently truncates malformed money input (fail-open) | **merged** |
| `bc7c1d3d0cd741a2` | Daftari | check-i18n hardcoded DYNAMIC_KEYS whitelist drifted (false positives) | **merged** |
| (5) | — | prior step-1 EXIT pilot tasks | merged/blocked per `2026-09-05_step1_exit` |

## Task 1 — `adce53bbfa964dc8` → `f64acc5` G

Observed results:

```
$ python3 -m forge new --repo Daftari --title "parseKESInput silently truncates ..." --accept "malformed returns null; valid still parses; tests cover; suite green"
queued adce53bbfa964dc8 [Daftari] ...
$ python3 -m forge to adce53bbfa964dc8 building --via agent-host --note "reproduced: 1.5.5->2, 1-2->1, 15..5->15, 1500.10.5->1500"
adce53bbfa964dc8: building (attempts 0/3)
$ npx tsx -e "parseKESInput('1.5.5')"          # AFTER fix: null (was 2)
$ python3 -m forge to adce53bbfa964dc8 merged --via reviewer --note "review f64acc5: malformed->null (fail-closed); valid parses unchanged; tests 399->402; lint+typecheck clean"
adce53bbfa964dc8: merged (attempts 0/3)
```

- Daftari suite: `npm run test:run` => **402 passed** (399 baseline + 3 new
  cases); `npm run typecheck` + `npm run lint` clean.
- Commit `f64acc5 G` pushed; CHANGELOG row later (`3cedd2f G`).

## Task 2 — `bc7c1d3d0cd741a2` → `0af9d0f` G

Observed results:

```
$ python3 -m forge new --repo Daftari --title "check-i18n: hardcoded DYNAMIC_KEYS whitelist drifted"
queued bc7c1d3d0cd741a2 [Daftari] ...
$ python3 -m forge to bc7c1d3d0cd741a2 building --via agent-host --note "source dynamic keys from OnboardingScreen + Receipt literals"
bc7c1d3d0cd741a2: building (attempts 0/3)
$ npm run check:i18n                                   # before: 3 unused warnings (yes_set_q1..3)
✅ i18n check passed — 238 keys in use, 238 in sw.json, 238 in en.json   # after: zero unused
$ sed -i "s/'pain_uncollected_debts'/'pain_uncollected_debts_broken'/" src/screens/OnboardingScreen.tsx && npm run check:i18n
❌ Dynamic key "pain_uncollected_debts_broken" ... MISSING from sw.json/en.json     # fail-closed proven
$ python3 -m forge to bc7c1d3d0cd741a2 merged --via reviewer --note "review 0af9d0f: sourced from real render sites; fail-on-missing proven; check green"
bc7c1d3d0cd741a2: merged (attempts 0/3)
```

- Commit `0af9d0f G` pushed; CHANGELOG row `3cedd2f G`.
- Dynamic-key scan returns exactly the 14 real keys (4 pain + 4 method +
  3 yes-set + 3 receipt literals) and fails loudly if any is missing — the old
  hand list silently missed `yes_set_q1..3`.

## L4 exit claims (honest)

- **Real diffs, not placeholders**: both fixes are user-facing improvements
  (money-entry safety on a P0 path; i18n linter accuracy), green, signed,
  pushed, and recorded in Daftari's own CHANGELOG (own-it-first doctrine).
- **Journal drove the work**: task creation -> transitions -> merged all recorded
  append-only at `~/.forge/tasks.jsonl`; `forge verify` passes.
- **Reviewer gate exercised**: `merged` only from `reviewing` with a recorded
  review note (engine-enforced).
- **Not claimed**: the Builder executor / Planner→Reviewer AI loop is still
  future work (README "Not started" lane). These tasks were agent-driven through
  the deterministic engine, which is the current Forge contract.