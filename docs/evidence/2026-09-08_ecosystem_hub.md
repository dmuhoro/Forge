# Forge ecosystem hub — real-boundary proof (L3, 2026-09-08)

`forge serve` now lands on the **ecosystem hub**: one browser address for the
whole corridor (Forge boards + DataBank vault + hosted Daftari), per ADR-020.
This file records the observed proof.

## Commands

```bash
python3 -m forge serve \
  --journal ~/.forge/tasks.jsonl \
  --corpus docs/corpus/builder-corpus.json \
  --repo-root . \
  --roots ~/workspace/projects/DataBank ~/workspace/projects/Forge ~/workspace/projects/ShrinkMedia \
  --host 127.0.0.1 --port 8443            # bind a tailnet IP to expose on Tailscale
  # --vault-base http://100.126.191.52:8787   (default http://127.0.0.1:8787)
```

with `FORGE_TOKEN` set (bearer auth, mandatory).

## Observed results (live server + live DataBank vault)

| route | no token | bearer token | observed |
|-------|----------|--------------|----------|
| `/` (hub) | 401 | 200 | `ShrinkMedia Ecosystem Hub` — Services + Repos panels, plumbing |
| `/hub` | 401 | 200 | same hub (alias) |
| `/board/vault` | 401 | **302 → `<vault_base>/ui`** | vault dashboard redirect, not proxied |
| `/healthz` | 200 | 200 | liveness open by design |

The hub renders:
- **Services panel**: DataBank vault row live-probed via `probe_vault`
  (`reachable / reachable-but-refused / unreachable`, reason always shown) and
  the hosted Daftari row (`https://daftari-amber.vercel.app`).
- **Repos panel**: DataBank / Forge / ShrinkMedia with signed `G` heads,
  versions and problems (from each repo's own pristine CHANGELOG per
  documentation doctrine).
- **Boards + plumbing**: `/project`, `/ecosystem`, vault dashboard, Daftari.

## Probe classification (the honest seam)

DataBank (ADR-017) gates `/healthz` behind the bearer token, so a live vault
without credentials answers 401. The probe reports that truthfully:

| probe result | hub renders |
|--------------|-------------|
| `ok:true, reachable:true` | `ok — reachable — N records` |
| `ok:false, reachable:true` (auth gate) | `http 401 — reachable, but /healthz refused` |
| `ok:false, reachable:false` (no listener) | `unreachable — no response: <reason>` |

No silent drop: a dead vault shows `unreachable`, never a blank row.

## Test suite

`python3 -m unittest discover -s tests` → **71 passed** (65 → +6 from
`tests/test_serve.py`), including a hermetic reachable-but-auth probe using a
local 401-returning server, an unreachable-probe-never-raises check, and the
`/board/vault` redirect asserted without following.

## Real-corridor smoke (same machine, live vault on 8787)

- `GET /` with token → 200; HTML contains `DataBank vault`, `Daftari`,
  `ShrinkMedia Ecosystem Hub`, all three repo heads.
- `curl -s -o /dev/null -w '%{http_code}' -H 'Authorization: Bearer …'
  http://127.0.0.1:8443/board/vault` → `302`.
- Live vault responds 401 to an unauthed probe → hub classifies
  `reachable, but /healthz refused` (proven by `probe_vault` on
  `http://100.126.191.52:8787`).