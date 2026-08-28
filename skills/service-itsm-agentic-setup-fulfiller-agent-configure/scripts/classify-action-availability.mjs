#!/usr/bin/env node
// Deterministic action-availability classifier for the NGA agent activation flow.
//
// The Fulfiller Agent Script references a fixed set of `svc_itsm_intelligence__*`
// invocable actions via its `source:` and `target:` fields (e.g.
// `source: "svc_itsm_intelligence__SummarizeIncident"`,
// `target: "generatePromptResponse://svc_itsm_intelligence__SummarizeIncident"`).
// A bundle version cannot activate when any of those actions is not surfaced by
// `/services/data/v67.0/actions/custom/generatePromptResponse` for the running
// user — the activate endpoint returns HTTP 200 with `{success:false,
// messages:[{... "does not exist"}]}` (silent-failure body). Diagnosing that
// after the fact is expensive; this classifier flags the mismatch BEFORE the
// activate call.
//
// Availability model (A9 — no prose interpretation):
//   Each action block in the Agent Script is a `source:` / `target:` pair:
//     source: "svc_..._<AgentActionName>"           # the planner-facing alias
//     target: "<scheme>://<InvocationTargetName>"    # the real invocation target
//   The `source:` value is the agent-action alias; the `target:` URI names the
//   thing actually invoked. These two names routinely DIFFER for the SAME action
//   — e.g. source `CreateIncidentResolutionSummary` →
//   target `generatePromptResponse://...IncidentResolutionSummarizationPrompt`,
//   or source `CreateIncidentRootCauseSummary` → target `flow://...CreaIncRootCse`
//   (an abbreviated flow API name). Treating the alias and the target as two
//   separate required actions (the old behaviour) false-flagged the alias as
//   "missing" and blocked a valid activation.
//
//   Only `generatePromptResponse://` targets are surfaced by
//   `/actions/custom/generatePromptResponse`; `flow://`, `apex://`, and
//   `standardInvocableAction://` targets live in other action buckets the
//   endpoint never lists (their names are often not even namespace-prefixed,
//   e.g. `associateSvcMgmntRecords`). So this gate can only verify the
//   `generatePromptResponse://` targets, keyed on the TARGET name — never the
//   source alias, never a non-prompt target. Rules:
//   1. Parse every `target:` URI; split by scheme. The checkable set is the
//      `generatePromptResponse://` target names. Non-gPR targets are recorded
//      and SKIPPED (this endpoint has no jurisdiction over them).
//   2. Enumerate every action name exposed by
//      `/actions/custom/generatePromptResponse` — accepts both response shapes:
//        (a) legacy `{ actions: [ { name, ... }, ... ] }`
//        (b) newer  `{ actions: { <fullyQualifiedName>: {...}, ... } }`
//   Emit `missing = <generatePromptResponse targets> - present`. missing.length
//   > 0 ⇒ NOT-READY (the ITSM Intelligence permset that surfaces these
//   prompt-response actions is not assigned for the running user). Zero gPR
//   targets referenced but other targets present ⇒ READY (nothing this gate
//   governs). No target: lines at all / non-parseable inputs ⇒ CANNOT-CONFIRM
//   (never block on unreadable state — surface it and let the workflow decide).
//
// Usage:
//   node classify-action-availability.mjs \
//        <agent-templates.json> <masterLabel> <generate-prompt-response.json>
//
// <agent-templates.json>          — Phase-1 `agent-templates` capture; the matched
//                                    template's `agentScript` is decoded exactly
//                                    like build-create-body.mjs decodes it, then
//                                    its `target:` invocation URIs are parsed and
//                                    split by scheme.
// <masterLabel>                   — the display label of the target template
//                                    (e.g. "IT Service Fulfiller").
// <generate-prompt-response.json> — GET
//                                    /services/data/v67.0/actions/custom/generatePromptResponse
//                                    response body.
//
// Emits a single JSON object to stdout:
//   { referenced: [...],   // generatePromptResponse:// target names this gate verifies
//     present:    [...],   // action names surfaced by generatePromptResponse
//     missing:    [...],   // referenced - present
//     skippedNonPromptTargets: [ { scheme, name }, ... ], // flow/apex/standard — not gate-checkable
//     verdict: "READY" | "NOT-READY" | "CANNOT-CONFIRM",
//     reasons: [...] }
// Exit is always 0 on parseable inputs; the verdict is carried in the payload.
// A truly unreadable input (missing/malformed file) becomes CANNOT-CONFIRM +
// exit 0 so the caller can surface the raw CLI error rather than assuming
// READY.

import { readFileSync } from 'node:fs';
import { stripReleaseManagement, decodeAgentScriptEntities } from './strip-release-management.mjs';

function readJson(path) {
  try {
    const text = readFileSync(path, 'utf8').trim();
    if (!text) return { ok: false, reason: `empty file: ${path}` };
    return { ok: true, data: JSON.parse(text) };
  } catch (e) {
    return { ok: false, reason: `unreadable/invalid JSON at ${path}: ${e?.message ?? e}` };
  }
}

function extractTargets(scriptText) {
  // Each action block pairs a `source:` alias with a `target:` invocation URI:
  //   source: "svc_itsm_intelligence__CreateIncidentResolutionSummary"
  //   target: "generatePromptResponse://svc_itsm_intelligence__IncidentResolutionSummarizationPrompt"
  //
  // Only the `target:` names the thing actually invoked, and only a
  // `generatePromptResponse://` target is surfaced (or withheld, per the ITSM
  // Intelligence permset) by /actions/custom/generatePromptResponse. `flow://`,
  // `apex://`, and `standardInvocableAction://` targets are surfaced through
  // other mechanisms and never appear in that endpoint, so they are recorded and
  // skipped rather than mis-flagged as missing. The `source:` alias is never
  // itself a generatePromptResponse entry — it is not part of the checkable set;
  // scanning it (the old behaviour) false-flagged aliases whose real target IS
  // present, blocking a valid activation.
  //
  // The regex tolerates leading whitespace, an optional YAML list dash, and the
  // scalar value in ANY of its YAML quote forms — unquoted, single-quoted, or
  // double-quoted. The opening quote (if any) is captured in group 1 and the same
  // character is re-checked as the optional closing quote via a backreference, so
  // `target: 'generatePromptResponse://Name'` parses exactly like the double-quoted
  // and unquoted forms (accepting only `"?` before was a regression: a
  // single-quoted target silently fell through to CANNOT-CONFIRM, and the workflow
  // then proceeded to create an agent whose activation fails). The name after `://`
  // is captured up to the next quote (either style) or whitespace. A target with no
  // `scheme://` shape simply does not match and contributes nothing.
  const gpr = new Set();
  const other = [];
  const targetLineRe = /^[ \t]*-?[ \t]*target[ \t]*:[ \t]*(['"]?)([A-Za-z][A-Za-z0-9]*):\/\/([^'"\s]+)\1?/;
  for (const rawLine of scriptText.split(/\r?\n/)) {
    const m = targetLineRe.exec(rawLine);
    if (!m) continue;
    const scheme = m[2];
    const name = m[3];
    if (scheme === 'generatePromptResponse') {
      gpr.add(name);
    } else {
      other.push({ scheme, name });
    }
  }
  return { gprTargets: [...gpr].sort(), otherTargets: other };
}

function extractPresentActions(actionsData) {
  const present = new Set();
  if (!actionsData || typeof actionsData !== 'object') return [];
  const a = actionsData.actions;
  if (Array.isArray(a)) {
    // Shape (a): [ { name, ... }, ... ]
    for (const it of a) {
      if (it && typeof it === 'object') {
        const nm = typeof it.name === 'string' ? it.name : null;
        if (nm) present.add(nm);
        const label = typeof it.label === 'string' ? it.label : null;
        if (label && /svc_[a-z0-9_]+__/.test(label)) present.add(label);
      }
    }
  } else if (a && typeof a === 'object') {
    // Shape (b): { <name>: {...}, ... }
    for (const key of Object.keys(a)) present.add(key);
  }
  return [...present].sort();
}

function findTemplateScript(agentTemplatesData, masterLabel) {
  if (!agentTemplatesData || typeof agentTemplatesData !== 'object') return null;
  const items = Array.isArray(agentTemplatesData.data) ? agentTemplatesData.data : null;
  if (!items) return null;
  const wanted = String(masterLabel).trim().toLowerCase();
  const match = items.find((it) => String(it?.masterLabel ?? '').trim().toLowerCase() === wanted);
  if (!match || typeof match.agentScript !== 'string' || !match.agentScript.trim()) return null;
  // Scan the SAME script the create actually ships — with the Release
  // Management subagent stripped. build-create-body.mjs removes it, so
  // `svc_itsm_intelligence__SummarizeRelease` is never referenced by the created
  // agent; leaving it in the scanned text here would false-flag it as "missing"
  // and block the very flow the strip unblocks on an org without ReleaseManagementPref.
  return stripReleaseManagement(decodeAgentScriptEntities(match.agentScript)).text;
}

const [templatesPath, rawLabel, actionsPath] = process.argv.slice(2);
if (!templatesPath || !rawLabel || !actionsPath) {
  process.stderr.write('usage: node classify-action-availability.mjs <agent-templates.json> <masterLabel> <generate-prompt-response.json>\n');
  process.exit(2);
}

const templatesRead = readJson(templatesPath);
const actionsRead = readJson(actionsPath);

if (!templatesRead.ok) {
  process.stdout.write(JSON.stringify({
    referenced: [], present: [], missing: [],
    verdict: 'CANNOT-CONFIRM',
    reasons: [templatesRead.reason],
  }, null, 2) + '\n');
  process.exit(0);
}
if (!actionsRead.ok) {
  process.stdout.write(JSON.stringify({
    referenced: [], present: [], missing: [],
    verdict: 'CANNOT-CONFIRM',
    reasons: [actionsRead.reason],
  }, null, 2) + '\n');
  process.exit(0);
}

const scriptText = findTemplateScript(templatesRead.data, rawLabel);
if (!scriptText) {
  process.stdout.write(JSON.stringify({
    referenced: [], present: [], missing: [],
    verdict: 'CANNOT-CONFIRM',
    reasons: [`No template with masterLabel "${rawLabel}" carrying a non-empty agentScript in agent-templates response.`],
  }, null, 2) + '\n');
  process.exit(0);
}

const { gprTargets: referenced, otherTargets } = extractTargets(scriptText);
const present = extractPresentActions(actionsRead.data);
const presentSet = new Set(present);
const missing = referenced.filter((r) => !presentSet.has(r));
const skippedNonPromptTargets = otherTargets;

let verdict, reasons;
if (referenced.length === 0) {
  if (otherTargets.length > 0) {
    // The template references only flow/apex/standard-invocable targets — none of
    // which /actions/custom/generatePromptResponse governs. There is nothing for
    // this permset gate to verify, so it must not block.
    verdict = 'READY';
    reasons = [
      `No generatePromptResponse-backed actions are referenced by the template; the ${otherTargets.length} non-prompt target(s) (flow/apex/standard-invocable) are surfaced through other mechanisms and are outside this gate.`,
    ];
  } else {
    verdict = 'CANNOT-CONFIRM';
    reasons = ['No target: invocation URIs were found in the decoded Agent Script — either the script shape is unexpected or decoding failed. Surface and continue with caution.'];
  }
} else if (missing.length === 0) {
  verdict = 'READY';
  reasons = [
    `All ${referenced.length} generatePromptResponse-backed action(s) referenced by the template are surfaced by /actions/custom/generatePromptResponse for the running user${
      otherTargets.length ? ` (${otherTargets.length} non-prompt flow/standard-invocable target(s) are outside this gate and were not checked)` : ''
    }.`,
  ];
} else {
  verdict = 'NOT-READY';
  reasons = [
    `${missing.length} of ${referenced.length} generatePromptResponse-backed action(s) referenced by the template are NOT surfaced by /actions/custom/generatePromptResponse for the running user.`,
    `Missing: ${missing.join(', ')}`,
    'Activate will succeed at the HTTP level but return {success:false, messages:[...]} — the agent will not be usable. Offer to hand off to service-itsm-agentic-setup-itsm-agentforce-permset-assign, which handles both the permset-not-assigned case and the package-not-installed case.',
  ];
}

process.stdout.write(JSON.stringify({
  referenced, present, missing, skippedNonPromptTargets, verdict, reasons,
}, null, 2) + '\n');
