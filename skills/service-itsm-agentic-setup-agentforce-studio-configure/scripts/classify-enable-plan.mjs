#!/usr/bin/env node
// Deterministic enable-plan classifier for Agentforce for IT Service.
//
// Consumes the raw JSON body of a single `sf api request rest` read of the
// Salesforce Go feature-status endpoint and, for a chosen agent path
// (fulfiller | employee), computes a dependency-ordered enable plan and (on a
// second call, after the enable loop) the final per-feature verdict. This is
// the deterministic decision table that MUST NOT be interpreted by the model
// in prose (authoring standard A9) — same contract as the sibling
// service-itsm-agentic-setup-agentforce-studio-validate skill's
// classify-readiness.mjs, extended with enable ordering.
//
// Usage:
//   node classify-enable-plan.mjs <features-status.json> <agentType> [exitStatus]
//
// <features-status.json> is a FILE PATH to the raw stdout captured from:
//   sf api request rest "/services/data/vXX.0/connect/setup/discovery/features/status" \
//     --method POST --body '{"featureApiNames":[...]}' --target-org <org> > file.json
// The body shape is { items: [ { apiName, status, enableBlockedReasons[],
// dependencyStatuses[] } ] } where status is "ENABLED" | "NOT_ENABLED". The
// file may instead hold the CLI error payload or be empty on a non-zero exit.
//
// <exitStatus> is the OPTIONAL numeric exit code of the `sf` command ($? in
// the shell) — distinguishes a confirmed 404 ("gate not wired" ->
// CANNOT-CONFIRM) from an auth/permission/transport failure (-> ERROR).
//
// <agentType> is one of: fulfiller | employee. Selects which path-specific
// template toggle is required in addition to the three shared toggles.
//
// Emits a single JSON object to stdout:
//   { agentType, readState,
//     features: { <apiName>: { status, signal, enableBlockedReasons } },
//     order: [<apiName>...],        // dependency-first order for the REQUIRED set
//     alreadyEnabled: [<apiName>...],
//     pending: [<apiName>...],      // NOT_ENABLED, in dependency order — the enable plan
//     blocked: [<apiName>...],      // NOT_ENABLED with non-empty enableBlockedReasons
//     unconfirmed: [<apiName>...],  // missing from the response or an unexpected status
//     verdict, reasons: [...], rawError }
// where verdict is ALL-ENABLED | NEEDS-ENABLE | CANNOT-CONFIRM | ERROR.
// Call this script BEFORE enabling (verdict=NEEDS-ENABLE -> drive the confirm
// list + enable loop from `pending`, in `order`) and AGAIN AFTER the enable
// loop on a fresh read (verdict=ALL-ENABLED -> success; anything left in
// `blocked` -> report enableBlockedReasons verbatim as FAILED for that toggle;
// anything in `unconfirmed` -> report CANNOT-CONFIRM for that toggle rather
// than assuming success — a required feature can be missing from the
// response or carry a status this classifier doesn't recognize, and an empty
// `pending` in that case does NOT mean every required toggle is ENABLED).
// Exit code is always 0 on a usable agentType; the verdict is in the payload.

import { readFileSync } from 'node:fs';

// Real Salesforce Go featureApiNames behind the "Agentforce for IT Service"
// setup page toggles — same apiNames the sibling validate skill classifies.
const EINSTEIN = 'sales-cloud-einstein-generative-ai';      // base layer (no deps)
const STUDIO = 'sales-cloud-agent-studio';                  // "Turn on Agentforce Studio"
const PARENT = 'service-cloud-agentforce-for-itsm';         // "Agentforce for IT Service" umbrella
const FULFILLER = 'service-cloud-it-fulfiller-agent';       // "IT Service Fulfiller"
const REQUESTOR = 'service-cloud-requestor-agent';          // "IT Service Employee"
const SPECIALIZED = 'service-cloud-it-service-employee-agent'; // "Specialized Agent Templates for Employee"

// Dependency-first order per path: Einstein GenAI -> Studio -> parent umbrella -> child template(s).
const ORDER = {
  fulfiller: [EINSTEIN, STUDIO, PARENT, FULFILLER],
  employee: [EINSTEIN, STUDIO, PARENT, REQUESTOR, SPECIALIZED],
};

const LABEL = {
  [EINSTEIN]: 'Einstein Generative AI',
  [STUDIO]: 'Agentforce Studio',
  [PARENT]: 'Agentforce for IT Service (parent)',
  [FULFILLER]: 'IT Service Fulfiller template',
  [REQUESTOR]: 'IT Service Employee template',
  [SPECIALIZED]: 'Specialized Agent Templates for Employee',
};

function readJson(path) {
  try {
    const text = readFileSync(path, 'utf8').trim();
    if (!text) return { ok: false, empty: true };
    return { ok: true, data: JSON.parse(text) };
  } catch {
    return { ok: false, empty: false };
  }
}

function asErrorArray(data) {
  if (Array.isArray(data)) return data.filter((e) => e && (e.errorCode || e.message));
  if (data && (data.errorCode || data.message)) return [data];
  return [];
}

function isNotFoundError(errs) {
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

function readFeatureStatus(res, exitStatus) {
  if (!res.ok) {
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
    return { status: 'UNKNOWN', signal: 'CANNOT-CONFIRM', enableBlockedReasons: [], reason: `${label} (${apiName}) — no status returned.` };
  }
  const { status, enableBlockedReasons } = statusMap.get(apiName);
  if (status === 'ENABLED') {
    return { status, signal: 'PASS', enableBlockedReasons: [], reason: `${label} (${apiName}) → ENABLED.` };
  }
  if (status === 'NOT_ENABLED') {
    const blocked = enableBlockedReasons.length > 0;
    return {
      status, signal: 'FAIL', enableBlockedReasons,
      reason: blocked
        ? `${label} (${apiName}) → NOT_ENABLED, blocked: ${enableBlockedReasons.map((r) => (typeof r === 'string' ? r : (r?.message ?? JSON.stringify(r)))).join('; ')}.`
        : `${label} (${apiName}) → NOT_ENABLED (ready to enable).`,
    };
  }
  return { status, signal: 'CANNOT-CONFIRM', enableBlockedReasons: [], reason: `${label} (${apiName}) → unexpected status "${status}".` };
}

const [statusPath, rawAgentType, rawExit] = process.argv.slice(2);
const agentType = String(rawAgentType ?? '').toLowerCase();
if (!statusPath || !ORDER[agentType]) {
  process.stderr.write('usage: node classify-enable-plan.mjs <features-status.json> <fulfiller|employee> [exitStatus]\n');
  process.exit(2);
}
const exitStatus = rawExit === undefined ? NaN : Number(rawExit);
const order = ORDER[agentType];

const { readState, statusMap, rawError } = readFeatureStatus(readJson(statusPath), exitStatus);

const features = {};
const reasons = [];
const alreadyEnabled = [];
const pending = [];
const blocked = [];

if (readState === 'error') {
  for (const apiName of order) {
    features[apiName] = { status: 'UNKNOWN', signal: 'ERROR', enableBlockedReasons: [] };
  }
  reasons.push(`Feature status could not be read: ${rawError} Surface the raw response and stop — do not treat as a wiring gap.`);
  process.stdout.write(JSON.stringify({
    agentType, readState, features, order, alreadyEnabled, pending, blocked, unconfirmed: order.slice(), verdict: 'ERROR', reasons, rawError,
  }, null, 2) + '\n');
  process.exit(0);
}

if (readState === 'not-wired') {
  for (const apiName of order) {
    features[apiName] = { status: 'UNKNOWN', signal: 'CANNOT-CONFIRM', enableBlockedReasons: [] };
  }
  reasons.push('The feature-discovery surface returned a confirmed 404 — not wired on this org tier.');
  process.stdout.write(JSON.stringify({
    agentType, readState, features, order, alreadyEnabled, pending, blocked, unconfirmed: order.slice(), verdict: 'CANNOT-CONFIRM', reasons, rawError,
  }, null, 2) + '\n');
  process.exit(0);
}

const unconfirmed = [];
for (const apiName of order) {
  const c = classifyFeature(apiName, statusMap);
  features[apiName] = { status: c.status, signal: c.signal, enableBlockedReasons: c.enableBlockedReasons };
  reasons.push(c.reason);
  if (c.signal === 'PASS') alreadyEnabled.push(apiName);
  if (c.signal === 'FAIL') {
    pending.push(apiName);
    if (c.enableBlockedReasons.length) blocked.push(apiName);
  }
  if (c.signal === 'CANNOT-CONFIRM') unconfirmed.push(apiName);
}

// A required feature missing from the response, or carrying an unexpected
// status string, is neither confirmed ENABLED nor NOT_ENABLED — an empty
// `pending` list in that case must NOT read as ALL-ENABLED.
let verdict;
if (pending.length > 0) verdict = 'NEEDS-ENABLE';
else if (unconfirmed.length > 0) verdict = 'CANNOT-CONFIRM';
else verdict = 'ALL-ENABLED';

process.stdout.write(JSON.stringify({
  agentType, readState, features, order, alreadyEnabled, pending, blocked, unconfirmed, verdict, reasons, rawError,
}, null, 2) + '\n');
