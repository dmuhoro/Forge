# L5 evidence — disposable MV3 extension, bearer-gated dashboard in a browser

> Directive step 5: *"Disposable browser surface for the corridor."* Claim proven
> here: the extension's DNR `modifyHeaders` rule is exactly the mechanism that
> opens a bearer-gated endpoint (`GET /ui`) in a plain browser, and the token is
> provably RAM-only. The real Chrome load is a manual Owner step (this agent env
> has no browser); everything else is verified below.

## 1. Rule-builder unit tests (structural, executable)

Structure: `background.js` exports a pure `buildRules(token, host)`; the worker
wiring is wrapped in `typeof chrome !== "undefined"` so Node can import it with
zero shims.

```
$ cd Forge && node --test "extension/tests/*.test.mjs"
# tests 6        # pass 6
```

Covered: exactly one `modifyHeaders` rule (Authorization, operation *set*, value
= token); empty/whitespace token → `REFUSED`; host outside the corridor
allow-list → `REFUSED` (fail-closed); token string appears in the rule JSON in
exactly one place (the Authorization value); **zero-residue guard** — every
extension JS file is scanned for `chrome.storage.*`, `localStorage.*`,
`sessionStorage.*`, `document.cookie` *invocations* → none (fail otherwise);
manifest is MV3 with a bounded host list (no `*://*`).

## 2. Live proof against a real bearer-gated vault (2026-09-08)

Spawned a throwaway DataBank vault (`proof-token-abc`) on `127.0.0.1:8787` —
the same server that gates `GET /ui` at the request boundary in production.

```
$ curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8787/healthz
401                                          # no token → refuse (server fail-closed)
$ <header exactly as the extension rule emits>
   Authorization: Bearer proof-token-abc
$ curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer proof-token-abc" http://127.0.0.1:8787/ui
200                                          # /ui opens — this is what DNR makes happen
```

Rule the worker would arm, printed from the shipped code:

```
$ node --input-type=module -e "import {buildRules} from './extension/background.js'; console.log(buildRules('proof-token-abc','127.0.0.1:8787')[0].condition.urlFilter)"
|*://127.0.0.1:8787/*
```

The anchored filter (`|` = start of URL, `*://` = http/https) means a lookalike
like `http://evil.io/http://127.0.0.1:8787/ui` cannot match → no header.
Host-scoping is also enforced in code (`ALLOWED_HOSTS` intersection with
`host_permissions`). Test vault torn down afterwards (no listeners on
`127.0.0.1:8787`).

## 3. Honest scope

- **Done and verified:** header mechanism against the production server code, host
  scoping, fail-closed refusals, zero-residue contract, RAM-only token.
- **Manual Owner step:** loading the unpacked extension in Chrome and the actual
  in-browser click-through. This repo has no Chrome. Verified by inspection of
  MV3 semantics (`declarativeNetRequest` `modifyHeaders`, `main_frame`) which is
  the documented mechanism used above.

## What was NOT tested

Anything at the DataBank HTTP layer this doesn't own (auth is DataBank's).
Reachability of the live vault from the phone depends on Tailscale, as before.