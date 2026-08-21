#!/usr/bin/env node
// Deterministic final-report aggregator for the enable flow (authoring
// standard A9). Combines the Phase-2 (before-write) plan, the Phase-4
// per-toggle enable results (from record-enable-result.mjs), and the Phase-5
// (after-write) re-classification into one final per-feature verdict plus an
// overall SUCCESS/PARTIAL/FAILED/CANNOT-CONFIRM/ERROR summary — a fixed
// comparison/aggregation that must not be eyeballed by the model across a
// variable-length feature list.
//
// Usage:
//   node classify-final-report.mjs <before.json> <results.json|-> <after.json>
//
// <before.json>  — stdout of classify-enable-plan.mjs from Phase 2 (pre-write).
// <results.json> — stdout of record-enable-result.mjs accumulated across
//                  Phase 4 (one entry per toggle actually POSTed to /enable).
//                  Pass "-" if Phase 4 never ran (Phase-2 verdict was already
//                  ALL-ENABLED or CANNOT-CONFIRM/ERROR).
// <after.json>   — stdout of classify-enable-plan.mjs from Phase 5 (post-write).
//
// Emits a single JSON object to stdout:
//   { features: { <apiName>: { finalStatus, reason } }, order: [...], overall, reasons: [...] }
// where finalStatus is ALREADY-ENABLED | ENABLED | FAILED | CANNOT-CONFIRM | ERROR
// and overall is SUCCESS | PARTIAL | FAILED | CANNOT-CONFIRM | ERROR.
// Exit code is always 0 on usable args.

import { readFileSync } from 'node:fs';

const [beforePath, resultsPath, afterPath] = process.argv.slice(2);
if (!beforePath || !resultsPath || !afterPath) {
  process.stderr.write('usage: node classify-final-report.mjs <before.json> <results.json|-> <after.json>\n');
  process.exit(2);
}

function readJson(path) {
  try {
    return JSON.parse(readFileSync(path, 'utf8'));
  } catch {
    return null;
  }
}

const before = readJson(beforePath);
const after = readJson(afterPath);
const results = resultsPath === '-' ? {} : (readJson(resultsPath) ?? {});

if (!after || !Array.isArray(after.order)) {
  process.stderr.write(`error: could not read/parse a usable "after" report from ${afterPath}\n`);
  process.exit(3);
}

const alreadyEnabledBefore = new Set(Array.isArray(before?.alreadyEnabled) ? before.alreadyEnabled : []);
const order = after.order;
const features = {};
const reasons = [];

for (const apiName of order) {
  const afterFeature = after.features?.[apiName];
  const recorded = results?.[apiName];
  const signal = afterFeature?.signal;

  // The Phase-2 "already enabled" shortcut only applies if the Phase-5
  // post-write read actually confirms it — a failed/unconfirmed re-read must
  // never be silently overridden by the pre-write snapshot, or a broken
  // verification read reports false SUCCESS for every already-enabled toggle.
  if (alreadyEnabledBefore.has(apiName) && signal === 'PASS') {
    features[apiName] = { finalStatus: 'ALREADY-ENABLED', reason: `${apiName} was already ENABLED before this run.` };
    continue;
  }

  if (signal === 'PASS') {
    features[apiName] = { finalStatus: 'ENABLED', reason: `${apiName} is ENABLED after this run.` };
  } else if (signal === 'FAIL') {
    const enableBlockedReasons = afterFeature?.enableBlockedReasons ?? [];
    const recordedReason = recorded?.status === 'FAILED' ? recorded.reason : null;
    features[apiName] = {
      finalStatus: 'FAILED',
      reason: recordedReason
        ? `${apiName} — the /enable call failed: ${recordedReason}`
        : enableBlockedReasons.length
          ? `${apiName} — still blocked after the enable loop: ${JSON.stringify(enableBlockedReasons)}`
          : `${apiName} — still NOT_ENABLED after the enable loop (not attempted or attempt did not persist).`,
    };
  } else if (signal === 'CANNOT-CONFIRM') {
    features[apiName] = { finalStatus: 'CANNOT-CONFIRM', reason: `${apiName} — status could not be confirmed on the post-write read.` };
  } else {
    features[apiName] = { finalStatus: 'ERROR', reason: `${apiName} — the post-write read failed (${afterFeature?.reason ?? 'unknown error'}).` };
  }
  reasons.push(features[apiName].reason);
}

const statuses = Object.values(features).map((f) => f.finalStatus);
const hasError = statuses.includes('ERROR');
const hasFailed = statuses.includes('FAILED');
const hasCannotConfirm = statuses.includes('CANNOT-CONFIRM');
const hasEnabled = statuses.includes('ENABLED');

let overall;
if (hasError) overall = 'ERROR';
else if (hasFailed || hasCannotConfirm) overall = hasEnabled ? 'PARTIAL' : (hasFailed ? 'FAILED' : 'CANNOT-CONFIRM');
else overall = 'SUCCESS';

process.stdout.write(JSON.stringify({ features, order, overall, reasons }, null, 2) + '\n');
