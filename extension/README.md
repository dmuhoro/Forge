# Forge Corridor Browser — disposable MV3 extension

Opens the ecosystem corridor's bearer-gated surfaces (DataBank vault `/ui`) in a
plain browser **without the bearer token ever touching the page, storage, or
disk**. It is deliberately disposable: the token lives in the service worker's
memory and evaporates when the worker is killed or the browser closes.

> L5 of the directive: *"disposable MV3 extension"* for the mobile/desktop
> corridor. Evidence: `docs/evidence/2026-09-08_L5_disposable_extension.md`.

## Why it exists

- DataBank serves its `/ui` dashboard on `GET /ui`, which is **bearer-gated** at
  the request boundary (ADR-017; `dvault/server.py:449` calls `_authorize()`
  before routing). A plain browser navigation sends no `Authorization` header, so
  the dashboard returns `401`.
- The old corridor demos used `curl -H "Authorization: Bearer …"`. That works
  but keeps the token on the device's shell history/terminal and hands no visual
  UX. The extension applies the header **at the request boundary via
  `declarativeNetRequest`**, the exact same boundary the server enforces, so a
  `chrome.tabs.create({url: "{host}/ui"})` opens the real dashboard.

## Zero-residue contract

Enforced by tests (`extension/tests/buildRules.test.mjs`, `node --test`):

1. **Token lives only in the service worker's `let token`.** Nothing ever reaches
   `chrome.storage`, `localStorage`, `sessionStorage`, or `document.cookie` — the
   test suite greps every file for *invocation* forms and fails otherwise
   (`zero-residue guard`).
2. **Header is scoped to an exact corridor host.** `buildRules` accepts only the
   hosts declared in `host_permissions` (fail-closed: empty token or out-of-list
   host → `VaultRefused`). The DNR `urlFilter` is anchored (`|*://{host}/*`), so
   lookalike hosts can never receive the header.
3. **No stale state survives restarts.** If a worker is killed and respawned, the
   module-level `token` is back to `""` and any leftover dynamic rule is cleared.
4. **Explicit wipe.** The popup's *Clear token* removes the rule and empties the
   variable; the token is never re-read from anywhere (it was never written).

## Install & use (manual — Chrome is not available in this agent env)

1. `chrome://extensions` → enable *Developer mode* → *Load unpacked* → select
   `extension/`.
2. Pin the icon, open the popup.
3. `Host` defaults to `100.126.191.52:8787` (corridor vault). Paste the bearer
   token (e.g. `DVLT_TOKEN` from `~/.databank/.serve.env`) into the password
   field.
4. *Open /ui* — the worker arms the one DNR rule and opens the dashboard.
5. Done for now? *Clear token*, or just close the browser.

To point at a different corridor vault (e.g. the future VPS per ADR-020 Option B),
add its host to both `manifest.json` and `ALLOWED_HOSTS` in `background.js` — a
host in only one place is refused.

## Layout & verification

```
extension/
  manifest.json             MV3, DNR + activeTab only
  background.js             rule builder (pure, exported) + worker wiring
  popup.html / popup.js     token entry; never reads it back, never stores
  tests/buildRules.test.mjs 6 tests incl. zero-residue guard
```

Run: `node --test "extension/tests/*.test.mjs"` (6/6 green).
Note: pure rule-builder code is unit-tested under plain Node; the real Chrome
load/unpack is a manual Owner step (see evidence doc).