// Forge Corridor Browser — background service worker (MV3, ESM).
//
// Zero-residue contract (fail-closed):
//   * the bearer token lives ONLY in this worker's memory (`let token`);
//   * nothing is ever written to chrome.storage / localStorage / cookies;
//   * authorization headers are applied EXCLUSIVELY to the exact host listed in
//     `host_permissions` — if the host is not allowed the worker refuses;
//   * the service worker can be killed by the browser at any moment, which erases
//     the token automatically; clearing it explicitly is also supported.
//
// The Authorization header is attached via declarativeNetRequest modifyHeaders on
// main_frame + fetch targets so a direct browser navigation to `{host}/ui`
// (bearer-gated on GET, see DataBank ADR-017) opens the dashboard without the
// token ever touching page JS storage.

/** Allowed corridor hosts (must match manifest host_permissions). */
export const ALLOWED_HOSTS = [
  "100.126.191.52:8787",
  "127.0.0.1:8787",
];

const RULE_ID = 1;
const RESOURCE_TYPES = ["main_frame", "xmlhttprequest", "fetch", "sub_frame"];

let token = ""; // in-memory only. Empty string == no rule installed.

/** Pure rule builder — unit-tested via node --test (no chrome needed). */
export function buildRules(bearerToken, host) {
  if (!bearerToken || !bearerToken.trim()) {
    const err = new Error("REFUSED: empty bearer token");
    err.name = "VaultRefused";
    throw err;
  }
  if (!ALLOWED_HOSTS.includes(host)) {
    const err = new Error(`REFUSED: host not in corridor allow-list: ${host}`);
    err.name = "VaultRefused";
    throw err;
  }
  return [
    {
      id: RULE_ID,
      priority: 1,
      action: {
        type: "modifyHeaders",
        requestHeaders: [
          { header: "Authorization", operation: "set", value: bearerToken.trim() },
        ],
      },
      condition: {
        urlFilter: `|*://${host}/*`,
        resourceTypes: RESOURCE_TYPES,
      },
    },
  ];
}

async function installRules(bearerToken, host) {
  const rules = buildRules(bearerToken, host);
  await chrome.declarativeNetRequest.updateDynamicRules({
    removeRuleIds: [RULE_ID],
    addRules: rules,
  });
  token = bearerToken.trim();
  return { ok: true, host };
}

function clearRules() {
  token = "";
  return chrome.declarativeNetRequest.updateDynamicRules({
    removeRuleIds: [RULE_ID],
    addRules: [],
  });
}

// The wiring below is Chrome-only. Guarding it lets the pure rule builder be
// imported and unit-tested under plain node (zero chrome stubs).
if (typeof chrome !== "undefined" && chrome.runtime) {
  chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
    (async () => {
      if (msg?.type === "ensure-token") {
        return installRules(String(msg.token ?? ""), String(msg.host ?? ""));
      }
      if (msg?.type === "clear-token") {
        await clearRules();
        return { ok: true };
      }
      throw new Error("REFUSED: unknown message type");
    })()
      .then(sendResponse)
      .catch((err) => sendResponse({ ok: false, error: err.message }));
    return true; // keep the messaging channel open for the async response
  });

  // Fail-closed safety on worker lifecycle restart: the in-memory token is gone
  // the moment the worker is evicted; re-arm nothing.
  if (token === "") {
    chrome.declarativeNetRequest.getDynamicRules().then((rules) => {
      // If a previous worker left rules behind (should be impossible), clear them
      // so no stale Authorization header survives a worker restart.
      const stale = rules.some((r) => r.id === RULE_ID);
      if (stale) return clearRules();
      return undefined;
    });
  }
}