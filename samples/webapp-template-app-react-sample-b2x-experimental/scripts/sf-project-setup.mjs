#!/usr/bin/env node
/**
 * Run from SFDX project root: install dependencies, build, and launch the dev server
 * for the web app in force-app/main/default/webapplications/.
 *
 * Usage: npm run sf-project-setup
 * (from the directory that contains force-app/ and sfdx-project.json)
 */

import { spawnSync } from 'node:child_process';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { readdirSync, existsSync, readFileSync } from 'node:fs';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(__dirname, '..');

function resolveWebapplicationsDir() {
  const sfdxPath = resolve(ROOT, 'sfdx-project.json');
  if (!existsSync(sfdxPath)) {
    console.error('Error: sfdx-project.json not found at project root.');
    process.exit(1);
  }
  const sfdxProject = JSON.parse(readFileSync(sfdxPath, 'utf8'));
  const pkgDir = sfdxProject?.packageDirectories?.[0]?.path;
  if (!pkgDir) {
    console.error('Error: No packageDirectories[].path found in sfdx-project.json.');
    process.exit(1);
  }
  return resolve(ROOT, pkgDir, 'main', 'default', 'webapplications');
}

function discoverWebappDir() {
  const webapplicationsDir = resolveWebapplicationsDir();
  if (!existsSync(webapplicationsDir)) {
    console.error(`Error: webapplications directory not found: ${webapplicationsDir}`);
    process.exit(1);
  }
  const entries = readdirSync(webapplicationsDir, { withFileTypes: true });
  const dirs = entries.filter((e) => e.isDirectory() && !e.name.startsWith('.'));
  if (dirs.length === 0) {
    console.error(`Error: No web app folder found under ${webapplicationsDir}`);
    process.exit(1);
  }
  if (dirs.length > 1) {
    console.log(`Multiple web apps found; using first: ${dirs[0].name}`);
  }
  return resolve(webapplicationsDir, dirs[0].name);
}

function run(label, cmd, args, opts) {
  console.log(`\n--- ${label} ---\n`);
  const result = spawnSync(cmd, args, { stdio: 'inherit', ...opts });
  if (result.status !== 0) {
    process.exit(result.status ?? 1);
  }
}

const webappDir = discoverWebappDir();
console.log('SFDX project root:', ROOT);
console.log('Web app directory:', webappDir);

run('npm install', 'npm', ['install', '--registry', 'https://registry.npmjs.org/'], { cwd: webappDir });
run('npm run build', 'npm', ['run', 'build'], { cwd: webappDir });
console.log('\n--- Launching dev server (Ctrl+C to stop) ---\n');
run('npm run dev', 'npm', ['run', 'dev'], { cwd: webappDir });
