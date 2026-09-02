#!/usr/bin/env node
// Deterministic idempotency / verification classifier for the Fulfiller-agent create flow.
//
// Idempotency for this flow is keyed PRIMARILY on the TEMPLATE's own
// `botDefinitionId` — the platform's authoritative link from an `agent-templates`
// row to the live `BotDefinition` it was instantiated into — and FALLS BACK
// first to the BotDefinition's own `AgentTemplate` field (the OOTB, namespaced
// template API name it was instantiated from, e.g.
// `svc_itsm_intelligence__ITSrvcMgmtFulfiller`), then to a `DeveloperName`-keyed
// read.
// If the Fulfiller template was already instantiated under a DeveloperName that
// differs from this skill's default collected `IT_Service_Fulfiller_Agent`, a
// DeveloperName-only read false-negatives (exists:false) and the create then
// collides on `apiName` with `DUPLICATE_VALUE`. `AgentTemplate` closes that gap
// far more reliably than a display name would: it is the platform-stamped source
// template on the live BotDefinition, so it survives any DeveloperName rename and
// carries the namespace prefix the skill already knows (preflight `template.id`).
// The template-row `botDefinitionId` is back-filled ONLY for platform-
// pre-provisioned agents (the ITSM create path never stamps `templateName`, so
// the platform never joins the agent-templates row to its BotDefinition), and the
// Fulfiller is never pre-provisioned — so its template `botDefinitionId` is null
// on the first run and every run after. Self-created Fulfiller agents also carry
// a NULL `AgentTemplate` (the create path doesn't stamp the source template), so
// for the Fulfiller the DeveloperName-keyed read is the guard that actually
// protects this path; `AgentTemplate` is a defensive key that would catch a
// hypothetical pre-provisioned Fulfiller and keeps this classifier identical to
// the Employee one (where `AgentTemplate` IS the load-bearing catcher). (Preflight
// emits `template.botDefinitionId`, `template.id`, and the collected
// developerName; the workflow passes the botDefinitionId as the primary key,
// template.id as the AgentTemplate key, and the developerName as the fallback.)
//
// This classifier consumes the raw JSON of a `sf data query ... --json` read of
// BotDefinition (BY Id primarily, BY AgentTemplate then DeveloperName on the
// fallback) and decides
// whether the agent already exists — and if so, whether its latest BotVersion is
// Inactive (so the workflow can offer to activate it instead of creating a
// duplicate). This is the deterministic decision that gates whether the write is
// skipped — it MUST NOT be interpreted by the model in prose (authoring standard A9).
//
// Usage:
//   node classify-agent-existence.mjs <bot-query.json> <botDefinitionId> [developerName] [agentTemplate]
//
// When <botDefinitionId> is empty, `-`, or the literal `null`/`undefined` (the
// matched template carries no botDefinitionId), the classifier FALLS BACK to
// keying on <agentTemplate> (the source template API name), and then to
// <developerName> when the AgentTemplate misses too. <bot-query.json> must
// therefore be a read that ORs all three keys together: self-created agents are
// never back-filled with a botDefinitionId AND carry a null AgentTemplate (the
// ITSM create path doesn't stamp `templateName`), so DeveloperName is their only
// idempotency guard; a pre-provisioned agent whose live DeveloperName differs from
// this skill's collected guess is caught by AgentTemplate. Only when ALL of
// <botDefinitionId>, <agentTemplate>, and <developerName> are absent is
// exists:false emitted without reading a query file. Otherwise <bot-query.json> is
// a FILE PATH to the stdout captured from:
//   sf data query -q "SELECT Id,DeveloperName,MasterLabel,AgentTemplate,
//     (SELECT Id,Status FROM BotVersions ORDER BY VersionNumber DESC LIMIT 1)
//     FROM BotDefinition WHERE Id='<botDefinitionId>' OR AgentTemplate='<agentTemplate>'
//       OR DeveloperName='<developerName>'" \
//     --target-org <org> --json > file.json
// (The present-id read ORs in AgentTemplate AND DeveloperName so a DANGLING
// template→BotDefinition link — a botDefinitionId whose target BotDefinition was
// since deleted — still surfaces the live agent: the classifier tries the Id
// first, then the AgentTemplate, then the DeveloperName on the SAME records. The
// pure FALLBACK read, taken when the template row carries no botDefinitionId at
// all, keys on `AgentTemplate='<agentTemplate>' OR DeveloperName='<developerName>'`;
// everything else is identical.
// `sf data query --json` wraps results in a `.result.records[]` envelope. The
// BotVersions subquery is required so this classifier can see the latest
// version's Status — a query without it leaves latestVersionStatus null and
// needsActivation false, which silently disables the reactivation path.)
//
// Emits a single JSON object to stdout:
//   { exists, count, matchedBy, agentId, botDefinitionId, developerName, latestVersionId, latestVersionStatus, needsActivation }
// where exists is true|false, developerName is the ACTUAL DeveloperName read
// from the matched record (NOT the collected guess `IT_Service_Fulfiller_Agent`)
// — so the report surfaces the live agent's real identity;
// latestVersionStatus is "Active"|"Inactive"|null (null means no BotVersion
// child row was returned), and needsActivation is true only when exists is true
// AND latestVersionStatus is "Inactive" — the signal to offer activating the
// existing version instead of creating a new agent. `matchedBy` is
// "botDefinitionId" | "agentTemplate" | "developerName" | null, recording which
// key hit. Exit code
// is always 0 on a parseable body (or when neither key is supplied); the verdict
// is carried in the payload. On an unparseable/failed query it exits 3 so the
// workflow surfaces the raw error rather than assuming NOT-EXISTS.

import { readFileSync } from 'node:fs';

const [queryPath, rawBotDefinitionId, rawDeveloperName, rawAgentTemplate] = process.argv.slice(2);
if (!queryPath) {
  process.stderr.write('usage: node classify-agent-existence.mjs <bot-query.json> <botDefinitionId> [developerName] [agentTemplate]\n');
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
const agentTemplate = String(rawAgentTemplate ?? '').trim();
const noId = notSet(botDefinitionId);
const noName = notSet(developerName);
const noTemplate = notSet(agentTemplate);

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

// Nothing to key on — no botDefinitionId AND no AgentTemplate fallback AND no
// DeveloperName fallback. There is no way to detect an existing agent, so this is
// the create path. (The workflow should always pass the collected developerName
// and the template's id/AgentTemplate so the fallbacks below can run; this bare
// branch only fires when none of the three keys is supplied.)
if (noId && noTemplate && noName) {
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
// template→BotDefinition link) — catches a pre-provisioned agent whose live
// DeveloperName differs from this skill's collected guess. For the Fulfiller this
// branch is defensive: the template `botDefinitionId` is null on every run (the
// Fulfiller is never pre-provisioned and this skill's create path never stamps
// `templateName`), so in practice the DeveloperName fallback below is what fires.
// The matching LOGIC here is kept identical to the Employee classifier on
// purpose — one shared matching contract, so the two can't drift and a future
// platform change that DOES populate the Fulfiller's botDefinitionId/AgentTemplate
// is handled correctly rather than silently mismatched; see that script's header
// for the pre-provisioned rationale it exercises.
// FALLBACK: the BotDefinition's own `AgentTemplate`, then the collected
// DeveloperName. `AgentTemplate` is the OOTB source-template API name the platform
// stamps on a template-instantiated agent — the reliable "an agent from THIS
// template already exists" signal for pre-provisioned agents, independent of any
// DeveloperName rename. Self-created agents are NOT stamped (the ITSM create path
// never sets `templateName`), so their `AgentTemplate` is null and DeveloperName
// is their guard. We ALSO fall back this way when a PRESENT botDefinitionId
// matches nothing (a dangling link whose target BotDefinition was deleted): the
// present-id Phase-2 SOQL reads `WHERE Id=... OR AgentTemplate=... OR
// DeveloperName=...`, so a stale link still surfaces the live agent instead of
// slipping through to the create path and colliding with DUPLICATE_VALUE. Try the
// Id first, then the template, then the name; each filter is self-checking on top
// of the SOQL WHERE so a wrong-keyed read can't false-positive.
let matches = [];
let matchedBy = null;
if (!noId) {
  const wantedIdKey = idKey(botDefinitionId);
  matches = records.filter((r) => idKey(r?.Id) === wantedIdKey);
  if (matches.length) matchedBy = 'botDefinitionId';
}
// FIRST FALLBACK: the BotDefinition's `AgentTemplate` (source template API name).
// When a live agent was instantiated from this template under a DeveloperName
// that differs from this skill's collected guess AND its template row carries no
// botDefinitionId, the Id and DeveloperName keys both miss and the create then
// collides with DUPLICATE_VALUE. `AgentTemplate` is the platform-stamped source
// template, so matching on it recovers that live agent reliably. SOQL text
// comparison is case-insensitive, so compare the same way. `AgentTemplate` is NOT
// unique (a template can be instantiated more than once), so if more than one
// record shares it we keep them all but surface an Active version first (see
// below) — the report should treat the already-active one as the real match.
if (!matches.length && !noTemplate) {
  const wantedTemplate = agentTemplate.toLowerCase();
  matches = records.filter((r) => String(r?.AgentTemplate ?? '').trim().toLowerCase() === wantedTemplate);
  if (matches.length) matchedBy = 'agentTemplate';
}
// SECOND FALLBACK: the collected DeveloperName — the guard for self-created agents
// (null AgentTemplate). DeveloperName uniqueness is case-insensitive; compare
// accordingly.
if (!matches.length && !noName) {
  const wantedName = developerName.toLowerCase();
  matches = records.filter((r) => String(r?.DeveloperName ?? '').trim().toLowerCase() === wantedName);
  if (matches.length) matchedBy = 'developerName';
}
if (matchedBy === 'agentTemplate' && matches.length > 1) {
  // Prefer a record whose latest BotVersion is Active so `matches[0]` (used for
  // latestVersion/agentId below) reflects the live agent rather than a stale draft.
  matches = [...matches].sort((a, b) => {
    const aActive = a?.BotVersions?.records?.[0]?.Status === 'Active' ? 0 : 1;
    const bActive = b?.BotVersions?.records?.[0]?.Status === 'Active' ? 0 : 1;
    return aActive - bActive;
  });
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
  // Which key matched — `botDefinitionId` (primary), `agentTemplate` (the
  // reliable catcher for a pre-provisioned agent whose DeveloperName differs from
  // the collected guess), or `developerName` (the fallback for self-created
  // agents). null when nothing matched.
  matchedBy: exists ? matchedBy : null,
  agentId: exists ? (matches[0].Id ?? null) : null,
  // On an AgentTemplate- or DeveloperName-fallback hit this surfaces the live
  // BotDefinition Id the template row was missing; on the Id path it echoes the
  // queried id.
  botDefinitionId: exists ? (matches[0].Id ?? null) : (noId ? null : botDefinitionId),
  developerName: exists ? (matches[0].DeveloperName ?? null) : null,
  latestVersionId: latestVersion?.Id ?? null,
  latestVersionStatus,
  needsActivation,
}, null, 2) + '\n');
