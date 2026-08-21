#!/usr/bin/env node
// Deterministic readiness classifier for the Agentforce for IT Service prerequisite check.
//
// Consumes the raw JSON body of a single `sf api request rest` read of the
// Salesforce Go feature-status endpoint and, for a chosen agent path
// (fulfiller | employee), decides whether every required feature toggle is ON.
// This is the deterministic decision table that MUST NOT be interpreted by the
// model in prose (authoring standard A9).
//
// Usage:
//   node classify-readiness.mjs <features-status.json> <agentType> [exitStatus]
//
// <features-status.json> is a FILE PATH to the raw stdout captured from:
//   sf api request rest "/services/data/vXX.0/connect/setup/discovery/features/status" \
//     --method POST --body '{"featureApiNames":[...]}' --target-org <org> > file.json
// The body shape is { items: [ { apiName, status, enableBlockedReasons[],
// dependencyStatuses[] } ] } where status is "ENABLED" | "NOT_ENABLED".
// The file may instead hold the CLI error payload (a JSON array like
// [{"errorCode":"NOT_FOUND",...}]) or be empty when the CLI exited non-zero.
//
// <exitStatus> is the OPTIONAL numeric exit code of the `sf` command ($? in the
// shell). Pass it so the classifier can tell a *confirmed* 404-style "gate not
// wired" (→ CANNOT-CONFIRM) apart from an auth / permission / transport failure
// (→ ERROR, surface the raw response and stop). An empty or unparseable body is
// treated as ERROR, never CANNOT-CONFIRM.
//
// <agentType> is one of: fulfiller | employee. It selects which feature toggles
// are required — fulfiller checks the fulfiller template pref, employee checks
// the requestor + specialized-employee template prefs. Both paths also require
// the shared Agentforce Studio pref and the ITSM parent umbrella.
//
// Emits a single JSON object to stdout:
//   { agentType, readState,
//     features: { <apiName>: { status, signal, enableBlockedReasons, enableable, enableRoute } },
//     verdict, notEnabled: [<apiName>...], enableable: [<apiName>...], reasons: [...], rawError }
// where each signal is PASS | FAIL | CANNOT-CONFIRM | ERROR and verdict is
// READY | NOT-READY | CANNOT-CONFIRM | ERROR. Exit code is always 0 on a usable
// agentType; the verdict is carried in the payload, not the exit status.

import { readFileSync } from 'node:fs';

// Required feature toggles per agent path. The apiNames are the real Salesforce
// Go featureApiNames behind the "Agentforce for IT Service" page toggles.
const STUDIO = 'sales-cloud-agent-studio';                 // "Turn on Agentforce Studio"
const PARENT = 'service-cloud-agentforce-for-itsm';        // "Agentforce for IT Service" umbrella
const FULFILLER = 'service-cloud-it-fulfiller-agent';      // "IT Service Fulfiller"
const REQUESTOR = 'service-cloud-requestor-agent';         // "IT Service Employee"
const SPECIALIZED = 'service-cloud-it-service-employee-agent'; // "Specialized Agent Templates for Employee"

const REQUIRED = {
  fulfiller: [STUDIO, PARENT, FULFILLER],
  employee: [STUDIO, PARENT, REQUESTOR, SPECIALIZED],
};

const LABEL = {
  [STUDIO]: 'Agentforce Studio',
  [PARENT]: 'Agentforce for IT Service (parent)',
  [FULFILLER]: 'IT Service Fulfiller template',
  [REQUESTOR]: 'IT Service Employee template',
  [SPECIALIZED]: 'Specialized Agent Templates for Employee',
};

function enableRoute(apiName) {
  return `POST /connect/setup/discovery/feature/${apiName}/enable`;
}

function readJson(path) {
  // { ok:true, data } on a parseable body; { ok:false, empty:true } when the file
  // is missing/empty; { ok:false, empty:false } when it holds non-JSON garbage.
  try {
    const text = readFileSync(path, 'utf8').trim();
    if (!text) return { ok: false, empty: true };
    return { ok: true, data: JSON.parse(text) };
  } catch {
    return { ok: false, empty: false };
  }
}

function asErrorArray(data) {
  // sf api request rest surfaces Connect API errors as an array of
  // {errorCode,message} (or a single such object). Returns [] if not an error body.
  if (Array.isArray(data)) return data.filter((e) => e && (e.errorCode || e.message));
  if (data && (data.errorCode || data.message)) return [data];
  return [];
}

function isNotFoundError(errs) {
  // A 404 / NOT_FOUND / gate-not-wired is the ONLY error shape that maps to
  // "cannot confirm". Auth (401), permission (403), and everything else = ERROR.
  return errs.some((e) => {
    const code = String(e?.errorCode ?? '').toUpperCase();
    const msg = String(e?.message ?? '').toUpperCase();
    return code.includes('NOT_FOUND') || code.includes('NOT_EXIST') ||
      msg.includes('NOT FOUND') || msg.includes('DOES NOT EXIST') ||
      msg.includes('COULD NOT BE FOUND');
  });
}

function errorSnippet(errs) {
  return errs.map((e) => `${e.errorCode ?? 'ERROR'}: ${e.message ?? ''}`.trim()).join(' | ').slice(0, 500);
}

// Returns { readState, statusMap, rawError }:
//   readState 'ok'        → statusMap has per-apiName { status, enableBlockedReasons }
//   readState 'not-wired' → a confirmed 404 (feature-discovery surface not wired)
//   readState 'error'     → empty / auth / permission / transport / unexpected body
function readFeatureStatus(res, exitStatus) {
  if (!res.ok) {
    // Empty or non-JSON body. Never a confirmed 404 → ERROR (surface it, stop).
    const why = res.empty
      ? (Number.isFinite(exitStatus) && exitStatus !== 0
          ? `The read command exited ${exitStatus} with an empty body (auth / permission / transport failure).`
          : 'The read produced an empty body — the response could not be read.')
      : 'The read produced a non-JSON body that could not be parsed.';
    return { readState: 'error', statusMap: null, rawError: why };
  }
  const d = res.data;
  const errs = asErrorArray(d);
  if (errs.length) {
    if (isNotFoundError(errs)) return { readState: 'not-wired', statusMap: null, rawError: null };
    return { readState: 'error', statusMap: null, rawError: errorSnippet(errs) };
  }
  const items = Array.isArray(d?.items) ? d.items : null;
  if (!items) {
    return { readState: 'error', statusMap: null, rawError: 'The response had no "items" array (unexpected shape).' };
  }
  const map = new Map();
  for (const it of items) {
    if (it?.apiName) {
      map.set(it.apiName, {
        status: String(it.status ?? '').toUpperCase(),
        enableBlockedReasons: Array.isArray(it.enableBlockedReasons) ? it.enableBlockedReasons : [],
      });
    }
  }
  return { readState: 'ok', statusMap: map, rawError: null };
}

function classifyFeature(apiName, statusMap) {
  const label = LABEL[apiName] ?? apiName;
  if (!statusMap || !statusMap.has(apiName)) {
    return {
      status: 'UNKNOWN', signal: 'CANNOT-CONFIRM', enableBlockedReasons: [], enableable: false, enableRoute: null,
      reason: `${label} (${apiName}) — no status returned (endpoint not wired / not in response).`,
    };
  }
  const { status, enableBlockedReasons } = statusMap.get(apiName);
  if (status === 'ENABLED') {
    return { status, signal: 'PASS', enableBlockedReasons: [], enableable: false, enableRoute: null, reason: `${label} (${apiName}) → ENABLED.` };
  }
  if (status === 'NOT_ENABLED') {
    const blocked = enableBlockedReasons.length > 0;
    return {
      status, signal: 'FAIL', enableBlockedReasons,
      enableable: !blocked,
      enableRoute: blocked ? null : enableRoute(apiName),
      reason: blocked
        ? `${label} (${apiName}) → NOT_ENABLED, but blocked: ${enableBlockedReasons.map((r) => (typeof r === 'string' ? r : (r?.message ?? JSON.stringify(r)))).join('; ')}.`
        : `${label} (${apiName}) → NOT_ENABLED (enableable).`,
    };
  }
  return {
    status, signal: 'CANNOT-CONFIRM', enableBlockedReasons: [], enableable: false, enableRoute: null,
    reason: `${label} (${apiName}) → unexpected status "${status}".`,
  };
}

const [statusPath, rawAgentType, rawExit] = process.argv.slice(2);
const agentType = String(rawAgentType ?? '').toLowerCase();
if (!statusPath || !REQUIRED[agentType]) {
  process.stderr.write('usage: node classify-readiness.mjs <features-status.json> <fulfiller|employee> [exitStatus]\n');
  process.exit(2);
}
const exitStatus = rawExit === undefined ? NaN : Number(rawExit);

const { readState, statusMap, rawError } = readFeatureStatus(readJson(statusPath), exitStatus);

const features = {};
const reasons = [];
const notEnabled = [];
const enableable = [];

if (readState === 'error') {
  // Hard read failure (auth / permission / transport / unexpected). Do NOT
  // pretend the gate is merely un-wired — surface it and stop.
  for (const apiName of REQUIRED[agentType]) {
    features[apiName] = { status: 'UNKNOWN', signal: 'ERROR', enableBlockedReasons: [], enableable: false, enableRoute: null };
  }
  reasons.push(`Feature status could not be read: ${rawError} Surface the raw response and stop — do not treat as a wiring gap.`);
  process.stdout.write(JSON.stringify({
    agentType, readState, features, verdict: 'ERROR', notEnabled, enableable, reasons, rawError,
  }, null, 2) + '\n');
  process.exit(0);
}

const signals = [];
for (const apiName of REQUIRED[agentType]) {
  const c = classifyFeature(apiName, statusMap);
  features[apiName] = {
    status: c.status, signal: c.signal,
    enableBlockedReasons: c.enableBlockedReasons, enableable: c.enableable, enableRoute: c.enableRoute,
  };
  reasons.push(c.reason);
  signals.push(c.signal);
  if (c.signal === 'FAIL') notEnabled.push(apiName);
  if (c.enableable) enableable.push(apiName);
}

let verdict;
if (signals.includes('FAIL')) verdict = 'NOT-READY';
else if (signals.every((s) => s === 'PASS')) verdict = 'READY';
else verdict = 'CANNOT-CONFIRM';

process.stdout.write(JSON.stringify({
  agentType,
  readState,
  features,
  verdict,
  notEnabled,
  enableable,
  reasons,
  rawError,
}, null, 2) + '\n');
