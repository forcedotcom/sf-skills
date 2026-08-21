#!/usr/bin/env node
// Build the NGA createBundleWithVersion request body from the shipped
// Employee template's agentScript.
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

const [templatesPath, masterLabel, developerName, label, outPath] = process.argv.slice(2);
if (!templatesPath || !masterLabel || !developerName || !label || !outPath) {
  process.stderr.write('usage: node build-create-body.mjs <agent-templates.json> <masterLabel> <developerName> <label> <outPath>\n');
  process.exit(2);
}

function decodeHtmlEntities(text) {
  let prev = text;
  for (let pass = 0; pass < 4; pass += 1) {
    const next = prev
      .replace(/&amp;/g, '&')
      .replace(/&quot;/g, '"')
      .replace(/&#39;/g, "'")
      .replace(/&lt;/g, '<')
      .replace(/&gt;/g, '>')
      .replace(/&#(\d+);/g, (_, code) => String.fromCharCode(parseInt(code, 10)));
    if (next === prev) break;
    prev = next;
  }
  return prev;
}

let templatesData;
try {
  templatesData = JSON.parse(readFileSync(templatesPath, 'utf8'));
} catch {
  process.stderr.write(`error: could not read/parse ${templatesPath}\n`);
  process.exit(3);
}

const items = Array.isArray(templatesData?.data) ? templatesData.data : [];
// Filter to `svc_emp_intelligence__` first — matches the preflight classifier.
// The agent-templates response also carries other-namespace entries; some
// share a masterLabel with an in-namespace entry (e.g. `System Password Reset
// Assistance`) so a `masterLabel`-only match would silently pick whichever
// appeared first in `data[]`.
const inNamespace = items.filter((it) => typeof it?.id === 'string' && it.id.startsWith('svc_emp_intelligence__'));
const wanted = String(masterLabel).trim().toLowerCase();
const match = inNamespace.find((it) => String(it?.masterLabel ?? '').trim().toLowerCase() === wanted);
if (!match) {
  process.stderr.write(`error: no svc_emp_intelligence__ template with masterLabel "${masterLabel}" found in ${templatesPath}\n`);
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

const decoded = decodeHtmlEntities(match.agentScript);
const developerNameEscaped = yamlDoubleQuoteEscape(developerName);
const labelEscaped = yamlDoubleQuoteEscape(label);

const substituted = decoded
  .replace(/developer_name:\s*"[^"]*"/, () => `developer_name: "${developerNameEscaped}"`)
  .replace(/agent_label:\s*"[^"]*"/, () => `agent_label: "${labelEscaped}"`);

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
