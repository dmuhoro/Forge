# Forge step 1 evidence — CLI-driven task lifecycle (2026-09-05)

## What was proven (real boundary: `python3 -m forge` CLI over the append-only journal)

### 1. Happy path: queued → retrieving → building → reviewing → changes_requested → building → reviewing → merged

```
$ python3 -m forge new --repo Daftari --title "Verify the PWA is installable on Android (manifest PNG icons)" ...
queued 2f1e8491493947fe [Daftari] Verify the PWA is installable on Android (manifest PNG icons)
$ python3 -m forge to 2f1e8491493947fe retrieving --via planner   → retrieving (attempts 0/3)
$ python3 -m forge to 2f1e8491493947fe building   --via builder   → building (attempts 0/3)
$ python3 -m forge to 2f1e8491493947fe reviewing  --via builder   → reviewing (attempts 0/3)
$ python3 -m forge to 2f1e8491493947fe changes_requested --via reviewer --note "icons still svg-only"
                                                                  → changes_requested (attempts 1/3)
$ python3 -m forge to 2f1e8491493947fe building   --via builder   → building (attempts 1/3)
$ python3 -m forge to 2f1e8491493947fe reviewing  --via builder   → reviewing (attempts 1/3)
$ python3 -m forge to 2f1e8491493947fe merged     --via reviewer --note "PNG 192+512 + apple-touch-icon verified"
                                                                  → merged (attempts 1/3)
```
`show` lists the full timestamped history; attempts incremented exactly once per review loop.

### 2. Blocked route = explicit reason, never a silent drop

```
$ python3 -m forge to 739d7e1256de49d9 blocked --via owner --note "owner must approve the exact doc scope first"
  blocked_reason: owner must approve the exact doc scope first
```

### 3. Terminal state never resurrects (fail-closed)

```
$ python3 -m forge to 739d7e1256de49d9 building --via builder
REFUSED: terminal state blocked cannot resurrect to building (id=739d7e1256de49d9)   (exit 2)
```

### 4. Journal integrity

```
$ python3 -m forge verify
journal ok: 8 task(s), all lines parses + hydrates
```

### 5. Automated suite

```
$ python3 -m unittest discover -s tests     → Ran 16 tests — OK
```

## Exit-criterion status (brief §9 step 1)

"State machine never gets stuck, history logs correctly, blocked surfaces properly" — **met for
the engine**. The other §9 step-1 words, "**Hand-run 5 real Daftari tasks through it**", are
explicitly **not** claimed: those are the owner's 5 real tasks on the real pilot repo, and Daftari
first needs its v6.4.0 correctness pass. Closing this gap is the next concrete milestone — not a
claim we will fake with synthetic tasks.