#!/usr/bin/env node
// Generate a `sf template generate project` starter and flatten it so the
// contents land directly at the target root (no `<name>/` wrapper subfolder).
//
// Usage: node <skill_dir>/scripts/generate-project.mjs <name> <dest> <template>
//   <name>     — project name passed to `sf template generate project --name`
//   <dest>     — target root directory the contents should land in
//                (so sfdx-project.json sits at <dest>/sfdx-project.json)
//   <template> — the `--template` flag value from the chosen framework reference
//
// Always invoke via `node` (never as a bare executable, and never wrap this
// in a bash/cmd/PowerShell script) so this works on Windows cmd/PowerShell
// as well as macOS/Linux/Git Bash. Pass <name>/<dest>/<template> as literal
// argv values — do not rely on shell variable assignment/interpolation
// (`$VAR` / `%VAR%` / `$env:VAR` differ per shell).
//
// Runs `sf` via spawnSync with shell:true so the platform's own shell
// resolves the CLI shim correctly (on Windows, globally-installed CLIs are
// usually `.cmd`/`.ps1` wrappers that spawn() cannot find without a shell).
//
// Exit 0 on success (project landed at <dest>).
// Exit 1 if `sf template generate project` fails, the generated project has
// no sfdx-project.json, or the flatten didn't result in a valid project root.

import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { flattenProject } from "./flatten-project.mjs";

const [name, dest, template] = process.argv.slice(2);

function fail(message) {
  console.error(message);
  process.exit(1);
}

if (!name || !dest || !template) {
  fail("usage: node <skill_dir>/scripts/generate-project.mjs <name> <dest> <template>");
}

fs.mkdirSync(dest, { recursive: true });

const result = spawnSync(
  "sf",
  ["template", "generate", "project", "--name", name, "--template", template, "--output-dir", dest],
  { stdio: "inherit", shell: true },
);

if (result.error) {
  fail(`ERROR: failed to run "sf template generate project": ${result.error.message}`);
}
if (result.status !== 0) {
  process.exit(result.status ?? 1);
}

const srcDir = path.join(dest, name);

if (!fs.existsSync(path.join(srcDir, "sfdx-project.json"))) {
  fail(`ERROR: generated project has no sfdx-project.json: ${srcDir}`);
}

try {
  flattenProject(srcDir, dest);
} catch (err) {
  fail(`ERROR: ${err.message}`);
}

// Remove the now-empty (or leftover) generated subfolder.
fs.rmSync(srcDir, { recursive: true, force: true });

const destProjectFile = path.join(dest, "sfdx-project.json");
if (!fs.existsSync(destProjectFile)) {
  fail(`FAILED: sfdx-project.json not found at ${destProjectFile} — flatten did not run correctly`);
}

console.log(`OK: project root landed at ${dest} (${destProjectFile})`);
process.exit(0);
