#!/usr/bin/env node
// Deterministic catalog-probe + name-resolution classifier (authoring standard A9).
//
// The access probe, HTTP-status parsing, self-heal decision, and the
// case-insensitive name→template resolution are a FIXED algorithm — parsing an
// HTTP status line, branching on 200/403/404/empty, and counting name matches
// must not be left to the model to eyeball in prose. This script encodes all of
// it; the skill's Bash steps only run the network calls its output dictates
// (the GET probe, and — on SELF_HEAL — the permset assigns), so every write
// stays visible in the trace.
//
// Usage:
//   node resolve-template.mjs <get-i-output.json> [requestedName]
//
// <get-i-output.json> is a FILE PATH holding the raw stdout of:
//   sf api request rest '.../service-process/get-all-templates' --method GET -i --target-org <alias>
// i.e. an HTTP status line, headers, a blank line, then the raw Connect body.
// [requestedName] is the template name the user asked to deploy (optional; when
// omitted the script only classifies access and does not resolve a match).
//
// Prints a structured outcome object to stdout. Exit code is 0 whenever the
// input was readable (a 403/404/empty catalog is a RECORDED outcome, not a
// script failure); exit 2 only on bad arguments / unreadable input.

import { readFileSync, writeSync } from 'node:fs';

const [inputPath, requestedName] = process.argv.slice(2);
if (!inputPath) {
  process.stderr.write('usage: node resolve-template.mjs <get-i-output.json> [requestedName]\n');
  process.exit(2);
}

let rawOutput;
try {
  rawOutput = readFileSync(inputPath, 'utf8');
} catch {
  process.stderr.write(`resolve-template: cannot read ${inputPath}\n`);
  process.exit(2);
}

// ---- strip ANSI color codes the CLI adds to header lines --------------------
const clean = rawOutput.replace(/\x1b\[[0-9;]*m/g, '');

// ---- read the HTTP status from the first status line (may be absent if the --
// ---- caller forgot -i; then we fall back to body-shape detection) -----------
const statusMatch = clean.match(/^HTTP\/[\d.]+\s+(\d{3})/m);
const httpStatus = statusMatch ? parseInt(statusMatch[1], 10) : null;

// ---- slice the JSON body: from the first line that begins with { or [ --------
function extractBody(text) {
  const idx = text.search(/^[[{]/m);
  return idx === -1 ? '' : text.slice(idx);
}

// ---- control-char–safe JSON parse: the live catalog embeds raw newlines/tabs -
// ---- inside description strings, which spec-compliant JSON.parse rejects.  ---
// ---- Walk the text; while inside a string literal, escape any bare control  -
// ---- char (< 0x20) to its \uXXXX form. (Python needed strict=False here.)   -
function sanitizeControlChars(text) {
  let out = '';
  let inString = false;
  let escaped = false;
  for (const ch of text) {
    const code = ch.charCodeAt(0);
    if (inString) {
      if (escaped) {
        out += ch;
        escaped = false;
        continue;
      }
      if (ch === '\\') {
        out += ch;
        escaped = true;
        continue;
      }
      if (ch === '"') {
        out += ch;
        inString = false;
        continue;
      }
      if (code < 0x20) {
        out += '\\u' + code.toString(16).padStart(4, '0');
        continue;
      }
      out += ch;
    } else {
      if (ch === '"') inString = true;
      out += ch;
    }
  }
  return out;
}

function parseBody(text) {
  const body = extractBody(text);
  if (!body) return { ok: false, data: null };
  try {
    return { ok: true, data: JSON.parse(body) };
  } catch {
    try {
      return { ok: true, data: JSON.parse(sanitizeControlChars(body)) };
    } catch {
      return { ok: false, data: null };
    }
  }
}

const parsed = parseBody(clean);

// ---- detect the 403 self-heal signature and 404 route-missing --------------
const bodyText = clean;
const isFunctionalityNotEnabled = /FUNCTIONALITY_NOT_ENABLED/.test(bodyText);
const isNotFound = /NOT_FOUND/.test(bodyText);

function emit(obj) {
  // Synchronous write to fd 1 — process.stdout.write() + process.exit(0) can
  // truncate a large payload (availableNames on a big catalog) because exit
  // races the async pipe drain.
  writeSync(1, JSON.stringify(obj, null, 2) + '\n');
  process.exit(0);
}

// ---- classify -------------------------------------------------------------
// 403 (explicit) OR a FUNCTIONALITY_NOT_ENABLED body with no 200 status.
if (httpStatus === 403 || (httpStatus === null && isFunctionalityNotEnabled && !parsed.ok)) {
  emit({
    httpStatus,
    access: false,
    catalogFetched: false,
    action: 'SELF_HEAL',
    recommendedOutcome: 'STOPPED_NO_ACCESS',
    matchCount: null,
    resolved: null,
    availableNames: [],
    note: '403 FUNCTIONALITY_NOT_ENABLED — assign UnifiedCatalogAdminPsl + UnifiedCatalogAdmin, then re-probe once. If still 403 after the heal, the org lacks the license (STOPPED_NO_ACCESS).',
  });
}

if (httpStatus === 404 || (isNotFound && !parsed.ok)) {
  emit({
    httpStatus,
    access: false,
    catalogFetched: false,
    action: 'STOP_ROUTE',
    recommendedOutcome: 'STOPPED_OTHER',
    matchCount: null,
    resolved: null,
    availableNames: [],
    note: 'Route is below its minimum API version (needs v65.0+; this skill targets v67.0).',
  });
}

// ---- any other explicit non-200 status (401 / 429 / 500 / 502 / …) ----------
// A parseable JSON error body (Salesforce errors are `[{errorCode,message}]`)
// must NOT be mistaken for an empty or missing catalog: an outage/auth/rate-limit
// failure is a real error, not "no such template". 403/404 are handled above; a
// null status (caller omitted -i) still falls through to body-shape detection.
if (httpStatus !== null && httpStatus !== 200) {
  emit({
    httpStatus,
    access: false,
    catalogFetched: false,
    action: 'STOP_OTHER',
    recommendedOutcome: 'STOPPED_OTHER',
    matchCount: null,
    resolved: null,
    availableNames: [],
    note: `Catalog GET returned HTTP ${httpStatus} — an API, auth, or transport failure, not an empty or missing catalog. Report the failure and stop; do not treat it as name-not-found.`,
  });
}

if (!parsed.ok) {
  emit({
    httpStatus,
    access: httpStatus === 200,
    catalogFetched: false,
    action: 'STOP_OTHER',
    recommendedOutcome: 'STOPPED_OTHER',
    matchCount: null,
    resolved: null,
    availableNames: [],
    note: 'Could not parse a catalog body from the GET output.',
  });
}

// ---- pull the template array from a catalog-SHAPED body ---------------------
// Accept only the canonical wrapper, the alternate wrapper, or a bare array whose
// entries look like templates (a string `name`). A parseable non-catalog body —
// e.g. an error array `[{errorCode,message}]` returned without a status line — is
// NOT catalog-shaped and must not be read as templates.
const wrapperArray =
  (Array.isArray(parsed.data?.serviceProcessTemplateOutputRepresentation) && parsed.data.serviceProcessTemplateOutputRepresentation) ||
  (Array.isArray(parsed.data?.serviceProcessTemplates) && parsed.data.serviceProcessTemplates) ||
  null;
// Require length > 0: an EMPTY bare array vacuously passes `.every()`, so a
// null-status `[]` (caller omitted -i) would look catalog-shaped and fall through
// to STOP_EMPTY / STOPPED_NAME_NOT_FOUND — a definitive "no such template" — when
// the read may have failed. A genuinely-empty 200 catalog still reaches STOP_EMPTY
// below via the httpStatus===200 path; only the unconfirmed null-status `[]` is
// downgraded to the failed-read STOP_OTHER.
const bareCatalog =
  Array.isArray(parsed.data) && parsed.data.length > 0 && parsed.data.every((t) => t && typeof t === 'object' && typeof t.name === 'string')
    ? parsed.data
    : null;
const catalogShaped = wrapperArray !== null || bareCatalog !== null;

// Parseable, but neither a 200 nor a catalog-shaped body (only reachable when the
// caller omitted -i so httpStatus is null): treat as a failed/unknown response,
// not an empty catalog.
if (!catalogShaped && httpStatus !== 200) {
  emit({
    httpStatus,
    access: false,
    catalogFetched: false,
    action: 'STOP_OTHER',
    recommendedOutcome: 'STOPPED_OTHER',
    matchCount: null,
    resolved: null,
    availableNames: [],
    note: 'The GET body is not a recognizable catalog response (and carried no HTTP 200 status) — report the failure and stop; do not treat it as an empty catalog.',
  });
}

const templates = wrapperArray || bareCatalog || [];
const availableNames = templates.map((t) => t?.name).filter((n) => typeof n === 'string');

if (templates.length === 0) {
  emit({
    httpStatus: httpStatus ?? 200,
    access: true,
    catalogFetched: true,
    action: 'STOP_EMPTY',
    recommendedOutcome: 'STOPPED_NAME_NOT_FOUND',
    matchCount: 0,
    resolved: null,
    availableNames: [],
    note: 'Catalog returned an empty array — nothing to deploy.',
  });
}

// No requested name — or a purely-whitespace one, which carries no name to
// resolve — → access confirmed, resolution deferred to the caller. The
// whitespace guard is load-bearing: without it a name like " " trims to ""
// below, and `String.includes("")` is true for every template, so `partial`
// would become the entire catalog and emit a bogus STOP_AMBIGUOUS.
if (!requestedName || !requestedName.trim()) {
  emit({
    httpStatus: httpStatus ?? 200,
    access: true,
    catalogFetched: true,
    action: 'CONTINUE',
    recommendedOutcome: null,
    matchCount: null,
    resolved: null,
    availableNames,
    note: 'Access confirmed. Re-run with a requestedName to resolve a specific template.',
  });
}

// ---- case-insensitive exact-name match -------------------------------------
const wanted = requestedName.trim().toLowerCase();
const matches = templates.filter((t) => (t?.name ?? '').trim().toLowerCase() === wanted);

if (matches.length === 1) {
  const m = matches[0];
  emit({
    httpStatus: httpStatus ?? 200,
    access: true,
    catalogFetched: true,
    action: 'DEPLOY',
    recommendedOutcome: null,
    matchCount: 1,
    resolved: {
      id: m.id,
      name: m.name,
      templateDependencyMetadata: m.templateDependencyMetadata ?? [],
    },
    availableNames,
    note: 'Exactly one match — proceed to build the deploy body from templateDependencyMetadata.',
  });
}

if (matches.length >= 2) {
  emit({
    httpStatus: httpStatus ?? 200,
    access: true,
    catalogFetched: true,
    action: 'STOP_AMBIGUOUS',
    recommendedOutcome: 'STOPPED_NAME_AMBIGUOUS',
    matchCount: matches.length,
    resolved: null,
    availableNames: matches.map((t) => t.name),
    note: 'Two or more exact matches — stop and ask the user to pick the exact one. Never pick the first.',
  });
}

// ---- zero exact matches: fall back to substring candidates ------------------
// A request can be a CATEGORY term ("access", "laptop") rather than a template
// name. If it appears inside two or more template names, the request is
// AMBIGUOUS, not simply not-found — the same "stop, list the candidates, ask for
// the exact one, never pick one" contract as a multi-exact tie. Only a term that
// matches zero (or a single near-match) template names is genuinely NOT_FOUND;
// a lone near-match is still never auto-deployed. matchCount carries the
// candidate count so the caller's STOPPED_NAME_AMBIGUOUS (>=2) stays coherent.
const partial = availableNames.filter((n) => n.toLowerCase().includes(wanted));

if (partial.length >= 2) {
  emit({
    httpStatus: httpStatus ?? 200,
    access: true,
    catalogFetched: true,
    action: 'STOP_AMBIGUOUS',
    recommendedOutcome: 'STOPPED_NAME_AMBIGUOUS',
    matchCount: partial.length,
    resolved: null,
    availableNames: partial,
    note: 'No exact match, but the requested term appears in two or more template names — the request is ambiguous. List these candidates and ask the user for the exact name. Never pick one.',
  });
}

emit({
  httpStatus: httpStatus ?? 200,
  access: true,
  catalogFetched: true,
  action: 'STOP_NOT_FOUND',
  recommendedOutcome: 'STOPPED_NAME_NOT_FOUND',
  matchCount: 0,
  resolved: null,
  availableNames: partial.length ? partial : availableNames,
  note: 'No exact match (and not enough near-matches to be ambiguous) — stop, report the requested name, and list available names. Never deploy a near-match.',
});
