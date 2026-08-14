#!/usr/bin/env node
// Deterministic HTTP-result classifier for automation-sandbox-post-copy-configure.
//
// Reads the outcome of a single Tooling API PATCH and classifies it as
// SUCCESS / FAILED. HTTP 204 with an empty body is success; every other code
// is failure. Encodes the classification that was formerly prose in SKILL.md
// (authoring standard A9). The RETRY-once policy stays as inline bash in the
// caller (a `for attempt in 1 2; do ... && break; done` loop) — this script
// is invoked on each attempt to decide whether that attempt succeeded.
//
// Usage:
//   node classify-patch-result.mjs <httpCode> [responseBodyFile]
//
// Emits to stdout (single JSON object):
//   { "status": "SUCCESS", "http": 204 }
//   { "status": "FAILED",  "http": <code>, "error": "<extracted message>" }
//
// Exit code 0 on SUCCESS; exit code 2 on FAILED (so a bash caller can
// `if node classify-patch-result.mjs "$code" body.json; then …; else …; fi`).
// Exit code 1 on input error (missing http code).

import { existsSync, readFileSync } from 'node:fs';

function fail(msg) {
  process.stderr.write(`classify-patch-result: ${msg}\n`);
  process.exit(1);
}

const [, , httpArg, bodyPath] = process.argv;
if (!httpArg) fail('missing http code argument');

const http = Number.parseInt(httpArg, 10);
if (!Number.isInteger(http) || http < 100 || http > 599) {
  fail(`invalid http code ${JSON.stringify(httpArg)}`);
}

let body = '';
let bodyReadFailed = false;
if (bodyPath) {
  if (!existsSync(bodyPath)) {
    bodyReadFailed = true;
  } else {
    try {
      body = readFileSync(bodyPath, 'utf-8');
    } catch {
      bodyReadFailed = true;
    }
  }
}
const trimmedBody = body.trim();

// Success requires HTTP 204 AND (either no bodyPath supplied at all, or the
// supplied path was readable and empty). A bodyPath that was supplied but
// missing/unreadable indicates the caller's response-capture step failed —
// must not short-circuit to SUCCESS, since a captured empty body is not the
// same signal as a body we could not read.
if (http === 204 && trimmedBody === '' && !bodyReadFailed) {
  process.stdout.write(JSON.stringify({ status: 'SUCCESS', http: 204 }) + '\n');
  process.exit(0);
}

let errorMessage = trimmedBody;
try {
  const parsed = JSON.parse(body);
  if (Array.isArray(parsed) && parsed[0]?.message) {
    errorMessage = String(parsed[0].message);
  } else if (parsed?.message) {
    errorMessage = String(parsed.message);
  } else if (parsed?.error?.message) {
    errorMessage = String(parsed.error.message);
  }
} catch {
  /* body was not JSON — surface raw text */
}

if (errorMessage.length > 800) errorMessage = errorMessage.slice(0, 800) + '…';
if (bodyReadFailed) {
  errorMessage = `response body path ${bodyPath} was supplied but could not be read (missing or unreadable) — capture step likely failed`;
} else if (!errorMessage) {
  errorMessage = `HTTP ${http} with no body`;
} else if (http === 204) {
  errorMessage = `HTTP 204 with unexpected non-empty body: ${errorMessage}`;
}

process.stdout.write(
  JSON.stringify({ status: 'FAILED', http, error: errorMessage }) + '\n',
);
process.exit(2);
