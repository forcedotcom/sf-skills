#!/usr/bin/env node
/**
 * Extracts the actual failure reason for a FailedStatus app-framework install
 * (e.g. the TPE Analytics App in Phase 11, or the C360 SDM app in Phase 6).
 *
 * `applicationStatus: FailedStatus` alone carries no detail — the underlying
 * per-requirement failure message only lives on the install's Domino runtime
 * (the App Framework's async execution graph), never on the app resource
 * itself. This script walks that graph so nothing in this skill has to
 * hand-parse it inline:
 *   1. GET /app-framework/apps/<appId>/activities -> latest activity's
 *      runtimeRequest.id (the runtime request tied to the failed install).
 *   2. GET /domino/runtimes/<runtimeRequestId> -> definition.nodes, each
 *      keyed by a graph node name (e.g. "template_requirement_<dmo>").
 *   3. Collect every node whose results.validate.taskStatus starts with
 *      "Fail" (covers FailEndOfPhaseStatus and any other Fail* variant) and
 *      its statusMessage — that message is the human-readable reason.
 *   4. Classify: a message matching the DMO-readiness template
 *      ("...[<dmo__dlm>] enabled or minimum required set of fields mapped
 *      in your org...") is a "DMO not available" failure; its DMO API name
 *      is pulled out of the message for the caller to act on (see this
 *      skill's Phase 11 debugging steps).
 *
 * Usage:
 *   node find-failure-reason.js --target-org <username> --app-id <appId>
 *
 * Prints one line of JSON: {"failedNodes":[{"node","statusMessage"}],
 * "dmoNotAvailable":["ssot__BusinessPeriod__dlm", ...]}. Exit 0 whether or
 * not a failure was found (this is a read-only diagnostic, not a
 * pass/fail gate) — exit 1 only on a request/usage error.
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
    process.exit(1);
  }
  return args[name];
}

async function getJson(targetOrg, path) {
  const { ok, status, body } = await restRequest({ targetOrg, path, method: 'GET' });
  if (!ok) {
    throw new Error(`HTTP ${status} for ${path}: ${JSON.stringify(body)}`);
  }
  return body;
}

// The chain's own failMessage template is inconsistent about the opening
// "[" (confirmed live: BusinessPeriod's message has it, MeasureDefinition's
// doesn't) — match the closing "]" only and treat the opening one as
// optional. statusMessage also arrives HTML-entity-encoded (e.g. "&#39;"
// for an apostrophe); decode the handful of entities this template uses
// before matching or displaying it.
const DMO_NOT_AVAILABLE_PATTERN =
  /don't have \[?([\w.]+__dlm)\] enabled or minimum required set of fields mapped/;

function decodeEntities(text) {
  return text
    .replace(/&#39;/g, "'")
    .replace(/&quot;/g, '"')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>');
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const targetOrg = requireArg(args, 'target-org');
  const appId = requireArg(args, 'app-id');

  let runtimeRequestId = args['runtime-request-id'];
  if (!runtimeRequestId) {
    const activities = await getJson(
      targetOrg,
      `/services/data/v67.0/app-framework/apps/${appId}/activities`
    );
    const items = activities.items || [];
    if (!items.length) {
      process.stdout.write(JSON.stringify({ failedNodes: [], dmoNotAvailable: [] }));
      return;
    }
    // Activities are returned most-recent-first; the latest install attempt
    // is the one whose reason we want.
    runtimeRequestId = items[0].runtimeRequest && items[0].runtimeRequest.id;
    if (!runtimeRequestId) {
      process.stdout.write(JSON.stringify({ failedNodes: [], dmoNotAvailable: [] }));
      return;
    }
  }

  const runtime = await getJson(
    targetOrg,
    `/services/data/v67.0/domino/runtimes/${runtimeRequestId}`
  );
  const nodes = (runtime.definition && runtime.definition.nodes) || {};

  const failedNodes = [];
  const dmoNotAvailable = [];

  for (const [nodeName, node] of Object.entries(nodes)) {
    const validate = node.results && node.results.validate;
    const taskStatus = validate && validate.taskStatus;
    if (!taskStatus || !taskStatus.startsWith('Fail')) continue;

    const statusMessage = decodeEntities(validate.statusMessage || '');
    failedNodes.push({ node: nodeName, statusMessage });

    const match = statusMessage.match(DMO_NOT_AVAILABLE_PATTERN);
    if (match) dmoNotAvailable.push(match[1]);
  }

  process.stdout.write(JSON.stringify({ failedNodes, dmoNotAvailable }));
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
