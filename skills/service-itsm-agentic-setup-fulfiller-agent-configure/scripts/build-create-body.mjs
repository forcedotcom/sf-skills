#!/usr/bin/env node
// Build the NGA createBundleWithVersion request body from the shipped
// Fulfiller template's agentScript.
//
// The legacy `agent-templates` read already returns the template's full Agent
// Script (AFScript) content in its `agentScript` field, HTML-entity-encoded
// (sometimes double-encoded). This script:
//   1. Locates the matching template item by masterLabel in the
//      agent-templates response.
//   2. Fully HTML-decodes `agentScript` (named + numeric entities, multi-pass
//      to unwind double-encoding).
//   3. Substitutes the script's internal `config.developer_name` /
//      `config.agent_label` with the collected <developerName> / <label> —
//      the bundle's outer apiName must match the script's internal
//      developer_name or the two diverge (the platform will otherwise
//      auto-suffix the apiName).
//   4. Writes the createBundleWithVersion body
//      { apiName, label, assets: [{ resourceName: "agentDefinition",
//        resourceType: "agentDefinition", sections: [], resourceContent }] }
//      to <outPath>.
//
// Usage:
//   node build-create-body.mjs <agent-templates.json> <masterLabel> <developerName> <label> <outPath>
//
// Exits 2 on missing/bad args, 3 if the template or its agentScript can't be found.

import { readFileSync, writeFileSync } from 'node:fs';
import { stripReleaseManagement, decodeAgentScriptEntities } from './strip-release-management.mjs';

const [templatesPath, masterLabel, developerName, label, outPath] = process.argv.slice(2);
if (!templatesPath || !masterLabel || !developerName || !label || !outPath) {
  process.stderr.write('usage: node build-create-body.mjs <agent-templates.json> <masterLabel> <developerName> <label> <outPath>\n');
  process.exit(2);
}

let templatesData;
try {
  templatesData = JSON.parse(readFileSync(templatesPath, 'utf8'));
} catch {
  process.stderr.write(`error: could not read/parse ${templatesPath}\n`);
  process.exit(3);
}

const items = Array.isArray(templatesData?.data) ? templatesData.data : [];
const wanted = String(masterLabel).trim().toLowerCase();
const match = items.find((it) => String(it?.masterLabel ?? '').trim().toLowerCase() === wanted);
if (!match) {
  process.stderr.write(`error: no template with masterLabel "${masterLabel}" found in ${templatesPath}\n`);
  process.exit(3);
}
if (!match.agentScript || typeof match.agentScript !== 'string' || !match.agentScript.trim()) {
  process.stderr.write(`error: template "${masterLabel}" (id=${match.id}) has no agentScript content\n`);
  process.exit(3);
}

// Escapes a value for use as a YAML double-quoted scalar — the agentScript's
// developer_name/agent_label fields are plain `"..."` strings, so a raw
// double-quote or backslash in a user-supplied label would otherwise break
// out of the scalar (e.g. label `Sam "Ops"` -> `agent_label: "Sam "Ops""`).
function yamlDoubleQuoteEscape(text) {
  return String(text).replace(/\\/g, '\\\\').replace(/"/g, '\\"');
}

const decodedRaw = decodeAgentScriptEntities(match.agentScript);

// Strip the Release Management subagent so the created agent never
// references `svc_itsm_intelligence__SummarizeRelease` — that action is gated
// behind Release Management (`ReleaseManagementPref`) and would otherwise make
// `activate` fail with a `{success:false}` silent-failure body on any org that
// has not enabled the pref. The strip is a no-op if the block is absent.
const { text: decoded, removed } = stripReleaseManagement(decodedRaw);
if (removed.topic > 0) {
  process.stderr.write(
    `note: stripped Release Management subagent (topic:${removed.topic} goto:${removed.goto} bullet:${removed.bullet} lines)\n`,
  );
}
// Completeness guard: if a ReleaseManagement/SummarizeRelease reference survives
// the strip (e.g. a future template references the gated action outside the
// three stripped surfaces), the shipped bundle would dangle it and `activate`
// could still return the {success:false} silent-failure body. Warn loudly.
if (removed.residual > 0) {
  process.stderr.write(
    `warning: ${removed.residual} residual ReleaseManagement/SummarizeRelease token(s) survive after strip — the template may reference the gated action outside the three stripped surfaces; the created agent's activation could still fail\n`,
  );
}

const developerNameEscaped = yamlDoubleQuoteEscape(developerName);
const labelEscaped = yamlDoubleQuoteEscape(label);

const substituted = decoded
  .replace(/developer_name:\s*"[^"]*"/, `developer_name: "${developerNameEscaped}"`)
  .replace(/agent_label:\s*"[^"]*"/, `agent_label: "${labelEscaped}"`);

if (!substituted.includes(`developer_name: "${developerNameEscaped}"`)) {
  process.stderr.write('error: failed to substitute config.developer_name in the decoded agentScript\n');
  process.exit(3);
}
if (!substituted.includes(`agent_label: "${labelEscaped}"`)) {
  process.stderr.write('error: failed to substitute config.agent_label in the decoded agentScript\n');
  process.exit(3);
}

const body = {
  apiName: developerName,
  label,
  assets: [
    {
      resourceName: 'agentDefinition',
      resourceType: 'agentDefinition',
      sections: [],
      resourceContent: substituted,
    },
  ],
};

writeFileSync(outPath, JSON.stringify(body), 'utf8');
process.stdout.write(outPath + '\n');
