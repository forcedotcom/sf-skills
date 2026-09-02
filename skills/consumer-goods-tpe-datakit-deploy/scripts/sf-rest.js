/**
 * Shared `sf` CLI helpers for this skill's scripts: running `sf ... --json`
 * commands and resolving an org's access token.
 *
 * `sf org display --json`'s `result.accessToken` stopped being a real token
 * as of CLI v2.136.8 — that field becomes a redacted hint string pointing at
 * `sf org auth show-access-token` instead. `getAccessToken()` is version-gated
 * to handle both cases. The token is never printed.
 *
 * Also runnable directly for two subcommands that print only safe,
 * non-secret fields from `sf org display --json` — that command's `result`
 * includes `accessToken`, so nothing in this skill should run it directly
 * and surface the raw output; these strip it before printing:
 *   node sf-rest.js org-status --target-org <username>
 *     -> {"username","alias","connectedStatus","orgId"} ; exit 1 if not Connected
 */

const { execFileSync } = require('child_process');

const ACCESS_TOKEN_VIA_SHOW_COMMAND_SINCE = [2, 136, 8];

function sfJson(cliArgs) {
  const raw = execFileSync('sf', cliArgs, { encoding: 'utf8' });
  return JSON.parse(raw).result;
}

function getCliVersion() {
  // Unlike every other `sf ... --json` command, `sf version --json` returns
  // its fields at the top level — no `{status, result}` envelope — so this
  // can't go through `sfJson`.
  const raw = execFileSync('sf', ['version', '--json'], { encoding: 'utf8' });
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
  if (isAtLeast(getCliVersion(), ACCESS_TOKEN_VIA_SHOW_COMMAND_SINCE)) {
    return sfJson([
      'org', 'auth', 'show-access-token',
      '--target-org', targetOrg, '--no-prompt', '--json',
    ]).accessToken;
  }
  return sfJson(['org', 'display', '--target-org', targetOrg, '--json']).accessToken;
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

function main() {
  const [command, ...rest] = process.argv.slice(2);
  const args = parseArgs(rest);
  const targetOrg = requireArg(args, 'target-org');

  if (command === 'org-status') {
    const status = getOrgStatus(targetOrg);
    process.stdout.write(JSON.stringify(status));
    if (status.connectedStatus !== 'Connected') process.exit(1);
    return;
  }
  console.error(`Unknown command: ${command}. Use "org-status"`);
  process.exit(2);
}

if (require.main === module) {
  main();
}

module.exports = { sfJson, getCliVersion, isAtLeast, getAccessToken, getOrgStatus };
