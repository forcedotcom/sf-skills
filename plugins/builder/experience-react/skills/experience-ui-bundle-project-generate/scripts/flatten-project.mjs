#!/usr/bin/env node
// Flatten a `sf template generate project` result into the target root.
//
// Usage: node <skill_dir>/scripts/flatten-project.mjs <srcDir> <destDir>
//   <srcDir>  — the generated project dir (the `$STAGE/$NAME` subfolder the CLI nests output under)
//   <destDir> — the target root the contents should land in (so sfdx-project.json sits at <destDir>/sfdx-project.json)
//
// Moves every generated entry (incl. dotfiles) from <srcDir> up into <destDir>, overwriting any
// existing file/dir of any type on conflict. Unrelated files already in <destDir> are left untouched
// — only the paths the template ships get replaced. The per-entry rmSync + renameSync is what
// guarantees the template's files win on conflict (including a file-vs-directory type mismatch).
// Requires Node ≥ 16.7 for rmSync.
//
// Always invoke via `node` (never as a bare executable) so this works on Windows cmd/PowerShell
// as well as macOS/Linux/Git Bash. Uses fs/path APIs only — no shell-out — so path separators and
// move semantics are correct on every OS.

import fs from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";

export function flattenProject(src, dest) {
  if (!fs.existsSync(path.join(src, "sfdx-project.json"))) {
    throw new Error("generated project has no sfdx-project.json: " + src);
  }

  for (const entry of fs.readdirSync(src)) {
    const target = path.join(dest, entry);
    fs.rmSync(target, { recursive: true, force: true });
    fs.renameSync(path.join(src, entry), target);
  }
}

function main() {
  const [src, dest] = process.argv.slice(2);

  if (!src || !dest) {
    console.error("usage: node <skill_dir>/scripts/flatten-project.mjs <srcDir> <destDir>");
    process.exit(1);
  }

  try {
    flattenProject(src, dest);
  } catch (err) {
    console.error(err.message);
    process.exit(1);
  }
}

// Only run as a CLI when invoked directly (not when imported by generate-project.mjs).
// pathToFileURL handles Windows drive letters/backslashes correctly (a manual
// `file://${path}` string would not).
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main();
}
