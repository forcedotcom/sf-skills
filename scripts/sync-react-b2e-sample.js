#!/usr/bin/env node
/**
 * Syncs source from @salesforce/webapp-template-app-react-sample-b2e-experimental
 * into samples/webapp-template-app-react-sample-b2e-experimental/.
 * Run from repo root after npm install. Same flow used locally and in CI.
 */

const fs = require('fs');
const path = require('path');
const { copyRecursive } = require('./lib/copy-recursive');

const PACKAGE_NAME = '@salesforce/webapp-template-app-react-sample-b2e-experimental';
const SAMPLE_DIR = path.join(process.cwd(), 'samples', 'webapp-template-app-react-sample-b2e-experimental');

const pkgRoot = path.join(process.cwd(), 'node_modules', PACKAGE_NAME.replace('/', path.sep));

if (!fs.existsSync(pkgRoot)) {
  console.error(`Package not found at ${pkgRoot}. Run "npm install" from repo root first.`);
  process.exit(1);
}

const pkgJsonPath = path.join(pkgRoot, 'package.json');
const pkgJson = JSON.parse(fs.readFileSync(pkgJsonPath, 'utf8'));
const version = pkgJson.version;

// Ensure sample dir exists and clear it (we replace with fresh copy from dist)
if (fs.existsSync(SAMPLE_DIR)) {
  for (const name of fs.readdirSync(SAMPLE_DIR)) {
    if (name === '.version') continue;
    const itemPath = path.join(SAMPLE_DIR, name);
    if (fs.statSync(itemPath).isDirectory()) {
      fs.rmSync(itemPath, { recursive: true });
    } else {
      fs.unlinkSync(itemPath);
    }
  }
} else {
  fs.mkdirSync(SAMPLE_DIR, { recursive: true });
}

// Copy dist/ contents into sample dir (package ships source in dist/)
const distPath = path.join(pkgRoot, 'dist');
if (fs.existsSync(distPath)) {
  for (const name of fs.readdirSync(distPath)) {
    copyRecursive(path.join(distPath, name), path.join(SAMPLE_DIR, name));
  }
}

// Copy LICENSE from package root
const licensePath = path.join(pkgRoot, 'LICENSE.txt');
if (fs.existsSync(licensePath)) {
  fs.copyFileSync(licensePath, path.join(SAMPLE_DIR, 'LICENSE.txt'));
}

// Write .version for version tracking (used by workflow and local)
fs.writeFileSync(path.join(SAMPLE_DIR, '.version'), version + '\n', 'utf8');

console.log(`Synced ${PACKAGE_NAME}@${version} to ${SAMPLE_DIR}`);
