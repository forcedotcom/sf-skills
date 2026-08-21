#!/usr/bin/env node
// Deterministic idempotency / verification classifier for the Employee-agent create flow.
//
// Idempotency for this flow is keyed PRIMARILY on the TEMPLATE's own
// `botDefinitionId` — the platform's authoritative link from an `agent-templates`
// row to the live `BotDefinition` it was instantiated into — and FALLS BACK to a
// `DeveloperName`-keyed read when that row carries no `botDefinitionId`.
// The broad "IT Service Employee" agent is pre-provisioned+active under
// DeveloperName `IT_Service_Employee`, which does NOT match this skill's default
// collected developerName `IT_Service_Employee_Agent`; a DeveloperName-only read
// false-negatives on THAT agent (exists:false) and the create then collides on
// `apiName` with `DUPLICATE_VALUE` — hence botDefinitionId is the primary key.
// But botDefinitionId is back-filled onto the template row ONLY for platform-
// pre-provisioned agents: the ITSM create path never stamps `templateName`, so
// agents THIS skill creates keep a null template botDefinitionId forever, and a
// DeveloperName-keyed read is the reliable guard for them — used as the FALLBACK.
// (Preflight emits `template.botDefinitionId`; the workflow passes it as the
// primary key and the collected developerName as the fallback key.)
//
// This classifier consumes the raw JSON of a `sf data query ... --json` read of
// BotDefinition (BY Id primarily, BY DeveloperName on the fallback) and decides
// whether the agent already exists — and if so, whether its latest BotVersion is
// Inactive (so the workflow can offer to activate it instead of creating a
// duplicate). This is the deterministic decision that gates whether the write is
// skipped — it MUST NOT be interpreted by the model in prose (authoring standard A9).
//
// Usage:
//   node classify-agent-existence.mjs <bot-query.json> <botDefinitionId> [developerName]
//
// When <botDefinitionId> is empty, `-`, or the literal `null`/`undefined` (the
// matched template carries no botDefinitionId), the classifier FALLS BACK to
// keying on <developerName>, and <bot-query.json> must be a DeveloperName-keyed
// BotDefinition read: self-created agents are never back-filled with a
// botDefinitionId (the ITSM create path doesn't stamp `templateName`, so the
// platform never joins the agent-templates row to its BotDefinition), so
// DeveloperName is the only idempotency guard left for them. Only when BOTH
// <botDefinitionId> and <developerName> are absent is exists:false emitted
// without reading a query file. Otherwise <bot-query.json> is a FILE PATH to the
// stdout captured from:
//   sf data query -q "SELECT Id,DeveloperName,MasterLabel,
//     (SELECT Id,Status FROM BotVersions ORDER BY VersionNumber DESC LIMIT 1)
//     FROM BotDefinition WHERE Id='<botDefinitionId>' OR DeveloperName='<developerName>'" \
//     --target-org <org> --json > file.json
// (The present-id read ORs in DeveloperName so a DANGLING template→BotDefinition
// link — a botDefinitionId whose target BotDefinition was since deleted — still
// surfaces the live same-name agent: the classifier tries the Id first, then
// falls back to the name on the SAME records. The pure FALLBACK read, taken when
// the template row carries no botDefinitionId at all, keys on
// `DeveloperName='<developerName>'` only; everything else is identical.
// `sf data query --json` wraps results in a `.result.records[]` envelope. The
// BotVersions subquery is required so this classifier can see the latest
// version's Status — a query without it leaves latestVersionStatus null and
// needsActivation false, which silently disables the reactivation path.)
//
// Emits a single JSON object to stdout:
//   { exists, count, matchedBy, agentId, botDefinitionId, developerName, latestVersionId, latestVersionStatus, needsActivation }
// where exists is true|false, developerName is the ACTUAL DeveloperName read
// from the matched record (e.g. `IT_Service_Employee`) — NOT the collected
// guess — so the report surfaces the live agent's real identity;
// latestVersionStatus is "Active"|"Inactive"|null (null means no BotVersion
// child row was returned), and needsActivation is true only when exists is true
// AND latestVersionStatus is "Inactive" — the signal to offer activating the
// existing version instead of creating a new agent. `matchedBy` is
// "botDefinitionId" | "developerName" | null, recording which key hit. Exit code
// is always 0 on a parseable body (or when neither key is supplied); the verdict
// is carried in the payload. On an unparseable/failed query it exits 3 so the
// workflow surfaces the raw error rather than assuming NOT-EXISTS.

import { readFileSync } from 'node:fs';

const [queryPath, rawBotDefinitionId, rawDeveloperName] = process.argv.slice(2);
if (!queryPath) {
  process.stderr.write('usage: node classify-agent-existence.mjs <bot-query.json> <botDefinitionId> [developerName]\n');
  process.exit(2);
}

// Salesforce Ids compare on their case-sensitive 15-char base (the trailing 3
// chars are a case-normalizing checksum), so a 15-char and an 18-char form of
// the same record compare equal on the first 15 chars.
function idKey(v) {
  return String(v ?? '').trim().slice(0, 15);
}

function notSet(v) {
  const s = String(v ?? '').trim().toLowerCase();
  return s === '' || s === '-' || s === 'null' || s === 'undefined';
}

const botDefinitionId = String(rawBotDefinitionId ?? '').trim();
const developerName = String(rawDeveloperName ?? '').trim();
const noId = notSet(botDefinitionId);
const noName = notSet(developerName);

const NOT_EXISTS = {
  exists: false,
  count: 0,
  matchedBy: null,
  agentId: null,
  botDefinitionId: null,
  developerName: null,
  latestVersionId: null,
  latestVersionStatus: null,
  needsActivation: false,
};

// Nothing to key on — no botDefinitionId AND no developerName fallback. There is
// no way to detect an existing agent, so this is the create path. (The workflow
// should always pass the collected developerName so the fallback below can run;
// this bare branch only fires when neither key is supplied.)
if (noId && noName) {
  process.stdout.write(JSON.stringify(NOT_EXISTS, null, 2) + '\n');
  process.exit(0);
}

let data;
try {
  const text = readFileSync(queryPath, 'utf8').trim();
  data = text ? JSON.parse(text) : null;
} catch {
  process.stderr.write(`error: could not read/parse ${queryPath}\n`);
  process.exit(3);
}

// A failed `sf data query --json` has status !== 0 (e.g. malformed SOQL, auth error).
// Do NOT treat that as "agent does not exist" — surface it.
if (!data || (typeof data.status === 'number' && data.status !== 0) || data.result === undefined) {
  process.stderr.write('error: query did not return a results envelope; surface the raw CLI error and stop\n');
  process.exit(3);
}

const records = Array.isArray(data.result?.records) ? data.result.records : [];

// PRIMARY key: the template's `botDefinitionId` (the platform's authoritative
// template→BotDefinition link) — catches the pre-provisioned broad agent whose
// live DeveloperName differs from this skill's collected guess.
// FALLBACK: the collected DeveloperName. Self-created agents are NOT
// back-filled — the ITSM create path never stamps `templateName`, so the
// platform never joins the agent-templates row to its BotDefinition and
// `botDefinitionId` stays null on every later read — so DeveloperName is their
// only guard. We ALSO fall back to DeveloperName when a PRESENT botDefinitionId
// matches nothing (a dangling link whose target BotDefinition was deleted): the
// present-id Phase-2 SOQL reads `WHERE Id=... OR DeveloperName=...`, so a stale
// link still surfaces the live same-name agent instead of slipping through to the
// create path and colliding with DUPLICATE_VALUE. Try the Id first, then the
// name; each filter is self-checking on top of the SOQL WHERE so a wrong-keyed
// read can't false-positive.
let matches = [];
let matchedBy = null;
if (!noId) {
  const wantedIdKey = idKey(botDefinitionId);
  matches = records.filter((r) => idKey(r?.Id) === wantedIdKey);
  if (matches.length) matchedBy = 'botDefinitionId';
}
if (!matches.length && !noName) {
  // DeveloperName uniqueness is case-insensitive; compare accordingly.
  const wantedName = developerName.toLowerCase();
  matches = records.filter((r) => String(r?.DeveloperName ?? '').trim().toLowerCase() === wantedName);
  if (matches.length) matchedBy = 'developerName';
}
const exists = matches.length > 0;

// The BotVersions child subquery (if present in the SOQL) surfaces the latest
// version's Status so we can tell "already created and active" apart from
// "already created but inactive" — the latter should offer reactivation
// instead of a silent ALREADY-CREATED skip. The actual BotVersion status is
// authoritative over the template's `isActivated` flag.
const latestVersion = exists ? matches[0]?.BotVersions?.records?.[0] ?? null : null;
const latestVersionStatus = latestVersion?.Status ?? null;
const needsActivation = exists && latestVersionStatus === 'Inactive';

process.stdout.write(JSON.stringify({
  exists,
  count: matches.length,
  // Which key matched — `botDefinitionId` (primary) or `developerName` (the
  // fallback for self-created agents). null when nothing matched.
  matchedBy: exists ? matchedBy : null,
  agentId: exists ? (matches[0].Id ?? null) : null,
  // On a DeveloperName-fallback hit this surfaces the live BotDefinition Id the
  // template row was missing; on the Id path it echoes the queried id.
  botDefinitionId: exists ? (matches[0].Id ?? null) : (noId ? null : botDefinitionId),
  developerName: exists ? (matches[0].DeveloperName ?? null) : null,
  latestVersionId: latestVersion?.Id ?? null,
  latestVersionStatus,
  needsActivation,
}, null, 2) + '\n');
