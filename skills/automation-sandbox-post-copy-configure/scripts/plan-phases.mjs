#!/usr/bin/env node
// Deterministic phase planner for automation-sandbox-post-copy-configure.
//
// Reads a post-copy config JSON array and emits the ordered execution plan
// the workflow steps through. Encodes the two invariants that were formerly
// prose in SKILL.md (authoring standard A9):
//
//   1. Phases are ORDINAL — the 1-indexed position of the entry's
//      ExecutionOrder bucket in the sorted list of distinct buckets. Sparse
//      ExecutionOrder values do NOT produce empty phases (1,2,5 → phases
//      1,2,3, not 1,2,5).
//   2. IsActive:false entries are pre-marked SKIPPED_INACTIVE and kept in
//      the plan (not filtered out) so the summary can list them.
//
// Usage:
//   node plan-phases.mjs <config.json>
//
// Emits to stdout (single JSON object):
//   {
//     "phases": [
//       { "ordinal": 1, "executionOrder": <raw>,
//         "entries": [
//           { "index": <0-based original index>,
//             "configurationName": "...",
//             "label": "...",
//             "isActive": <bool>,
//             "action": "APPLY" | "SKIP_INACTIVE",
//             "fields": { ... } } ] }
//     ],
//     "totals": { "entries": <n>, "phases": <m>, "skipInactive": <k> }
//   }
//
// Exit codes: 0 on success; 1 on any input/parse error (message on stderr).

import { readFileSync } from 'node:fs';

function fail(msg) {
  process.stderr.write(`plan-phases: ${msg}\n`);
  process.exit(1);
}

const [, , path] = process.argv;
if (!path) fail('missing config path argument');

let raw;
try {
  raw = readFileSync(path, 'utf-8');
} catch (err) {
  fail(`cannot read ${path}: ${err.message}`);
}

let entries;
try {
  entries = JSON.parse(raw);
} catch (err) {
  fail(`config is not valid JSON: ${err.message}`);
}

if (!Array.isArray(entries)) fail('config must be a top-level JSON array');

const buckets = new Map();
entries.forEach((entry, index) => {
  const eo = entry?.ExecutionOrder;
  if (!Number.isInteger(eo) || eo < 1) {
    fail(`entry[${index}] has invalid ExecutionOrder ${JSON.stringify(eo)} — must be a positive integer`);
  }
  const list = buckets.get(eo) ?? [];
  list.push({ entry, index });
  buckets.set(eo, list);
});

const sortedOrders = [...buckets.keys()].sort((a, b) => a - b);
let skipInactive = 0;

const phases = sortedOrders.map((eo, i) => ({
  ordinal: i + 1,
  executionOrder: eo,
  entries: buckets.get(eo).map(({ entry, index }) => {
    const isActive = entry.IsActive !== false;
    if (!isActive) skipInactive += 1;
    return {
      index,
      configurationName: entry.ConfigurationName,
      label: entry.Label,
      isActive,
      action: isActive ? 'APPLY' : 'SKIP_INACTIVE',
      fields: entry.Fields ?? {},
    };
  }),
}));

process.stdout.write(
  JSON.stringify(
    { phases, totals: { entries: entries.length, phases: phases.length, skipInactive } },
    null,
    2,
  ) + '\n',
);
