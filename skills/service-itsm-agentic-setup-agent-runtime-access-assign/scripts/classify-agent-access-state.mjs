#!/usr/bin/env node
// Deterministic idempotency classifier for the custom `Agent_Access` permission
// set and its per-agent SetupEntityAccess grants.
//
// The Agent Access concern has two writes that must be idempotent:
//   1. Create the `Agent_Access` PermissionSet (Name=Agent_Access,
//      Label="Agent Access") — only if it does not already exist.
//   2. For each CHOSEN activated agent, add a SetupEntityAccess row
//      { ParentId: <Agent_Access permset Id>, SetupEntityId: <BotDefinition Id> }
//      — only if a grant for that agent is not already present.
//      (SetupEntityType is NOT sent in the POST body — it is not createable and
//       is derived from the 0Xx key prefix; it IS filterable on the read.)
//
// Reads:
//   1. `agent-access-permset.json` — `sf data query --json` capture of
//        SELECT Id, Name, Label FROM PermissionSet WHERE Name='Agent_Access'
//   2. `sea-existing.json` OR the literal sentinel `NO-PERMSET`:
//        - permset present ⇒ pass the capture of
//            SELECT SetupEntityId FROM SetupEntityAccess
//            WHERE ParentId='<permsetId>' AND SetupEntityType='BotDefinition'
//        - permset absent ⇒ pass `NO-PERMSET` (there is no parent to query yet).
//   3. `chosenAgentIds-csv` — comma-separated BotDefinition Ids the user selected.
//
// Usage:
//   node classify-agent-access-state.mjs <agent-access-permset.json> <sea-existing.json | NO-PERMSET> <chosenAgentIds-csv>
//
// Emits a single JSON object to stdout:
//   { permsetExists, permsetId, chosenAgentIds, grantedAgentIds, missingAgentIds,
//     needsCreate, needsGrants,
//     verdict: "NEEDS-WORK" | "ALREADY-COMPLETE" | "CANNOT-CONFIRM",
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

const argv = process.argv.slice(2).filter((a) => a !== undefined && a !== '');
if (argv.length < 3) {
  process.stderr.write('usage: node classify-agent-access-state.mjs <agent-access-permset.json> <sea-existing.json | NO-PERMSET> <chosenAgentIds-csv>\n');
  process.exit(2);
}
const [permsetPath, seaArg, chosenCsv] = argv;
const chosenAgentIds = chosenCsv.split(',').map((s) => s.trim()).filter(Boolean);

function cannotConfirm(reasons) {
  process.stdout.write(JSON.stringify({
    permsetExists: null, permsetId: null, chosenAgentIds,
    grantedAgentIds: [], missingAgentIds: [],
    needsCreate: null, needsGrants: null,
    verdict: 'CANNOT-CONFIRM', reasons,
  }, null, 2) + '\n');
  process.exit(0);
}

if (chosenAgentIds.length === 0) {
  cannotConfirm(['no chosen agent Ids supplied — pass the comma-separated BotDefinition Ids the user selected.']);
}

const permset = readEnvelope(permsetPath);
if (!permset.ok) cannotConfirm([permset.reason]);

const permsetRow = permset.records.find((r) => r?.Name === 'Agent_Access') ?? null;
const permsetExists = !!permsetRow;
const permsetId = permsetExists ? (permsetRow.Id ?? null) : null;

let grantedAgentIds = [];
if (permsetExists) {
  if (seaArg === 'NO-PERMSET') {
    cannotConfirm(['Agent_Access permset exists but the SetupEntityAccess capture was passed as NO-PERMSET — query the existing grants and pass the real capture.']);
  }
  const sea = readEnvelope(seaArg);
  if (!sea.ok) cannotConfirm([sea.reason]);
  const grantedSet = new Set(sea.records.map((r) => r?.SetupEntityId).filter(Boolean));
  grantedAgentIds = chosenAgentIds.filter((id) => grantedSet.has(id));
}
// When the permset does not exist, seaArg must be NO-PERMSET and nothing is granted.

const missingAgentIds = chosenAgentIds.filter((id) => !grantedAgentIds.includes(id));
const needsCreate = !permsetExists;
const needsGrants = missingAgentIds.length > 0;

const reasons = [];
reasons.push(permsetExists
  ? `Agent_Access permission set already exists (${permsetId}).`
  : 'Agent_Access permission set does not exist yet — it will be created.');
reasons.push(`Chosen agents: ${chosenAgentIds.length}; already granted: ${grantedAgentIds.length}; missing grants: ${missingAgentIds.length}.`);

const verdict = (needsCreate || needsGrants) ? 'NEEDS-WORK' : 'ALREADY-COMPLETE';
reasons.push(verdict === 'NEEDS-WORK'
  ? 'Proceed to the confirm-to-write gate, then create the permset (if missing) and add one SetupEntityAccess grant per missing agent.'
  : 'The Agent_Access permset exists and already grants every chosen agent — no SetupEntityAccess writes needed (still assign the permset to the target user(s) if not yet assigned).');

process.stdout.write(JSON.stringify({
  permsetExists, permsetId, chosenAgentIds, grantedAgentIds, missingAgentIds,
  needsCreate, needsGrants, verdict, reasons,
}, null, 2) + '\n');
