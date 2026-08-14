#!/usr/bin/env node
// Deterministic target-org alias resolver for automation-sandbox-post-copy-configure.
//
// Resolves the org alias that goes into the summary header so it never
// contains an unresolved `$SF_TARGET_ORG` / `<env:SF_TARGET_ORG>` placeholder
// (authoring standard A9 — this is deterministic string substitution, not
// model judgment).
//
// Precedence:
//   1. $SF_TARGET_ORG (set by the eval harness or the caller)
//   2. `sf config get target-org --json` → .result[0].value
//
// Usage:
//   node resolve-target-org.mjs
//
// Emits to stdout (single JSON object):
//   { "alias": "<value>", "source": "env|sf-config" }
//   { "error":  "<message>" }
//
// Exit code 0 when an alias is resolved; 1 when neither source yields one
// (so the caller can hard-fail before writing a report with a broken header).

import { execFileSync } from 'node:child_process';

const envAlias = process.env.SF_TARGET_ORG?.trim();
if (envAlias) {
  process.stdout.write(JSON.stringify({ alias: envAlias, source: 'env' }) + '\n');
  process.exit(0);
}

try {
  const raw = execFileSync('sf', ['config', 'get', 'target-org', '--json'], {
    encoding: 'utf-8',
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  const parsed = JSON.parse(raw);
  const alias = parsed?.result?.[0]?.value;
  if (typeof alias === 'string' && alias.trim().length > 0) {
    process.stdout.write(JSON.stringify({ alias: alias.trim(), source: 'sf-config' }) + '\n');
    process.exit(0);
  }
  process.stdout.write(
    JSON.stringify({
      error: 'no target-org configured — set $SF_TARGET_ORG or run `sf config set target-org=<alias>`',
    }) + '\n',
  );
  process.exit(1);
} catch (err) {
  const detail = err instanceof Error ? err.message : String(err);
  process.stdout.write(
    JSON.stringify({
      error: `sf config get target-org failed: ${detail.slice(0, 400)}`,
    }) + '\n',
  );
  process.exit(1);
}
