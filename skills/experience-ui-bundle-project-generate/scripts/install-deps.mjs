#!/usr/bin/env node
// Install dependencies for a generated UI bundle starter project: the
// project root `package.json`, plus each `package.json` under
// force-app/main/default/uiBundles/*/ (the toolchain the preview server
// loads). Then verify node_modules landed everywhere it was installed.
//
// Usage: node <skill_dir>/scripts/install-deps.mjs <dest>
//   <dest> — the project root (same value passed to generate-project.mjs)
//
// Always invoke via `node` (never as a bare executable, and never wrap this
// in a bash/cmd/PowerShell script) so this works on Windows cmd/PowerShell
// as well as macOS/Linux/Git Bash. Runs `npm install` via spawnSync with an
// explicit `cwd` (no `cd &&` subshell chaining) and shell:true so the
// platform's own shell resolves the `npm` CLI shim correctly.
//
// Exit 0 if every install succeeded (or there was nothing to install).
// Exit 1 with a summary of which installs failed — surface it, don't hand
// off a half-installed project.

import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";

const [dest] = process.argv.slice(2);

if (!dest) {
  console.error("usage: node <skill_dir>/scripts/install-deps.mjs <dest>");
  process.exit(1);
}

function npmInstall(cwd) {
  console.log(`Running "npm install" in ${cwd} ...`);
  const result = spawnSync("npm", ["install"], { cwd, stdio: "inherit", shell: true });
  if (result.error) {
    return `${cwd}: ${result.error.message}`;
  }
  if (result.status !== 0) {
    return `${cwd}: npm install exited with code ${result.status}`;
  }
  return null;
}

const failures = [];

// 1. Project root.
if (fs.existsSync(path.join(dest, "package.json"))) {
  const failure = npmInstall(dest);
  if (failure) failures.push(failure);
} else {
  console.error(`ERROR: no package.json found at project root: ${dest}`);
  failures.push(`${dest}: missing package.json`);
}

// 2. Each UI bundle.
const bundlesDir = path.join(dest, "force-app", "main", "default", "uiBundles");
const bundleDirs = fs.existsSync(bundlesDir)
  ? fs
      .readdirSync(bundlesDir, { withFileTypes: true })
      .filter((entry) => entry.isDirectory())
      .map((entry) => path.join(bundlesDir, entry.name))
  : [];

for (const bundleDir of bundleDirs) {
  if (fs.existsSync(path.join(bundleDir, "package.json"))) {
    const failure = npmInstall(bundleDir);
    if (failure) failures.push(failure);
  }
}

// 3. Verify node_modules landed everywhere it was installed.
console.log("\nVerifying installs:");
let allInstalled = true;
if (fs.existsSync(path.join(dest, "package.json"))) {
  const ok = fs.existsSync(path.join(dest, "node_modules"));
  console.log(`  ${ok ? "OK" : "MISSING"}: ${path.join(dest, "node_modules")}`);
  allInstalled = allInstalled && ok;
}
for (const bundleDir of bundleDirs) {
  if (fs.existsSync(path.join(bundleDir, "package.json"))) {
    const ok = fs.existsSync(path.join(bundleDir, "node_modules"));
    console.log(`  ${ok ? "OK" : "MISSING"}: ${path.join(bundleDir, "node_modules")}`);
    allInstalled = allInstalled && ok;
  }
}

if (failures.length > 0 || !allInstalled) {
  console.error("\nFAILED: one or more installs did not complete:");
  for (const failure of failures) {
    console.error(`  - ${failure}`);
  }
  process.exit(1);
}

console.log("\nOK: all dependencies installed.");
process.exit(0);
