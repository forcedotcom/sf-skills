#!/usr/bin/env node
// Resolve the existing path of a UIBundle's meta XML file.
//
// UIBundle metadata may live at either the nested bundle-style path
// (uiBundles/{appName}/{appName}.uibundle-meta.xml) or, in older/hand-authored
// projects, the flat path (uiBundles/{appName}.uibundle-meta.xml). This script
// performs the deterministic file-existence check and prints whichever path
// already exists, preferring the nested layout.
//
// Always invoke via `node` (never as a bare executable) so this works on
// Windows cmd/PowerShell as well as macOS/Linux/Git Bash.
//
// Usage: node scripts/resolve-uibundle-path.mjs <appName>
//
// Exit 0: existing meta XML found — its path is printed to stdout.
// Exit 1: appName argument missing, or no .uibundle-meta.xml found for it.

import fs from "node:fs";
import path from "node:path";

const APP = process.argv[2] ?? "";

if (!APP) {
  console.error("ERROR: appName argument is required");
  process.exit(1);
}

// appName is interpolated into filesystem paths, so restrict it to a plain
// bundle name. Rejecting separators and "." blocks traversal (e.g. "../x")
// out of uiBundles/ and keeps the printed path inside it.
if (!/^[A-Za-z0-9][A-Za-z0-9_-]*$/.test(APP)) {
  console.error(
    "ERROR: invalid appName (allowed: letters, digits, '_' and '-'; must start with a letter or digit)"
  );
  process.exit(1);
}

const NESTED = path.join("uiBundles", APP, `${APP}.uibundle-meta.xml`);
const FLAT = path.join("uiBundles", `${APP}.uibundle-meta.xml`);

if (fs.existsSync(NESTED) && fs.statSync(NESTED).isFile()) {
  console.log(NESTED);
  process.exit(0);
} else if (fs.existsSync(FLAT) && fs.statSync(FLAT).isFile()) {
  console.log(FLAT);
  process.exit(0);
} else {
  console.error(`ERROR: no .uibundle-meta.xml found for ${APP}`);
  process.exit(1);
}
