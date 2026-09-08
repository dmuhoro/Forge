import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync, readdirSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

import { buildRules, ALLOWED_HOSTS } from "../background.js";

const here = dirname(fileURLToPath(import.meta.url));
const extRoot = join(here, "..");

test("buildRules emits exactly one Authorization modifyHeaders rule", () => {
  const rules = buildRules("deadbeef", ALLOWED_HOSTS[0]);
  assert.equal(rules.length, 1);
  const r = rules[0];
  assert.equal(r.action.type, "modifyHeaders");
  assert.equal(r.action.requestHeaders[0].header, "Authorization");
  assert.equal(r.action.requestHeaders[0].operation, "set");
  assert.equal(r.action.requestHeaders[0].value, "deadbeef");
  assert.ok(r.condition.urlFilter.includes(ALLOWED_HOSTS[0]));
  assert.ok(r.condition.resourceTypes.includes("main_frame"));
});

test("buildRules refuses empty token (fail-closed)", () => {
  assert.throws(() => buildRules("", ALLOWED_HOSTS[0]), /REFUSED/);
  assert.throws(() => buildRules("  ", ALLOWED_HOSTS[0]), /REFUSED/);
});

test("buildRules refuses hosts outside the corridor allow-list", () => {
  assert.throws(() => buildRules("x", "evil.example:8787"), /REFUSED/);
  assert.throws(() => buildRules("x", "100.126.191.52:9999"), /REFUSED/);
});

test("token value appears only in the Authorization header, never elsewhere", () => {
  const token = "s3cret-t0k3n";
  const rules = buildRules(token, ALLOWED_HOSTS[0]);
  for (const r of rules) {
    const dump = JSON.stringify(r);
    const occurrences = dump.split(token).length - 1;
    assert.equal(occurrences, 1, `token leaked ${occurrences - 1} extra place(s): ${dump}`);
  }
});

test("zero-residue guard: no storage API invocation anywhere in the extension JS", () => {
  const jsFiles = readdirSync(extRoot, { recursive: true })
    .filter((f) => f.endsWith(".js") || f.endsWith(".mjs"))
    .map((f) => join(extRoot, f));
  assert.ok(jsFiles.length >= 3, "expected background.js, popup.js, tests");
  // Invocation forms only — prose mentioning the APIs (in comments/docs) is fine.
  const forbidden = [
    /chrome\.storage\.(local|sync|session)\./,
    /localStorage\.(getItem|setItem|removeItem)\s*\(/,
    /sessionStorage\.(getItem|setItem|removeItem)\s*\(/,
    /document\.cookie\s*=/,
    /document\.cookie/,
  ];
  for (const f of jsFiles) {
    const src = readFileSync(f, "utf-8");
    for (const re of forbidden) {
      assert.ok(!re.test(src), `${join("extension", f.split(extRoot)[1])} must never use ${re}`);
    }
  }
});

test("manifest is MV3 and declares only corridor hosts", () => {
  const m = JSON.parse(readFileSync(join(extRoot, "manifest.json"), "utf-8"));
  assert.equal(m.manifest_version, 3);
  assert.ok(Array.isArray(m.host_permissions) && m.host_permissions.length > 0);
  assert.ok(!m.host_permissions.some((h) => h.includes("*://*")));
  assert.equal(m.background.type, "module");
});