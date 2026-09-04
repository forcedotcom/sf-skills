#!/usr/bin/env node
// Precondition classifier: BotDefinition+latest BotVersion query JSON → { exists, active, ready, ... }; ready only when exists && active; exit 3 on unparseable. Query/output shape: references/classifier-contracts.md.

import { readFileSync } from 'node:fs';

const [queryPath, developerName] = process.argv.slice(2);
if (!queryPath || !developerName) {
  process.stderr.write('usage: node classify-agent-active.mjs <bot-query.json> <developerName>\n');
  process.exit(2);
}

let data;
try {
  const text = readFileSync(queryPath, 'utf8').trim();
  data = text ? JSON.parse(text) : null;
} catch {
  process.stderr.write(`error: could not read/parse ${queryPath}\n`);
  process.exit(3);
}

if (!data || (typeof data.status === 'number' && data.status !== 0) || data.result === undefined) {
  process.stderr.write('error: query did not return a results envelope; surface the raw CLI error and stop\n');
  process.exit(3);
}

const records = Array.isArray(data.result?.records) ? data.result.records : [];
const wantedLower = String(developerName).toLowerCase();
const matches = records.filter((r) => String(r?.DeveloperName ?? '').toLowerCase() === wantedLower);
const exists = matches.length > 0;

const latestVersion = exists ? matches[0]?.BotVersions?.records?.[0] ?? null : null;
const latestVersionStatus = latestVersion?.Status ?? null;
const active = exists && latestVersionStatus === 'Active';

let reason;
if (!exists) reason = 'agent-not-found';
else if (!active) reason = 'agent-inactive';
else reason = 'ready';

process.stdout.write(JSON.stringify({
  exists,
  active,
  agentId: exists ? (matches[0].Id ?? null) : null,
  developerName,
  latestVersionId: latestVersion?.Id ?? null,
  latestVersionStatus,
  ready: exists && active,
  reason,
}, null, 2) + '\n');
