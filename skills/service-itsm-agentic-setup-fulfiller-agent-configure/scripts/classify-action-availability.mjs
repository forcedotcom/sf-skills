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
// Two fixed rules (A9 — no prose interpretation):
//   1. Enumerate every `svc_*__<ActionName>` token that appears inside a
//      `source:` or `target:` line of the decoded Agent Script.
//   2. Enumerate every action name exposed by
//      `/actions/custom/generatePromptResponse` — accepts both response shapes:
//        (a) legacy `{ actions: [ { name, ... }, ... ] }`
//        (b) newer  `{ actions: { <fullyQualifiedName>: {...}, ... } }`
//   Emit `missing = referenced - present`. If missing.length > 0 ⇒ verdict
//   NOT-READY. On non-parseable inputs, verdict is CANNOT-CONFIRM (never block
//   on unreadable state — surface it and let the workflow decide).
//
// Usage:
//   node classify-action-availability.mjs \
//        <agent-templates.json> <masterLabel> <generate-prompt-response.json>
//
// <agent-templates.json>          — Phase-1 `agent-templates` capture; the matched
//                                    template's `agentScript` is decoded exactly
//                                    like build-create-body.mjs decodes it, then
//                                    scanned for source:/target: action tokens.
// <masterLabel>                   — the display label of the target template
//                                    (e.g. "IT Service Fulfiller").
// <generate-prompt-response.json> — GET
//                                    /services/data/v67.0/actions/custom/generatePromptResponse
//                                    response body.
//
// Emits a single JSON object to stdout:
//   { referenced: [...],
//     present:    [...],
//     missing:    [...],
//     verdict: "READY" | "NOT-READY" | "CANNOT-CONFIRM",
//     reasons: [...] }
// Exit is always 0 on parseable inputs; the verdict is carried in the payload.
// A truly unreadable input (missing/malformed file) becomes CANNOT-CONFIRM +
// exit 0 so the caller can surface the raw CLI error rather than assuming
// READY.

import { readFileSync } from 'node:fs';

function readJson(path) {
  try {
    const text = readFileSync(path, 'utf8').trim();
    if (!text) return { ok: false, reason: `empty file: ${path}` };
    return { ok: true, data: JSON.parse(text) };
  } catch (e) {
    return { ok: false, reason: `unreadable/invalid JSON at ${path}: ${e?.message ?? e}` };
  }
}

// Multi-pass HTML entity decode — matches build-create-body.mjs so both see the
// same script content. Connect API bodies can be double-encoded.
const NAMED = { amp: '&', quot: '"', apos: "'", lt: '<', gt: '>', '#39': "'", nbsp: ' ' };
function decodeEntitiesOnce(s) {
  return s.replace(/&(#?\w+);/g, (m, ref) => {
    if (ref.startsWith('#')) {
      const n = ref[1] === 'x' || ref[1] === 'X' ? parseInt(ref.slice(2), 16) : parseInt(ref.slice(1), 10);
      return Number.isFinite(n) ? String.fromCodePoint(n) : m;
    }
    return Object.prototype.hasOwnProperty.call(NAMED, ref) ? NAMED[ref] : m;
  });
}
function decodeEntities(s) {
  let prev = s, next = decodeEntitiesOnce(s);
  while (next !== prev) { prev = next; next = decodeEntitiesOnce(next); }
  return next;
}

function extractReferencedActions(scriptText) {
  // Only lines whose YAML key is `source` or `target` are load-bearing — a
  // namespace-prefixed action name mentioned inside a description, instruction,
  // or comment is documentation, not a required invocation. Scanning globally
  // would mis-flag such a mention as NOT-READY and block a valid activation.
  //
  // Agent Script YAML forms observed:
  //   source: "svc_itsm_intelligence__SummarizeIncident"
  //   source: svc_itsm_intelligence__SummarizeIncident
  //   target: "generatePromptResponse://svc_itsm_intelligence__SummarizeIncident"
  //   - source: "..."
  //
  // The key line regex tolerates leading whitespace, an optional YAML list dash,
  // and both quoted and unquoted scalar values (single line). Block scalars
  // (`source: |`) are extraordinarily rare for these fields and safely fall
  // through to CANNOT-CONFIRM when nothing is extracted.
  const referenced = new Set();
  const tokenRe = /\bsvc_[a-z0-9_]+__[A-Za-z][A-Za-z0-9_]*\b/g;
  const keyLineRe = /^[ \t]*-?[ \t]*(?:source|target)[ \t]*:[ \t]*(.*)$/;
  for (const rawLine of scriptText.split(/\r?\n/)) {
    const km = keyLineRe.exec(rawLine);
    if (!km) continue;
    const value = km[1];
    for (const m of value.matchAll(tokenRe)) {
      referenced.add(m[0]);
    }
  }
  return [...referenced].sort();
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
  return decodeEntities(match.agentScript);
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

const referenced = extractReferencedActions(scriptText);
const present = extractPresentActions(actionsRead.data);
const presentSet = new Set(present);
const missing = referenced.filter((r) => !presentSet.has(r));

let verdict, reasons;
if (referenced.length === 0) {
  verdict = 'CANNOT-CONFIRM';
  reasons = ['No svc_*__ action tokens were found in the decoded Agent Script — either the script does not use namespace-prefixed invocables or decoding failed. Surface and continue with caution.'];
} else if (missing.length === 0) {
  verdict = 'READY';
  reasons = [`All ${referenced.length} template-referenced invocable action(s) are surfaced by /actions/custom/generatePromptResponse for the running user.`];
} else {
  verdict = 'NOT-READY';
  reasons = [
    `${missing.length} of ${referenced.length} template-referenced invocable action(s) are NOT surfaced by /actions/custom/generatePromptResponse for the running user.`,
    `Missing: ${missing.join(', ')}`,
    'Activate will succeed at the HTTP level but return {success:false, messages:[...]} — the agent will not be usable. Offer to hand off to service-itsm-agentic-setup-itsm-agentforce-permset-assign, which handles both the permset-not-assigned case and the package-not-installed case.',
  ];
}

process.stdout.write(JSON.stringify({
  referenced, present, missing, verdict, reasons,
}, null, 2) + '\n');
