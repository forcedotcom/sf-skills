#!/usr/bin/env node
/**
 * Sync webapp skills: pins @salesforce/webapp-template-app-react-sample-b2e-experimental
 * to the latest npm version, runs npm install, then copies skills from
 * dist/.a4drules/skills/ into skills/. Run from repo root.
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');
const { copyRecursive } = require('./lib/copy-recursive');

const PACKAGE_NAME = '@salesforce/webapp-template-app-react-sample-b2e-experimental';
const SKILLS_SRC = 'dist/.a4drules/skills';

const repoRoot = process.cwd();
const pkgPath = path.join(repoRoot, 'package.json');
const skillsDir = path.join(repoRoot, 'skills');

// ── Pin to latest npm version ────────────────────────────────────────
const pkg = JSON.parse(fs.readFileSync(pkgPath, 'utf8'));
const current = (pkg.devDependencies || {})[PACKAGE_NAME];
if (current && !current.startsWith('file:')) {
  let latest;
  try {
    latest = execSync(`npm view ${PACKAGE_NAME} version`, { encoding: 'utf8' }).trim();
  } catch (_) {
    console.warn(`Could not resolve ${PACKAGE_NAME} on npm, using current version.`);
    latest = current;
  }
  if (current !== latest) {
    console.log(`${PACKAGE_NAME}: ${current} -> ${latest}`);
    pkg.devDependencies[PACKAGE_NAME] = latest;
    fs.writeFileSync(pkgPath, JSON.stringify(pkg, null, 2) + '\n', 'utf8');
  }
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

/** Set front matter `name` in SKILL.md to match the destination folder name. */
function setSkillFrontMatterName(skillDir, destName) {
  const skillPath = path.join(skillDir, 'SKILL.md');
  if (!fs.existsSync(skillPath)) return;
  let content = fs.readFileSync(skillPath, 'utf8');
  content = content.replace(/^name:\s*.+$/m, `name: ${destName}`);
  fs.writeFileSync(skillPath, content, 'utf8');
}

const syncedDirs = [];
for (const srcName of fs.readdirSync(srcDir)) {
  const src = path.join(srcDir, srcName);
  if (!fs.statSync(src).isDirectory()) continue;

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
