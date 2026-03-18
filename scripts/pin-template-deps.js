#!/usr/bin/env node
/**
 * Pins each template skill devDependency in package.json to its latest npm version.
 * Run before `npm install` in CI so the lockfile and installed packages reflect
 * exact published versions instead of "*".
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');
const { matchingDeps } = require('./lib/package-utils');

const pkgPath = path.join(process.cwd(), 'package.json');
const pkg = JSON.parse(fs.readFileSync(pkgPath, 'utf8'));
const names = matchingDeps(pkg);

let changed = false;
for (const name of names) {
  const current = pkg.devDependencies[name];
  if (current.startsWith('file:')) continue;

  let latest;
  try {
    latest = execSync(`npm view ${name} version`, { encoding: 'utf8' }).trim();
  } catch (_) {
    console.warn(`Could not resolve ${name} on npm, skipping.`);
    continue;
  }

  if (current !== latest) {
    console.log(`${name}: ${current} -> ${latest}`);
    pkg.devDependencies[name] = latest;
    changed = true;
  }
}

if (changed) {
  fs.writeFileSync(pkgPath, JSON.stringify(pkg, null, 2) + '\n', 'utf8');
  console.log('Updated package.json with pinned versions.');
} else {
  console.log('All template deps already pinned to latest.');
}
