#!/usr/bin/env node
/**
 * Generic status poller for async App Framework installs (and any other
 * REST endpoint shaped the same way).
 *
 * Usage:
 *   node poll-status.js \
 *     --target-org <username> \
 *     --path "/services/data/v67.0/app-framework/apps/<appId>" \
 *     --status-field applicationStatus \
 *     --success-values SuccessStatus,SuccessWithWarningsStatus \
 *     --failure-values FailedStatus \
 *     --interval-seconds 15 \
 *     --max-wait-seconds 300
 *
 * Behavior:
 *   - Calls `restRequest()` from the sibling `sf-rest.js` on every tick — a
 *     direct authenticated HTTP GET, not `sf api request rest` (beta, no
 *     `--json`, can change or be pulled without notice).
 *   - Reads --status-field off the parsed response body. Handles both a
 *     single-object response and a first-array-element response (same
 *     shape covers `apps/{id}` and `apps?templateSourceId=...` list calls).
 *   - Exit 0 on a success value, exit 1 on a failure value, exit 2 on
 *     timeout (still not-terminal) — distinct so a caller can tell
 *     "still installing" apart from "actually failed".
 *
 * Reused as-is by every async-install step in this skill — do not write a
 * second poll loop.
 */

const { restRequest } = require('./sf-rest');

function parseArgs(argv) {
  const args = {};
  for (let i = 0; i < argv.length; i += 1) {
    const token = argv[i];
    if (!token.startsWith('--')) continue;
    const key = token.slice(2);
    const value = argv[i + 1];
    args[key] = value;
    i += 1;
  }
  return args;
}

function requireArg(args, name) {
  if (!args[name]) {
    console.error(`Missing required --${name}`);
    process.exit(2);
  }
  return args[name];
}

async function fetchStatus(targetOrg, path) {
  const { ok, status, body } = await restRequest({ targetOrg, path, method: 'GET' });
  if (!ok) {
    throw new Error(`HTTP ${status}: ${JSON.stringify(body)}`);
  }
  if (Array.isArray(body)) {
    return body[0];
  }
  if (body && Array.isArray(body.apps)) {
    return body.apps[0];
  }
  return body;
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const targetOrg = requireArg(args, 'target-org');
  const path = requireArg(args, 'path');
  const statusField = requireArg(args, 'status-field');
  const successValues = requireArg(args, 'success-values').split(',');
  const failureValues = requireArg(args, 'failure-values').split(',');
  const intervalSeconds = Number(args['interval-seconds'] || '15');
  const maxWaitSeconds = Number(args['max-wait-seconds'] || '300');

  const deadline = Date.now() + maxWaitSeconds * 1000;

  for (;;) {
    let record;
    try {
      record = await fetchStatus(targetOrg, path);
    } catch (err) {
      console.error(`poll-status: request failed: ${err.message}`);
      process.exit(1);
    }

    const status = record ? record[statusField] : undefined;
    console.log(`poll-status: ${statusField}=${status}`);

    if (successValues.includes(status)) {
      console.log(`poll-status: terminal success (${status})`);
      process.exit(0);
    }
    if (failureValues.includes(status)) {
      console.error(`poll-status: terminal failure (${status})`);
      process.exit(1);
    }

    if (Date.now() >= deadline) {
      console.error(
        `poll-status: timed out after ${maxWaitSeconds}s, last status=${status}`
      );
      process.exit(2);
    }

    await sleep(intervalSeconds * 1000);
  }
}

main();
