#!/usr/bin/env node
// Deterministic classifier for the ACTIVATED agents a user needs access to.
//
// Reads ONE input:
//   - BotDefinition query capture (from `sf data query --json`) shaped as:
//       SELECT Id, DeveloperName, MasterLabel,
//              (SELECT Status FROM BotVersions WHERE Status='Active')
//       FROM BotDefinition WHERE Type='InternalCopilot'
//     Every NGA / Agentforce agent is a BotDefinition with Type='InternalCopilot';
//     an agent is ACTIVATED iff it has at least one BotVersion with Status='Active'
//     (the child subquery returns ≥1 record).
//
// The Agent Access custom permset should grant access ONLY to activated agents,
// so this classifier separates activated from inactive and hands the caller the
// activated set to present for a multi-select.
//
// Usage:
//   node classify-activated-agents.mjs <bot-definitions.json>
//
// Emits a single JSON object to stdout:
//   { agents: [ { Id, DeveloperName, MasterLabel, active } ],
//     activatedAgents: [ { Id, DeveloperName, MasterLabel } ],
//     inactiveAgents:  [ { Id, DeveloperName, MasterLabel } ],
//     verdict: "AGENTS-FOUND" | "NONE-ACTIVE" | "CANNOT-CONFIRM",
//     reasons: [...] }
// Exit is always 0 on parseable bodies; verdict carries the decision. Exit 2 on
// missing argv.

import { readFileSync } from 'node:fs';

function readEnvelope(path) {
  try {
    const text = readFileSync(path, 'utf8').trim();
    if (!text) return { ok: false, reason: `empty file: ${path}` };
    const data = JSON.parse(text);
    if (!data || typeof data !== 'object') return { ok: false, reason: `non-object JSON at ${path}` };
    if (typeof data.status === 'number' && data.status !== 0) {
      return { ok: false, reason: `sf data query at ${path} failed with status ${data.status}` };
    }
    const records = Array.isArray(data.result?.records) ? data.result.records : null;
    if (!records) return { ok: false, reason: `missing result.records[] at ${path}` };
    return { ok: true, records };
  } catch (e) {
    return { ok: false, reason: `unreadable/invalid JSON at ${path}: ${e?.message ?? e}` };
  }
}

const [botPath] = process.argv.slice(2);
if (!botPath) {
  process.stderr.write('usage: node classify-activated-agents.mjs <bot-definitions.json>\n');
  process.exit(2);
}

const bots = readEnvelope(botPath);
if (!bots.ok) {
  process.stdout.write(JSON.stringify({
    agents: [], activatedAgents: [], inactiveAgents: [],
    verdict: 'CANNOT-CONFIRM',
    reasons: [bots.reason],
  }, null, 2) + '\n');
  process.exit(0);
}

// A child-relationship subquery surfaces as a nested { totalSize, records:[...] }
// object, or null when there are no matching children.
function activeVersionCount(r) {
  const bv = r?.BotVersions;
  if (!bv) return 0;
  if (Array.isArray(bv.records)) return bv.records.length;
  if (typeof bv.totalSize === 'number') return bv.totalSize;
  return 0;
}

const agents = bots.records
  .filter((r) => r && typeof r.Id === 'string')
  .map((r) => ({
    Id: r.Id,
    DeveloperName: r.DeveloperName ?? null,
    MasterLabel: r.MasterLabel ?? null,
    active: activeVersionCount(r) > 0,
  }));

const activatedAgents = agents.filter((a) => a.active).map(({ active, ...rest }) => rest);
const inactiveAgents = agents.filter((a) => !a.active).map(({ active, ...rest }) => rest);

const reasons = [];
let verdict;
if (activatedAgents.length > 0) {
  verdict = 'AGENTS-FOUND';
  reasons.push(`Found ${activatedAgents.length} activated agent(s): ${activatedAgents.map((a) => a.MasterLabel ?? a.DeveloperName).join(', ')}.`);
  if (inactiveAgents.length > 0) {
    reasons.push(`Excluded ${inactiveAgents.length} agent(s) with no active version (not activated yet): ${inactiveAgents.map((a) => a.MasterLabel ?? a.DeveloperName).join(', ')}.`);
  }
  reasons.push('Present the activated agents for a multi-select — the Agent Access permset gets one SetupEntityAccess grant per chosen agent.');
} else {
  verdict = 'NONE-ACTIVE';
  if (agents.length === 0) {
    reasons.push('No InternalCopilot agents exist on this org — there is nothing for the Agent Access permset to grant. Create + activate an agent first.');
  } else {
    reasons.push(`${agents.length} InternalCopilot agent(s) exist but none has an active version — activate an agent before granting access.`);
  }
}

process.stdout.write(JSON.stringify({
  agents, activatedAgents, inactiveAgents, verdict, reasons,
}, null, 2) + '\n');
