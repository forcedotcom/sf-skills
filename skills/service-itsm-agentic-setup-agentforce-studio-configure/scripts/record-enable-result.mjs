#!/usr/bin/env node
// Deterministic per-toggle enable-result recorder (authoring standard A9).
//
// Classifying a single `/enable` POST response as ENABLED vs FAILED, and
// accumulating that into a running results file across the enable loop, is a
// fixed decision — it must not be left to the model to eyeball each response
// in prose across a variable-length loop.
//
// Usage:
//   node record-enable-result.mjs <response.json> <apiName> <results.json>
//
// <response.json> is a FILE PATH to the raw stdout captured from a single:
//   sf api request rest ".../feature/<apiName>/enable" --method POST --body '{}' --target-org <alias>
// <results.json> is a FILE PATH this script reads (if present) and rewrites —
// an accumulator object keyed by apiName, so it can be called once per
// toggle, immediately after each individual (still-visible) Bash enable call.
//
// Prints the updated accumulator object to stdout on success. Exit code is
// always 0 on usable args — a failed enable is a recorded FAILED result, not
// a script failure.

import { readFileSync, writeFileSync, existsSync } from 'node:fs';

const [responsePath, apiName, resultsPath] = process.argv.slice(2);
if (!responsePath || !apiName || !resultsPath) {
  process.stderr.write('usage: node record-enable-result.mjs <response.json> <apiName> <results.json>\n');
  process.exit(2);
}

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

function errorSnippet(errs) {
  return errs.map((e) => `${e.errorCode ?? 'ERROR'}: ${e.message ?? ''}`.trim()).join(' | ').slice(0, 500);
}

const res = readJson(responsePath);
let entry;
if (!res.ok) {
  entry = { status: 'FAILED', reason: res.empty ? 'Enable call produced an empty body.' : 'Enable call produced a non-JSON body.' };
} else {
  const errs = asErrorArray(res.data);
  if (errs.length) {
    entry = { status: 'FAILED', reason: errorSnippet(errs) };
  } else if (res.data?.success === true) {
    entry = { status: 'ENABLED', reason: null };
  } else {
    entry = { status: 'FAILED', reason: `Unexpected response shape (no success:true, no error body): ${JSON.stringify(res.data).slice(0, 500)}` };
  }
}

let results = {};
if (existsSync(resultsPath)) {
  const existing = readJson(resultsPath);
  if (existing.ok && existing.data && typeof existing.data === 'object') results = existing.data;
}
results[apiName] = entry;

writeFileSync(resultsPath, JSON.stringify(results, null, 2), 'utf8');
process.stdout.write(JSON.stringify(results, null, 2) + '\n');
