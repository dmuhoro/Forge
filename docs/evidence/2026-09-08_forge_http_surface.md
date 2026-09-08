# Forge HTTP surface — real-boundary proof (L1, 2026-09-08)

The two dashboards are now reachable over stdlib HTTP, token-gated and
fail-closed by construction. This file records the observed proof.

## Commands

```bash
python3 -m forge serve \
  --journal ~/.forge/tasks.jsonl \
  --corpus docs/corpus/builder-corpus.json \
  --repo-root . \
  --roots ~/workspace/projects/DataBank ~/workspace/projects/Forge ~/workspace/projects/ShrinkMedia \
  --host 127.0.0.1 --port 8443            # bind a tailnet IP to expose on Tailscale
```

with `FORGE_TOKEN` set (bearer auth, mandatory).

## Observed results (smoke live server, port 8843)

| route | no token | bearer token | observed |
|-------|----------|--------------|----------|
| `/healthz` | 200 | 200 | liveness open by design |
| `/project` | 401 | 200 | HTML board renders `Forge Project Board`, merged % |
| `/ecosystem` | 401 | 200 | HTML board renders all three repos |
| `/ecosystem.json` | 401 | 200 | JSON, signed `G` heads |
| `/project.json` | 401 | 200 | JSON, type `project` |
| unknown route | — | 404 | `{"error":"no route: /nope"}` |

`/ecosystem.json` body (excerpt):
`[{"name":"DataBank","head":"8440958","signed":"G"},{"name":"Forge","head":"6baf75a","signed":"G"},{"name":"ShrinkMedia","head":"aaf9015","signed":"G"}]`

## Fail-closed proofs

- Server refuses to start (exit 1, stderr `REFUSED: FORGE_TOKEN is not set ...`) with
  empty `FORGE_TOKEN`.
- Server refuses to start with `--host 0.0.0.0` or `::` (stderr `REFUSED: refusing to bind
  broadcast address ...`) — no random public broadcast. Tailnet exposure = explicit bind.
- Corrupt journal over HTTP → **503** `{"error":"board refused: ..."}` (asserted in tests).
- 401 on wrong token; 404 on unknown route — asserted in `tests/test_serve.py`.

## Test suite

`python3 -m pytest` → **65 passed** (49 → +16 from `tests/test_serve.py`).