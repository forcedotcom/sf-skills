#!/usr/bin/env node
/**
 * Trigger and poll a Data Cloud (SSOT) Data Transform via the sibling
 * `sf-rest.js`'s authenticated HTTP callout, reimplementing the run+wait
 * contract confirmed against this repo's own
 * `packages/liability-accruals/test/cdp-client.js`
 * (`waitForTransform` / `runAndWaitForTransform`) — that file is grounding
 * evidence for the REST contract only, never a runtime dependency; this
 * script never shells out to it or assumes `packages/liability-accruals`
 * is present in the checkout.
 *
 * Usage:
 *   node run-data-transform.js \
 *     --target-org <username> \
 *     --transform-name TPM_PROMOTION_MEASURE \
 *     [--api-version v67.0] \
 *     [--poll-interval-seconds 60] \
 *     [--max-wait-seconds 3600]
 *
 * Exit codes: 0 = terminal success, 1 = terminal failure (FAILURE with a
 * fresh lastRunDate), 2 = timeout while still pending/in-progress.
 *
 * Auth: the org's plain Salesforce access token via the already-
 * authenticated `sf` CLI user is sufficient for all three calls below —
 * despite the `/ssot/` path segment, this is not the separate CDP/A360
 * token exchange `cdp-client.js` performs for its unrelated ingestion
 * calls.
 */

const { restRequest } = require('./sf-rest');

function parseArgs(argv) {
  const args = {};
  for (let i = 0; i < argv.length; i += 1) {
    const token = argv[i];
    if (!token.startsWith('--')) continue;
    args[token.slice(2)] = argv[i + 1];
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

async function sfApi(targetOrg, path, method) {
  // A direct authenticated HTTP call via the sibling `sf-rest.js`, not
  // `sf api request rest` — that command is beta, has no `--json` flag at
  // all (confirmed live — it errors "Nonexistent flag: --json"), and beta
  // CLI surfaces can change or be pulled without notice.
  const { ok, status, body } = await restRequest({ targetOrg, path, method });
  if (!ok) {
    throw new Error(`HTTP ${status}: ${JSON.stringify(body)}`);
  }
  return body;
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function transformPath(apiVersion, name) {
  return `/services/data/${apiVersion}/ssot/data-transforms/${name}`;
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const targetOrg = requireArg(args, 'target-org');
  const name = requireArg(args, 'transform-name');
  const apiVersion = args['api-version'] || 'v67.0';
  const pollIntervalSeconds = Number(args['poll-interval-seconds'] || '60');
  const maxWaitSeconds = Number(args['max-wait-seconds'] || String(1 * 60 * 60));

  const path = transformPath(apiVersion, name);
  const baseline = await sfApi(targetOrg, path, 'GET');
  const baselineRunDate = baseline ? baseline.lastRunDate : null;
  console.log(`run-data-transform: name=${name}, baselineRunDate=${baselineRunDate}`);

  await sfApi(targetOrg, `${path}/actions/run`, 'POST');
  console.log('run-data-transform: run triggered');

  const deadline = Date.now() + maxWaitSeconds * 1000;

  for (;;) {
    await sfApi(targetOrg, `${path}/actions/refresh-status`, 'POST');
    const current = await sfApi(targetOrg, path, 'GET');
    const { lastRunStatus, lastRunDate, lastRunErrorMessage } = current;
    console.log(`run-data-transform: lastRunStatus=${lastRunStatus} lastRunDate=${lastRunDate}`);

    const isFresh = lastRunDate !== baselineRunDate;
    const isPending = lastRunStatus === 'PENDING' || lastRunStatus === 'IN_PROGRESS';

    if (isFresh && !isPending) {
      if (lastRunStatus === 'FAILURE') {
        console.error(`run-data-transform: FAILURE — ${lastRunErrorMessage}`);
        process.exit(1);
      }
      console.log(`run-data-transform: terminal success (${lastRunStatus})`);
      process.exit(0);
    }

    if (Date.now() >= deadline) {
      console.error(
        `run-data-transform: timed out after ${maxWaitSeconds}s, last status=${lastRunStatus} (still pending — not a failure)`
      );
      process.exit(2);
    }

    await sleep(pollIntervalSeconds * 1000);
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
