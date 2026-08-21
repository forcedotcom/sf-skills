#!/usr/bin/env node
// Deterministic target-user resolver for the ITSM Intelligence permset-assign flow.
//
// Reads the `GET /services/data/v67.0/` capture (or an equivalent versions-list
// response the CLI writes when hitting the API root), and extracts the running
// user's Id from the `identity` URL. The URL shape is:
//     https://<mydomain>.my.salesforce.com/id/<orgId 00D…>/<userId 005…>
// so we take the LAST path segment and require it to start with `005` and be
// 15 or 18 chars (case-preserving).
//
// This exists so no prose step ever tries to parse the identity URL by hand
// (A9 — deterministic decisions belong in scripts).
//
// Usage:
//   node resolve-target-user.mjs <api-root.json>
//
// Emits a single JSON object to stdout:
//   { userId: "005…" | null,
//     identity: "<full URL>" | null,
//     verdict: "RESOLVED" | "CANNOT-CONFIRM",
//     reasons: [...] }
// Exit is always 0 on parseable bodies; verdict carries the decision.

import { readFileSync } from 'node:fs';

const [rootPath] = process.argv.slice(2);
if (!rootPath) {
  process.stderr.write('usage: node resolve-target-user.mjs <api-root.json>\n');
  process.exit(2);
}

function fail(reasons) {
  process.stdout.write(JSON.stringify({
    userId: null, identity: null, verdict: 'CANNOT-CONFIRM', reasons,
  }, null, 2) + '\n');
  process.exit(0);
}

let text;
try {
  text = readFileSync(rootPath, 'utf8').trim();
} catch (e) {
  fail([`unreadable file at ${rootPath}: ${e?.message ?? e}`]);
}
if (!text) fail([`empty file: ${rootPath}`]);

let data;
try {
  data = JSON.parse(text);
} catch (e) {
  fail([`invalid JSON at ${rootPath}: ${e?.message ?? e}`]);
}
if (!data || typeof data !== 'object') fail([`non-object JSON at ${rootPath}`]);
if (typeof data.status === 'number' && data.status !== 0) {
  fail([`sf api request at ${rootPath} failed with status ${data.status}`]);
}

// `sf api request rest` returns the raw body directly; the API root response
// contains `identity`, `rest`, and version fields at the top level.
const identity = typeof data.identity === 'string'
  ? data.identity
  : (typeof data.result?.identity === 'string' ? data.result.identity : null);

if (!identity) {
  fail(['response body has no `identity` field — cannot resolve the running user without it. Confirm the org is reachable and re-run `sf api request rest "/services/data/v67.0/"`.']);
}

const segments = identity.split('/').filter(Boolean);
const last = segments[segments.length - 1] ?? '';

// Salesforce user Ids: 15-char case-sensitive or 18-char case-insensitive, prefix `005`.
if (!/^005[A-Za-z0-9]{12}([A-Za-z0-9]{3})?$/.test(last)) {
  fail([
    `identity URL trailing segment "${last}" does not match the expected user-Id shape (005 + 12 or 15 alphanum chars).`,
    `full identity URL: ${identity}`,
  ]);
}

process.stdout.write(JSON.stringify({
  userId: last,
  identity,
  verdict: 'RESOLVED',
  reasons: [
    `Extracted running-user Id "${last}" from identity URL trailing path segment.`,
  ],
}, null, 2) + '\n');
