#!/usr/bin/env node
// Injection-safe activate-and-verify helper (authoring standards: Agent Safety + A9).
//
// SECURITY (the BLOCKER this script exists to fix): the Service Process name is
// USER-SUPPLIED. It must never be interpolated into a double-quoted Bash command
// or a single-quoted SOQL literal — a name containing shell metacharacters or a
// stray quote could execute during command construction or alter the query and
// touch an unintended Product2. This script:
//   1. accepts the name as an argv ARGUMENT (no shell interpolation ever), and
//   2. invokes `sf` via execFileSync with an ARGUMENT ARRAY (shell:false), and
//   3. escapes the name for the SOQL string literal before embedding it.
//
// A9: the resolve-Id → conditional-activate → re-read sequence is a fixed
// multi-command operation with query parsing and conditional DML; encoding it
// here keeps it deterministic instead of relying on model interpretation.
//
// Usage:
//   node activate-verify.mjs <serviceProcessName> [--target-org <alias>] [--no-activate]
//
// --no-activate : verify only (use when the user asked to leave it inactive).
//
// Prints a JSON result: { found, id, isActive, activated, verified }.
// Exit 0 when the operation completed (found or honestly not-found); exit 2 on
// bad args; exit 1 only when an sf call errors unexpectedly.

import { execFileSync } from 'node:child_process';

const argv = process.argv.slice(2);
const noActivate = argv.includes('--no-activate');
const orgIdx = argv.indexOf('--target-org');
const targetOrg = orgIdx !== -1 ? argv[orgIdx + 1] : null;
// Positional name = first non-flag token that is NOT the --target-org value.
// Excluding the alias slot stops a flags-first call
// (`--target-org myOrg "My Template"`) from mistaking the alias for the name.
// Guard on orgIdx !== -1: when --target-org is absent, orgIdx is -1 and a bare
// `orgIdx + 1` would be 0 and wrongly exclude a name sitting at argv[0]. Setting
// the exclude slot to -1 in that case means it matches no real index.
const aliasIdx = orgIdx === -1 ? -1 : orgIdx + 1;
const name = argv.find((a, i) => !a.startsWith('--') && i !== aliasIdx);

if (!name) {
  process.stderr.write('usage: node activate-verify.mjs <serviceProcessName> [--target-org <alias>] [--no-activate]\n');
  process.exit(2);
}

// Escape a value for embedding inside a single-quoted SOQL string literal.
// SOQL uses backslash escaping: backslash and single-quote must be escaped.
// (Reject any residual control chars defensively.)
function soqlLiteral(value) {
  return value.replace(/\\/g, '\\\\').replace(/'/g, "\\'").replace(/[\n\r\t]/g, ' ');
}

// Run `sf` with an argument ARRAY — no shell, so nothing in `name` can be
// interpreted as a shell token. Returns parsed --json stdout.
function sf(args) {
  const full = targetOrg ? [...args, '--target-org', targetOrg] : args;
  try {
    const out = execFileSync('sf', full, { encoding: 'utf8', maxBuffer: 20 * 1024 * 1024 });
    return { ok: true, json: JSON.parse(out) };
  } catch (err) {
    // sf exits non-zero on query/DML errors; stdout may still hold --json.
    const stdout = err.stdout ? String(err.stdout) : '';
    try {
      return { ok: false, json: JSON.parse(stdout) };
    } catch {
      return { ok: false, json: null, raw: stdout || String(err.message) };
    }
  }
}

const literal = soqlLiteral(name);
const findQuery =
  `SELECT Id, Name, IsActive FROM Product2 ` +
  `WHERE Name='${literal}' AND UsedFor='ServiceProcess' ` +
  `ORDER BY CreatedDate DESC LIMIT 1`;

// ---- 1. resolve the deployed Product2 by name (no shell; name is a query arg)
const found = sf(['data', 'query', '--query', findQuery, '--json']);

// A failed CLI query (auth/transport/malformed) must NOT be reported as a
// verified absence — `found:false` would be indistinguishable from a real
// not-found and could let a caller conclude the deploy silently vanished.
// Surface the error and exit non-zero so the caller treats it as a check failure.
if (!found.ok) {
  const detail =
    found.json?.message ||
    found.json?.[0]?.message ||
    found.raw ||
    'sf data query failed';
  process.stderr.write(`activate-verify: initial Product2 lookup failed — ${detail}\n`);
  process.stdout.write(
    JSON.stringify({
      error: true,
      found: null,
      id: null,
      isActive: null,
      activated: false,
      verified: false,
      detail: String(detail),
    }) + '\n',
  );
  process.exit(1);
}

const rec = found.json?.result?.records?.[0];

if (!rec) {
  process.stdout.write(
    JSON.stringify({ found: false, id: null, isActive: null, activated: false, verified: false }) + '\n',
  );
  process.exit(0);
}

let activated = false;

// ---- 2. activate (conditional) — only if not already active and allowed ----
if (!noActivate && rec.IsActive !== true) {
  const upd = sf(['data', 'update', 'record', '--sobject', 'Product2', '--record-id', rec.Id, '--values', 'IsActive=true', '--json']);
  activated = upd.ok;
}

// ---- 3. verify by re-reading -----------------------------------------------
const verifyRes = sf(['data', 'query', '--query', findQuery, '--json']);

// Symmetric to the initial-lookup guard above: a failed verification re-read
// (auth/transport/malformed) must NOT collapse to verified:false — that is
// indistinguishable from a genuine "record absent after activate" and could
// mask a deploy that actually landed. Surface the check error and exit non-zero.
// `activated` still reflects what the DML step reported.
if (!verifyRes.ok) {
  const detail =
    verifyRes.json?.message ||
    verifyRes.json?.[0]?.message ||
    verifyRes.raw ||
    'sf data query failed';
  process.stderr.write(`activate-verify: verification re-read failed — ${detail}\n`);
  process.stdout.write(
    JSON.stringify({
      error: true,
      found: true,
      id: rec.Id,
      isActive: null,
      activated,
      verified: false,
      detail: String(detail),
    }) + '\n',
  );
  process.exit(1);
}

const verifyRec = verifyRes.json?.result?.records?.[0];
const isActive = verifyRec?.IsActive === true;
const verified = Boolean(verifyRec) && (noActivate || isActive);

process.stdout.write(
  JSON.stringify({
    found: true,
    id: verifyRec?.Id ?? rec.Id,
    isActive,
    activated,
    verified,
  }) + '\n',
);
process.exit(0);
