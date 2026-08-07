#!/usr/bin/env node
// Locally sanity-check an SFAP JWT *before* any network call, so a bad token
// fails fast with a clear reason instead of a bare HTTP 401 deep in the poll
// loop. This does NOT verify the signature (only the server can) — it decodes
// the freely-readable header/body claims to catch the two things that cause
// almost every 401: missing sfap_api scope, or expired.
//
// The token's environment (prod/stage/dev) is detected from its tnk claim and
// reported as detectedEnv so the caller can route to the matching endpoint.
//
// The token is read from STDIN (never argv) so it does not leak into the
// process list. Usage:
//   printf '%s' "$JWT" | node validate-token.js [--now <epoch>]
//
// Output (stdout, single-line JSON):
//   pass:  {"ok":true,"tnk":"...","detectedEnv":"prod|stage|dev|null","expiresInSeconds":N,"warnings":[...]}
//   fail:  {"ok":false,"error":"...","hint":"..."}  (exit 1)
// A "fail" only happens for things we can PROVE wrong (expired / missing scope).
// Anything we cannot read is a warning, not a block.

function out(obj, code) {
  console.log(JSON.stringify(obj));
  process.exit(code);
}

const args = process.argv.slice(2);
let now = Math.floor(Date.now() / 1000);
for (let i = 0; i < args.length; i++) {
  if (args[i] === "--now") now = parseInt(args[++i], 10) || now;
}

// Read the token from stdin (keeps it out of argv / process list).
let token = "";
try {
  token = require("fs").readFileSync(0, "utf8").trim();
} catch {
  token = "";
}
if (!token) out({ ok: false, error: "no token on stdin", hint: "resolve the token before validating" }, 1);

// A JWT is header.body.signature, each a base64url-encoded chunk.
function decodeSegment(seg) {
  const b64 = seg.replace(/-/g, "+").replace(/_/g, "/");
  const pad = b64 + "=".repeat((4 - (b64.length % 4)) % 4);
  return JSON.parse(Buffer.from(pad, "base64").toString("utf8"));
}

const parts = token.split(".");
if (parts.length < 2) {
  // Not a JWT we can read — don't block (token may be an opaque format).
  out({ ok: true, tnk: null, detectedEnv: null, expiresInSeconds: null, warnings: ["token is not a readable JWT — skipping local checks"] }, 0);
}

let header, body;
try {
  header = decodeSegment(parts[0]);
  body = decodeSegment(parts[1]);
} catch {
  out({ ok: true, tnk: null, detectedEnv: null, expiresInSeconds: null, warnings: ["could not decode JWT claims — skipping local checks"] }, 0);
}

const warnings = [];

// --- 1. tnk / environment. Per the SFAP contract, tnk lives on the HEADER and
// looks like core/<instance>/<orgId> (e.g. core/prod/00D..., core/stagecomstg2/...,
// core/falcondeva/...). The environment marker lives ONLY in the <instance>
// segment — the trailing <orgId> (00D...) is an opaque id that must NOT be
// scanned for substrings, or a prod org whose id happens to contain "dev"/"stg"
// would be wrongly rejected. So we match markers against the instance segment
// and the iss host only, never the whole claim string. The detected env is
// reported (not rejected) so the caller can route to the matching endpoint. ---
const tnk = header.tnk || body.tnk || null;
const iss = body.iss || "";
// tnk instance segment = the middle of core/<instance>/<orgId>; fall back to the
// whole tnk only if it isn't in that 3-part shape.
const tnkParts = tnk ? String(tnk).split("/") : [];
const tnkInstance = tnkParts.length >= 3 ? tnkParts[1] : tnk || "";
// iss host (strip scheme/path) so we match the host label, not a full URL.
const issHost = String(iss).replace(/^https?:\/\//, "").split(/[/?#]/)[0];
const envHay = `${tnkInstance} ${issHost}`.toLowerCase();
const looksDev = /falcondeva|falcondev|falcontest|deva|(^|[^a-z])dev([^a-z]|$)/.test(envHay);
const looksStage = /stg|stage/.test(envHay);
// Env inferred from the token's own claims (null when we can't tell). Production
// instances carry no stg/dev marker, so a readable tnk with neither signal is prod.
const detectedEnv = looksStage && !looksDev
  ? "stage"
  : looksDev && !looksStage
  ? "dev"
  : tnk && !looksStage && !looksDev
  ? "prod"
  : null;

if (!tnk) warnings.push("no tnk claim found — could not detect the token's environment; defaulting to prod endpoint");

// --- 2. scope must include sfap_api. Scope may be a space-delimited string
// (scp/scope) or an array. Only fail if we can read it AND sfap_api is absent. ---
const scopeRaw = body.scp ?? body.scope ?? null;
if (scopeRaw != null) {
  const scopes = Array.isArray(scopeRaw) ? scopeRaw : String(scopeRaw).split(/\s+/);
  if (!scopes.includes("sfap_api")) {
    out({ ok: false, error: "token scope does not include sfap_api",
          hint: "Re-mint the token with the sfap_api scope. See references/authentication.md." }, 1);
  }
} else {
  warnings.push("no scope claim found — could not confirm sfap_api scope");
}

// --- 3. expiry. exp is epoch seconds. Fail if already past. ---
let expiresInSeconds = null;
if (typeof body.exp === "number") {
  expiresInSeconds = body.exp - now;
  if (expiresInSeconds <= 0) {
    out({ ok: false, error: `token expired ${Math.abs(expiresInSeconds)}s ago`,
          hint: "Re-mint a fresh SFAP token and retry." }, 1);
  }
  if (expiresInSeconds < 60) warnings.push(`token expires in ${expiresInSeconds}s — it may lapse mid-scan`);
} else {
  warnings.push("no exp claim found — could not confirm the token is unexpired");
}

out({ ok: true, tnk, detectedEnv, expiresInSeconds, warnings }, 0);
