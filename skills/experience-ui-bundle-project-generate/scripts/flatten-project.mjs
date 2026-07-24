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

import fs from "node:fs";
import path from "node:path";

const [src, dest] = process.argv.slice(2);

if (!src || !dest) {
  console.error("usage: node <skill_dir>/scripts/flatten-project.mjs <srcDir> <destDir>");
  process.exit(1);
}

if (!fs.existsSync(path.join(src, "sfdx-project.json"))) {
  console.error("generated project has no sfdx-project.json: " + src);
  process.exit(1);
}

for (const entry of fs.readdirSync(src)) {
  const target = path.join(dest, entry);
  fs.rmSync(target, { recursive: true, force: true });
  fs.renameSync(path.join(src, entry), target);
}
