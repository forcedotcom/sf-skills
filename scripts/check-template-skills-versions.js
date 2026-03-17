#!/usr/bin/env node
/**
 * Compares npm-latest versions vs the synced .template-versions.json for each
 * template skill package.  Writes skip, branch, title, body to GITHUB_OUTPUT
 * when running in CI; prints JSON locally.
 *
 * Used by .github/workflows/sync-template-skills.yml to decide whether a sync
 * is needed and to build descriptive PR metadata.
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');
const { matchingDeps } = require('./lib/package-utils');

const VERSIONS_FILE = '.template-versions.json';

const repoRoot = process.cwd();
const pkg = JSON.parse(fs.readFileSync(path.join(repoRoot, 'package.json'), 'utf8'));
const packageNames = matchingDeps(pkg);

const versionsPath = path.join(repoRoot, 'skills', VERSIONS_FILE);
let syncedVersions = {};
if (fs.existsSync(versionsPath)) {
  syncedVersions = JSON.parse(fs.readFileSync(versionsPath, 'utf8'));
}

const results = [];
for (const name of packageNames) {
  let latest = '';
  try {
    latest = execSync(`npm view ${name} version`, { encoding: 'utf8' }).trim();
  } catch {
    latest = '';
  }
  const current = syncedVersions[name] || '';
  results.push({ name, latest, current, changed: current !== latest });
}

const changed = results.filter((r) => r.changed);
const skip = changed.length === 0;

let title = 'chore: sync template skills from npm';
if (changed.length === 1) {
  title = `chore: sync template skills from npm (${changed[0].name}@${changed[0].latest})`;
} else if (changed.length > 1) {
  title = `chore: sync template skills from npm (${changed.length} packages)`;
}

const bodyLines = [
  'Synced skills from template npm packages into `skills/salesforce-webapp-*/`.',
  '',
  ...changed.map(
    (r) => `- **${r.name}**: ${r.current || 'none'} → ${r.latest}`
  ),
  '',
  'Same flow as running locally: `npm install` then `npm run sync-template-skills`.',
];
const body = bodyLines.join('\n');

const out = process.env.GITHUB_OUTPUT;
if (out) {
  const delim = 'EOF' + Math.random().toString(36).slice(2);
  fs.appendFileSync(out, `skip=${skip}\n`, 'utf8');
  fs.appendFileSync(out, `title=${title}\n`, 'utf8');
  fs.appendFileSync(out, `body<<${delim}\n${body}\n${delim}\n`, 'utf8');
} else {
  console.log(JSON.stringify({ skip, title, results }, null, 2));
}
