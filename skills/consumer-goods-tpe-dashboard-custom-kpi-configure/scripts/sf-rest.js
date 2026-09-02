#!/usr/bin/env node
/**
 * Authenticated Salesforce REST callout, replacing `sf api request rest`
 * everywhere in this skill — that command is beta, doesn't support --json,
 * and beta CLI surfaces can change or be pulled without notice. Fetches the
 * org's instanceUrl and access token via the `sf` CLI, then performs a
 * plain HTTP request with Node's built-in fetch. Access token retrieval is
 * version-gated the same way as `datakit-for-tpe`'s
 * `download-static-resource.js`: `sf org auth show-access-token` for CLI
 * >= 2.136.8 (below that version, `sf org display`'s own `result.accessToken`
 * is a redacted hint string, not a real token — see the `sfJson`/`getAccessToken`
 * pair below). The token is never printed.
 *
 * CLI usage:
 *   node sf-rest.js --target-org <username> --path <path> \
 *     [--method GET|POST|PATCH|DELETE] [--body <json-string>]
 *
 * <path> is relative to the org's instanceUrl, e.g.
 * "/services/apexrest/tpm-api/..." or "/services/data/v63.0/...".
 * Prints the response body as one line of JSON to stdout on both success
 * and failure, so a non-2xx error body (e.g. `{"error":"..."}`) is still
 * readable by the caller. Exit codes: 0 = 2xx response, 1 = non-2xx
 * response, 2 = usage/CLI error.
 *
 * Module usage (for sibling scripts in this same skill's scripts/ dir —
 * never imported across skill directories):
 *   const { restRequest } = require('./sf-rest');
 *   const { ok, status, body } = await restRequest({ targetOrg, path, method, body: jsonString });
 */

/**
 * Also exposes two subcommands that print only safe, non-secret fields from
 * `sf org display --json` — that command's `result` includes `accessToken`
 * (a live credential), so nothing in this skill should run it directly and
 * surface the raw output; these strip it before printing:
 *   node sf-rest.js org-status --target-org <username>
 *     -> {"username","alias","connectedStatus","orgId"} ; exit 1 if not Connected
 */

const { execFileSync } = require('child_process');

function sfJson(cliArgs) {
  // A color-forcing terminal (e.g. Warp's FORCE_COLOR=3) makes `sf` emit ANSI
  // codes even with --json, which breaks JSON.parse — force color off for
  // this invocation regardless of the calling shell's env.
  const raw = execFileSync('sf', cliArgs, {
    encoding: 'utf8',
    env: { ...process.env, FORCE_COLOR: '0', NO_COLOR: '1' },
  });
  return JSON.parse(raw).result;
}

const ACCESS_TOKEN_VIA_SHOW_COMMAND_SINCE = [2, 136, 8];

function getCliVersion() {
  // Unlike every other `sf ... --json` command, `sf version --json` returns
  // its fields at the top level — no `{status, result}` envelope.
  const raw = execFileSync('sf', ['version', '--json'], {
    encoding: 'utf8',
    env: { ...process.env, FORCE_COLOR: '0', NO_COLOR: '1' },
  });
  const { cliVersion } = JSON.parse(raw);
  const match = cliVersion.match(/(\d+)\.(\d+)\.(\d+)/);
  // A pre-release/suffixed version string (e.g. a nightly build) that
  // doesn't match this pattern is treated as "new enough" below, via
  // isAtLeast's null passthrough — never silently fall back to the
  // redacted-token path on an unparseable version.
  return match ? match.slice(1).map(Number) : null;
}

function isAtLeast(version, minVersion) {
  if (!version) return true;
  for (let i = 0; i < minVersion.length; i += 1) {
    const a = version[i] || 0;
    const b = minVersion[i] || 0;
    if (a !== b) return a > b;
  }
  return true;
}

function getAccessToken(targetOrg) {
  const useShowAccessTokenCommand = isAtLeast(
    getCliVersion(),
    ACCESS_TOKEN_VIA_SHOW_COMMAND_SINCE
  );
  if (useShowAccessTokenCommand) {
    return sfJson([
      'org', 'auth', 'show-access-token',
      '--target-org', targetOrg,
      '--no-prompt', '--json',
    ]).accessToken;
  }
  return sfJson(['org', 'display', '--target-org', targetOrg, '--json']).accessToken;
}

// instanceUrl/accessToken don't change within a single script run — caching
// them per targetOrg avoids 3 fresh `sf` CLI subprocess spawns (org display,
// version, show-access-token) on every single REST call, which otherwise
// dominates runtime once a script makes dozens of calls (e.g. cloning every
// KPI-bound visualization on a dashboard).
const orgConnectionCache = new Map();

function getOrgConnection(targetOrg) {
  if (!orgConnectionCache.has(targetOrg)) {
    const { instanceUrl } = sfJson(['org', 'display', '--target-org', targetOrg, '--json']);
    const accessToken = getAccessToken(targetOrg);
    orgConnectionCache.set(targetOrg, { instanceUrl, accessToken });
  }
  return orgConnectionCache.get(targetOrg);
}

async function restRequest({ targetOrg, path, method, body }) {
  const { instanceUrl, accessToken } = getOrgConnection(targetOrg);

  const headers = { Authorization: `Bearer ${accessToken}` };
  if (body !== undefined) headers['Content-Type'] = 'application/json';

  const response = await fetch(`${instanceUrl}${path}`, {
    method: method || 'GET',
    headers,
    body,
  });
  const text = await response.text();
  let parsedBody = {};
  if (text.length) {
    try {
      parsedBody = JSON.parse(text);
    } catch {
      parsedBody = text;
    }
  }
  return { ok: response.ok, status: response.status, body: parsedBody };
}

function getOrgStatus(targetOrg) {
  const info = sfJson(['org', 'display', '--target-org', targetOrg, '--json']);
  return {
    username: info.username,
    alias: info.alias || null,
    connectedStatus: info.connectedStatus,
    orgId: info.id,
  };
}

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

async function main() {
  const [maybeCommand, ...rest] = process.argv.slice(2);

  if (maybeCommand === 'org-status') {
    const args = parseArgs(rest);
    const status = getOrgStatus(requireArg(args, 'target-org'));
    process.stdout.write(JSON.stringify(status));
    if (status.connectedStatus !== 'Connected') process.exit(1);
    return;
  }

  const args = parseArgs(process.argv.slice(2));
  const targetOrg = requireArg(args, 'target-org');
  const path = requireArg(args, 'path');
  const method = args.method || 'GET';

  const { ok, status, body } = await restRequest({ targetOrg, path, method, body: args.body });
  process.stdout.write(JSON.stringify(body));
  if (!ok) {
    console.error(`sf-rest: HTTP ${status}`);
    process.exit(1);
  }
}

if (require.main === module) {
  main().catch((err) => {
    console.error(err);
    process.exit(1);
  });
}

module.exports = { restRequest, getOrgStatus };
