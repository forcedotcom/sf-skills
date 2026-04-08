#!/usr/bin/env node
/**
 * Syncs source from @salesforce/ui-bundle-template-app-react-sample-b2x
 * into samples/ui-bundle-template-app-react-sample-b2x/.
 * Run from repo root after npm install. Same flow used locally and in CI.
 */

const fs = require('fs');
const path = require('path');

const PACKAGE_NAME = '@salesforce/ui-bundle-template-app-react-sample-b2x';
const SAMPLE_DIR = path.join(process.cwd(), 'samples', 'ui-bundle-template-app-react-sample-b2x');

const pkgRoot = path.join(process.cwd(), 'node_modules', PACKAGE_NAME.replace('/', path.sep));

if (!fs.existsSync(pkgRoot)) {
  console.error(`Package not found at ${pkgRoot}. Run "npm install" from repo root first.`);
  process.exit(1);
}

// Read version from the package we're syncing from
const pkgJsonPath = path.join(pkgRoot, 'package.json');
const pkgJson = JSON.parse(fs.readFileSync(pkgJsonPath, 'utf8'));
const version = pkgJson.version;

function copyRecursive(src, dest, excludeDirs = new Set(['node_modules', '.git'])) {
  const stat = fs.statSync(src);
  const basename = path.basename(src);
  if (excludeDirs.has(basename)) return;

  if (stat.isDirectory()) {
    if (!fs.existsSync(dest)) fs.mkdirSync(dest, { recursive: true });
    for (const name of fs.readdirSync(src)) {
      copyRecursive(path.join(src, name), path.join(dest, name), excludeDirs);
    }
  } else {
    fs.mkdirSync(path.dirname(dest), { recursive: true });
    fs.copyFileSync(src, dest);
  }
}

// Ensure sample dir exists and clear it (we replace with fresh copy from dist)
if (fs.existsSync(SAMPLE_DIR)) {
  for (const name of fs.readdirSync(SAMPLE_DIR)) {
    if (name === '.version') continue; // keep .version until we overwrite it
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

// Write .gitignore for the sample project
const gitignoreContent = `# This file is used for Git repositories to specify intentionally untracked files that Git should ignore.
# If you are not using git, you can delete this file. For more information see: https://git-scm.com/docs/gitignore
# For useful gitignore templates see: https://github.com/github/gitignore

# Salesforce cache
.sf/
.sfdx/
.localdevserver/
deploy-options.json

# LWC VSCode autocomplete
**/lwc/jsconfig.json

# LWC Jest coverage reports
coverage/

# Logs
logs
*.log
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# Dependency directories
node_modules/

# Eslint cache
.eslintcache

# MacOS system files
.DS_Store

# Windows system files
Thumbs.db
ehthumbs.db
[Dd]esktop.ini
$RECYCLE.BIN/

# Local environment variables
.env

# Python Salesforce Functions
**/__pycache__/
**/.venv/
**/venv/
`;
fs.writeFileSync(path.join(SAMPLE_DIR, '.gitignore'), gitignoreContent, 'utf8');

// Generate package-lock.json for the uiBundle
const { execSync } = require('child_process');
const uiBundleDir = path.join(SAMPLE_DIR, 'force-app', 'main', 'default', 'uiBundles', 'propertyrentalapp');
console.log(`Generating package-lock.json for uiBundles/propertyrentalapp`);
execSync('npm install --package-lock-only --ignore-scripts', { cwd: uiBundleDir, stdio: 'inherit' });

// Write .version for version tracking (used by workflow and local)
fs.writeFileSync(path.join(SAMPLE_DIR, '.version'), version + '\n', 'utf8');

console.log(`Synced ${PACKAGE_NAME}@${version} to ${SAMPLE_DIR}`);
