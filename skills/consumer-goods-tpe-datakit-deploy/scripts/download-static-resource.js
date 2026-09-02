#!/usr/bin/env node
/**
 * Downloads and unzips a StaticResource from an authenticated org, reusing
 * the same contract as `downloadStaticResource` in
 * `packages/liability-accruals/setup/steps/01-download-static-resource.js`
 * (SOQL for the StaticResource Id, then an authenticated GET against
 * `<instanceUrl>/services/data/v<apiVersion>/sobjects/StaticResource/<id>/Body`,
 * then extract the zip) — reimplemented here with Node's built-in fetch
 * instead of `curl`, so this skill has no dependency on that script. Zip
 * extraction shells out to a platform-native tool rather than an npm
 * package (`adm-zip`, etc.) so this skill stays dependency-free and portable
 * across machines that clone/copy it standalone, per this repo's
 * self-contained-skills rule:
 *   - Windows: `tar -xf` — the `tar.exe` bundled with Windows 10 (1803+) and
 *     11 is bsdtar, which reads zip archives transparently.
 *   - macOS/Linux: `unzip` — preinstalled on macOS; on Linux it's a common
 *     but not universal package (missing ⇒ clear error telling the user to
 *     install it). GNU `tar` on Linux cannot read zip, so `tar` is not a
 *     safe cross-platform substitute there.
 *
 * One deliberate deviation from that reference: `getOrgDetails()` there
 * reads `sf org display --json`'s `result.accessToken` directly, which no
 * longer returns a real token on `sf` CLI >= 2.136.8 (that field becomes a
 * redacted hint string pointing at `sf org auth show-access-token` —
 * confirmed live against this repo's own dev org). `getAccessToken()` in
 * ``./sf-rest` is version-gated to handle both cases; the token is never
 * printed.
 *
 * Usage:
 *   node download-static-resource.js \
 *     --target-org <username> \
 *     --name CGCloudAddons \
 *     [--output-dir <dir>]   # defaults to a fresh dir under the OS temp dir
 *
 * Writes <output-dir>/<name>.zip and unzips it to <output-dir>/<name>/.
 * Prints STATIC_RESOURCE_PATH=<absolute unzipped dir> on success.
 *
 * Exit codes: 0 = success, 1 = resource not found, org not connected, or
 * download/unzip failure.
 */

const fs = require('fs');
const os = require('os');
const path = require('path');
const { execFileSync } = require('child_process');
const { sfJson, getAccessToken } = require('./sf-rest');

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

function unzipTo(zipPath, destDir) {
  const [cmd, cmdArgs] = process.platform === 'win32'
    ? ['tar', ['-xf', zipPath, '-C', destDir]]
    : ['unzip', ['-o', '-q', zipPath, '-d', destDir]];
  const attemptedCommand = `${cmd} ${cmdArgs.join(' ')}`;
  try {
    execFileSync(cmd, cmdArgs, { stdio: 'pipe' });
  } catch (error) {
    if (error.code === 'ENOENT') {
      console.error(
        `download-static-resource: command failed — "${attemptedCommand}" — "${cmd}" is not installed or not on PATH — ${
          process.platform === 'win32'
            ? 'expected the tar.exe bundled with Windows 10 (1803+) / 11'
            : 'install it (e.g. `apt install unzip`) and retry'
        }. If a different extraction command is available on this machine, run it manually against "${zipPath}" -> "${destDir}" and re-invoke this script with the same --output-dir to skip re-downloading.`
      );
      process.exit(1);
    }
    console.error(
      `download-static-resource: command failed — "${attemptedCommand}" — ${error.message}`
    );
    process.exit(1);
  }
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const targetOrg = requireArg(args, 'target-org');
  const name = requireArg(args, 'name');
  const outputDir =
    args['output-dir'] ||
    fs.mkdtempSync(path.join(os.tmpdir(), 'cgcloud-static-resource-'));

  const queryResult = sfJson([
    'data',
    'query',
    '--target-org',
    targetOrg,
    '--query',
    `SELECT Id, Name FROM StaticResource WHERE Name='${name}'`,
    '--json',
  ]);
  if (!queryResult.records || queryResult.records.length < 1) {
    console.error(
      `download-static-resource: no StaticResource named "${name}" found in ${targetOrg} — confirm the package version installed in this org includes it.`
    );
    process.exit(1);
  }
  const staticResourceId = queryResult.records[0].Id;

  const orgDetails = sfJson(['org', 'display', '--target-org', targetOrg, '--json']);
  const instanceUrl = orgDetails.instanceUrl;
  const apiVersion = orgDetails.apiVersion || '60.0';
  const accessToken = getAccessToken(targetOrg);

  const bodyUrl = `${instanceUrl}/services/data/v${apiVersion}/sobjects/StaticResource/${staticResourceId}/Body`;
  const response = await fetch(bodyUrl, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (!response.ok) {
    console.error(
      `download-static-resource: download failed with HTTP ${response.status}`
    );
    process.exit(1);
  }
  const buffer = Buffer.from(await response.arrayBuffer());

  fs.mkdirSync(outputDir, { recursive: true });
  const zipPath = path.join(outputDir, `${name}.zip`);
  fs.writeFileSync(zipPath, buffer);

  const unzipDir = path.join(outputDir, name);
  if (fs.existsSync(unzipDir)) {
    fs.rmSync(unzipDir, { recursive: true, force: true });
  }
  fs.mkdirSync(unzipDir, { recursive: true });
  unzipTo(zipPath, unzipDir);

  console.log(`STATIC_RESOURCE_PATH=${path.resolve(unzipDir)}`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
