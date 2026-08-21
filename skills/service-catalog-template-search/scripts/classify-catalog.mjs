#!/usr/bin/env node
// Deterministic catalog fetch-outcome classifier (authoring standard A9).
//
// Parsing the get-all-templates GET output — reading the HTTP status, telling
// 200 / 403 (FUNCTIONALITY_NOT_ENABLED) / 404 (NOT_FOUND) / empty apart, and
// extracting the template array — is a FIXED algorithm. Leaving it in prose
// invites inconsistent status handling and (worse) fabricating a catalog when
// the read failed. This script returns a structured outcome; the read-only
// skill runs only the GET and reports what this classifier says. It performs
// NO writes and NO self-heal (that is the deploy skill's job).
//
// Usage:
//   node classify-catalog.mjs <get-i-output.json>
//
// <get-i-output.json> is a FILE PATH holding the raw stdout of:
//   sf api request rest '.../service-process/get-all-templates' --method GET -i --target-org <alias>
//
// Prints { httpStatus, access, catalogFetched, outcome, count, templates } to
// stdout. `templates` is the parsed array (for ranking) on the 200 branch, [] otherwise.
// Exit 0 whenever the input was readable; exit 2 on bad args / unreadable input.

import { readFileSync, writeSync } from 'node:fs';

const [inputPath] = process.argv.slice(2);
if (!inputPath) {
  process.stderr.write('usage: node classify-catalog.mjs <get-i-output.json>\n');
  process.exit(2);
}

let raw;
try {
  raw = readFileSync(inputPath, 'utf8');
} catch {
  process.stderr.write(`classify-catalog: cannot read ${inputPath}\n`);
  process.exit(2);
}

const clean = raw.replace(/\x1b\[[0-9;]*m/g, '');
const statusMatch = clean.match(/^HTTP\/[\d.]+\s+(\d{3})/m);
const httpStatus = statusMatch ? parseInt(statusMatch[1], 10) : null;

function extractBody(text) {
  const idx = text.search(/^[[{]/m);
  return idx === -1 ? '' : text.slice(idx);
}

// The live catalog embeds raw control chars inside description strings, which
// spec-compliant JSON.parse rejects — escape bare control chars inside string
// literals before a fallback parse.
function sanitizeControlChars(text) {
  let out = '';
  let inString = false;
  let escaped = false;
  for (const ch of text) {
    const code = ch.charCodeAt(0);
    if (inString) {
      if (escaped) { out += ch; escaped = false; continue; }
      if (ch === '\\') { out += ch; escaped = true; continue; }
      if (ch === '"') { out += ch; inString = false; continue; }
      if (code < 0x20) { out += '\\u' + code.toString(16).padStart(4, '0'); continue; }
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
  if (!body) return null;
  try {
    return JSON.parse(body);
  } catch {
    try {
      return JSON.parse(sanitizeControlChars(body));
    } catch {
      return null;
    }
  }
}

function emit(obj) {
  // Synchronous write to fd 1 — a plain process.stdout.write() followed by
  // process.exit(0) truncates large payloads (the OK branch carries all ~144
  // templates, > 64KB) because exit races the async pipe drain.
  writeSync(1, JSON.stringify(obj, null, 2) + '\n');
  process.exit(0);
}

const isFunctionalityNotEnabled = /FUNCTIONALITY_NOT_ENABLED/.test(clean);
const isNotFound = /NOT_FOUND/.test(clean);
const parsed = parseBody(clean);

if (httpStatus === 403 || (httpStatus === null && isFunctionalityNotEnabled && !parsed)) {
  emit({
    httpStatus,
    access: false,
    catalogFetched: false,
    outcome: 'NO_ACCESS',
    count: 0,
    templates: [],
    note: 'Current user lacks Unified Catalog access (403 FUNCTIONALITY_NOT_ENABLED). Read-only skill: report the remediation (assign UnifiedCatalogAdminPsl + UnifiedCatalogAdmin) and stop. Do NOT fabricate a catalog.',
  });
}

if (httpStatus === 404 || (isNotFound && !parsed)) {
  emit({
    httpStatus,
    access: false,
    catalogFetched: false,
    outcome: 'ROUTE_UNAVAILABLE',
    count: 0,
    templates: [],
    note: 'Route below its minimum API version (needs v65.0+; this skill targets v67.0). Report and stop.',
  });
}

// ---- any other explicit non-200 status (401 / 429 / 500 / 502 / …) ----------
// A parseable JSON error body (Salesforce errors are `[{errorCode,message}]`)
// must NOT be reported as an empty catalog: an outage/auth/rate-limit failure is
// a real error, not "no templates exist". 403/404 are handled above; a null
// status (caller omitted -i) still falls through to body-shape detection.
if (httpStatus !== null && httpStatus !== 200) {
  emit({
    httpStatus,
    access: false,
    catalogFetched: false,
    outcome: 'UNAVAILABLE',
    count: 0,
    templates: [],
    note: `Catalog GET returned HTTP ${httpStatus} — an API, auth, or transport failure, not an empty catalog. Report the failure and stop; do not tell the user there are no templates.`,
  });
}

if (!parsed) {
  emit({
    httpStatus,
    access: httpStatus === 200,
    catalogFetched: false,
    outcome: 'UNPARSEABLE',
    count: 0,
    templates: [],
    note: 'Could not parse a catalog body from the GET output.',
  });
}

// ---- pull the template array from a catalog-SHAPED body ---------------------
// Accept only the canonical wrapper, the alternate wrapper, or a bare array whose
// entries look like templates (a string `name`). A parseable non-catalog body —
// e.g. an error array `[{errorCode,message}]` returned without a status line — is
// NOT catalog-shaped and must not be counted as templates or reported as empty.
const wrapperArray =
  (Array.isArray(parsed.serviceProcessTemplateOutputRepresentation) && parsed.serviceProcessTemplateOutputRepresentation) ||
  (Array.isArray(parsed.serviceProcessTemplates) && parsed.serviceProcessTemplates) ||
  null;
// Require length > 0: an EMPTY bare array vacuously passes `.every()`, so a
// null-status `[]` (caller omitted -i) would look catalog-shaped and be reported
// as EMPTY — a definitive "no templates" — when the read may have failed. A
// genuinely-empty 200 catalog still reaches EMPTY below via the httpStatus===200
// path; only the unconfirmed null-status `[]` is downgraded to UNPARSEABLE.
const bareCatalog =
  Array.isArray(parsed) && parsed.length > 0 && parsed.every((t) => t && typeof t === 'object' && typeof t.name === 'string')
    ? parsed
    : null;
const catalogShaped = wrapperArray !== null || bareCatalog !== null;

// Parseable, but neither a 200 nor a catalog-shaped body (only reachable when the
// caller omitted -i so httpStatus is null): treat as unparseable/failed, not empty.
if (!catalogShaped && httpStatus !== 200) {
  emit({
    httpStatus,
    access: false,
    catalogFetched: false,
    outcome: 'UNPARSEABLE',
    count: 0,
    templates: [],
    note: 'The GET body is not a recognizable catalog response (and carried no HTTP 200 status) — report the failure and stop; do not report an empty catalog.',
  });
}

const templates = wrapperArray || bareCatalog || [];

if (templates.length === 0) {
  emit({
    httpStatus: httpStatus ?? 200,
    access: true,
    catalogFetched: true,
    outcome: 'EMPTY',
    count: 0,
    templates: [],
    note: 'Catalog returned an empty array — report that no templates are available. Do NOT invent any.',
  });
}

emit({
  httpStatus: httpStatus ?? 200,
  access: true,
  catalogFetched: true,
  outcome: 'OK',
  count: templates.length,
  templates,
  note: 'Rank these templates against the business need using name/description/scopeAndUseCases/whatIsIncluded. Never rank over remembered templates.',
});
