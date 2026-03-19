#!/usr/bin/env node
/**
 * Sync webapp skills: pins b2e and b2x template packages to latest npm versions,
 * runs npm install, then copies skills from dist/.a4drules/skills/ into skills/.
 * Run from repo root.
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');
const { copyRecursive } = require('./lib/copy-recursive');

const TEMPLATE_PACKAGES = [
  '@salesforce/webapp-template-app-react-sample-b2e-experimental',
  '@salesforce/webapp-template-app-react-sample-b2x-experimental',
];
const PACKAGE_NAME = TEMPLATE_PACKAGES[0]; // used for syncing skills
const SKILLS_SRC = 'dist/.a4drules/skills';

const repoRoot = process.cwd();
const pkgPath = path.join(repoRoot, 'package.json');
const skillsDir = path.join(repoRoot, 'skills');

// ── Pin template packages to latest npm versions ────────────────────
const pkg = JSON.parse(fs.readFileSync(pkgPath, 'utf8'));
let pkgChanged = false;
for (const name of TEMPLATE_PACKAGES) {
  const current = (pkg.devDependencies || {})[name];
  if (!current || current.startsWith('file:')) continue;
  let latest;
  try {
    latest = execSync(`npm view ${name} version`, { encoding: 'utf8' }).trim();
  } catch (_) {
    console.warn(`Could not resolve ${name} on npm, using current version.`);
    continue;
  }
  if (current !== latest) {
    console.log(`${name}: ${current} -> ${latest}`);
    pkg.devDependencies[name] = latest;
    pkgChanged = true;
  }
}
if (pkgChanged) {
  fs.writeFileSync(pkgPath, JSON.stringify(pkg, null, 2) + '\n', 'utf8');
}

// ── Install ──────────────────────────────────────────────────────────
console.log('Installing dependencies...');
execSync('npm install', { cwd: repoRoot, stdio: 'inherit' });

// ── Sync skills ──────────────────────────────────────────────────────
const pkgRoot = path.join(repoRoot, 'node_modules', PACKAGE_NAME.replace('/', path.sep));
if (!fs.existsSync(pkgRoot)) {
  console.error(`Package not found at ${pkgRoot}.`);
  process.exit(1);
}

const srcDir = path.join(pkgRoot, SKILLS_SRC);
if (!fs.existsSync(srcDir)) {
  console.error(`Skills not found at ${srcDir}.`);
  process.exit(1);
}

if (!fs.existsSync(skillsDir)) fs.mkdirSync(skillsDir, { recursive: true });

function addWebappPrefix(name) {
  const parts = name.split('-');
  if (parts.length < 2) return name;
  if (parts[1] === 'webapp') return name;
  return parts[0] + '-webapp-' + parts.slice(1).join('-');
}

/** Dirs in skills/ that look like synced webapp skills (e.g. *-webapp-*, creating-webapp). */
function isSyncedWebappSkillDir(name) {
  return name.includes('webapp');
}

/** Set front matter `name` in SKILL.md to match the destination folder name. */
function setSkillFrontMatterName(skillDir, destName) {
  const skillPath = path.join(skillDir, 'SKILL.md');
  if (!fs.existsSync(skillPath)) return;
  let content = fs.readFileSync(skillPath, 'utf8');
  content = content.replace(/^name:\s*.+$/m, `name: ${destName}`);
  fs.writeFileSync(skillPath, content, 'utf8');
}

// ── Clean up: remove skills no longer in the package ───────────────────
const srcNames = fs.readdirSync(srcDir).filter((name) =>
  fs.statSync(path.join(srcDir, name)).isDirectory()
);
const currentDestNames = new Set(srcNames.map(addWebappPrefix));

for (const name of fs.readdirSync(skillsDir)) {
  const dirPath = path.join(skillsDir, name);
  if (!fs.statSync(dirPath).isDirectory()) continue;
  if (!isSyncedWebappSkillDir(name)) continue;
  if (currentDestNames.has(name)) continue;
  fs.rmSync(dirPath, { recursive: true });
  console.log(`Removed skills/${name}/ (no longer in package)`);
}

// ── Copy each skill from package ──────────────────────────────────────
const syncedDirs = [];
for (const srcName of srcNames) {
  const src = path.join(srcDir, srcName);
  const destName = addWebappPrefix(srcName);
  const dest = path.join(skillsDir, destName);
  if (fs.existsSync(dest)) fs.rmSync(dest, { recursive: true });
  copyRecursive(src, dest);
  setSkillFrontMatterName(dest, destName);
  syncedDirs.push(destName);
  console.log(`Synced skills/${destName}/`);
}

const version = JSON.parse(
  fs.readFileSync(path.join(pkgRoot, 'package.json'), 'utf8')
).version;
console.log(`Done — synced ${syncedDirs.length} skills from ${PACKAGE_NAME}@${version}.`);
