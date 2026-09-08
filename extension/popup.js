// Forge Corridor popup — forwards the token to the service worker (in-memory),
// never reads it back, never touches extension storage.

const hostInput = document.getElementById("host");
const tokenInput = document.getElementById("token");
const statusEl = document.getElementById("status");
const openBtn = document.getElementById("open");
const clearBtn = document.getElementById("clear");

function status(text, isErr = false) {
  statusEl.textContent = text;
  statusEl.classList.toggle("err", isErr);
}

openBtn.addEventListener("click", async () => {
  status("validating…");
  const host = (hostInput.value || "").trim();
  const token = tokenInput.value || "";
  if (!host || !token) {
    status("REFUSED: host and token are required", true);
    return;
  }
  const resp = await chrome.runtime.sendMessage({ type: "ensure-token", token, host });
  if (!resp?.ok) {
    status(`REFUSED: ${resp?.error ?? "unknown"}`, true);
    return;
  }
  status("token armed in RAM — opening /ui…");
  const url = /^https?:\/\//.test(host) ? host : `http://${host}`;
  await chrome.tabs.create({ url: `${url.replace(/\/$/, "")}/ui` });
});

clearBtn.addEventListener("click", async () => {
  const resp = await chrome.runtime.sendMessage({ type: "clear-token" });
  if (resp?.ok) status("token cleared; header rule removed");
  else status(`REFUSED: ${resp?.error ?? "unknown"}`, true);
  tokenInput.value = "";
});