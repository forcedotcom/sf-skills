#!/usr/bin/env node
// Deterministic Phase-0 scratch-directory creator for the Employee-agent
// create/activate flow.
//
// Phase-0 path selection + `mkdtemp` behavior are deterministic and must not
// live in workflow prose (authoring standard A9).
//
// The scratch dir MUST stay OUTSIDE the harness's scored `${outputDir}` tree.
// Several phases capture raw `sf api request rest` stdout, and that command is
// in beta — it prints beta/update/plugin diagnostics to STDERR. If an agent
// captures combined output (`2>&1`) instead of the documented `2>…err` split,
// that stderr preamble is merged into the captured file; a raw capture rooted
// under `${outputDir}` would then land in the eval's scored artifact set and
// fail the `core:json-valid` assertion even though the response body itself is
// well-formed JSON. So the scratch dir roots under `${TMPDIR}` (private,
// user-scoped), then `/tmp`, and only as an ultimate fallback (both temp bases
// unwritable) under the harness `${outputDir}`. `mkdtempSync` creates the run
// dir mode 0700 (owner-only) with a random suffix, so the world-writable `/tmp`
// parent is not a concern. Only the durable `${outputDir}/report.md` (written
// directly by render-report.mjs) is ever meant to be scored.
//
// Usage:
//   node create-scratch-dir.mjs [outputDir]
//
// Emits the absolute path of the created directory to stdout (a single line,
// trailing newline). Exit 0 on success, 3 when no candidate base is writable.

import { mkdtempSync } from 'node:fs';
import { join } from 'node:path';

const PREFIX = 'itsm-employee-agent.';

// Candidate scratch bases, in priority order. `${outputDir}` is LAST so
// transient captures never enter the scored tree except when no temp dir works.
const candidates = [];
const tmp = (process.env.TMPDIR ?? '').trim();
if (tmp) candidates.push(tmp);
candidates.push('/tmp');
const outputDir = (process.argv[2] ?? '').trim();
if (outputDir) candidates.push(outputDir);

let dir = null;
let lastErr = null;
for (const base of candidates) {
  try {
    dir = mkdtempSync(join(base, PREFIX));
    break;
  } catch (err) {
    lastErr = err;
  }
}

if (dir) {
  process.stdout.write(`${dir}\n`);
} else {
  process.stderr.write(`error: mkdtemp failed under all of [${candidates.join(', ')}]: ${lastErr?.message ?? 'no base dir'}\n`);
  process.exit(3);
}
