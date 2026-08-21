#!/usr/bin/env node
// Deterministic post-activate result classifier for the NGA agent flow.
//
// The activate endpoints return **HTTP 200** on both success AND on structural
// activation failures like "invocable action not found". The failure body is:
//   { success: false, isActivated: false, messages: [ { code, ... } ] }
// or an array-wrapped variant. Nothing in the CLI exit code tells the workflow
// apart from a real success; parsing the body is the only signal.
//
// This helper is the single choke point (A9 — no prose interpretation) for that
// decision, shared by:
//   - Phase 6 (create path):     POST /nextgen-authoring/bundle-versions/<id>/activate
//   - Phase 2b (reactivation):   POST /connect/bot-versions/<id>/activation
//
// Rules:
//   - Empty body        → PASS  (documented Phase-6 success shape)
//   - {success:true}    → PASS
//   - {success:false}   → FAIL  (surface `messages[]` verbatim)
//   - unparseable body  → CANNOT-CONFIRM (surface the raw file + let workflow
//                                          fall back to the Phase-7 verify SOQL)
//
// Usage:
//   node classify-activate-result.mjs <activate-response.json>
//
// Emits a single JSON object to stdout:
//   { verdict: "PASS" | "FAIL" | "CANNOT-CONFIRM",
//     success, isActivated, messages: [...], reasons: [...] }
// Exit is always 0 on a readable file; the verdict is carried in the payload.

import { readFileSync } from 'node:fs';

const [respPath] = process.argv.slice(2);
if (!respPath) {
  process.stderr.write('usage: node classify-activate-result.mjs <activate-response.json>\n');
  process.exit(2);
}

let text;
try { text = readFileSync(respPath, 'utf8'); }
catch (e) {
  process.stdout.write(JSON.stringify({
    verdict: 'CANNOT-CONFIRM',
    success: null, isActivated: null, messages: [],
    reasons: [`unreadable file: ${respPath} (${e?.message ?? e})`],
  }, null, 2) + '\n');
  process.exit(0);
}

const trimmed = text.trim();
if (!trimmed) {
  // Documented Phase-6 success — activate returns empty body on success.
  process.stdout.write(JSON.stringify({
    verdict: 'PASS',
    success: true, isActivated: null, messages: [],
    reasons: ['Empty response body — documented success shape for the activate endpoint. Confirm via the Phase-7 BotDefinition verify read.'],
  }, null, 2) + '\n');
  process.exit(0);
}

let parsed;
try { parsed = JSON.parse(trimmed); }
catch {
  process.stdout.write(JSON.stringify({
    verdict: 'CANNOT-CONFIRM',
    success: null, isActivated: null, messages: [],
    reasons: [`Activate response is non-empty but not JSON — surface it verbatim and rely on the Phase-7 verify read: ${trimmed.slice(0, 500)}`],
  }, null, 2) + '\n');
  process.exit(0);
}

// Some Connect endpoints wrap the body in a single-element array.
const body = Array.isArray(parsed) && parsed.length === 1 && parsed[0] && typeof parsed[0] === 'object'
  ? parsed[0]
  : parsed;

// A Connect error array (each { errorCode, message }) also arrives here on 4xx.
if (Array.isArray(body)) {
  const errs = body.filter((e) => e && (e.errorCode || e.message));
  const asMsgs = errs.map((e) => ({ code: e.errorCode ?? 'ERROR', message: e.message ?? '' }));
  process.stdout.write(JSON.stringify({
    verdict: 'FAIL',
    success: false, isActivated: false, messages: asMsgs,
    reasons: ['Activate returned a Connect error array — surface every message verbatim.'],
  }, null, 2) + '\n');
  process.exit(0);
}

if (!body || typeof body !== 'object') {
  process.stdout.write(JSON.stringify({
    verdict: 'CANNOT-CONFIRM',
    success: null, isActivated: null, messages: [],
    reasons: [`Activate response is JSON but not an object — surface it and rely on the Phase-7 verify read: ${trimmed.slice(0, 500)}`],
  }, null, 2) + '\n');
  process.exit(0);
}

const success = typeof body.success === 'boolean' ? body.success : null;
const isActivated = typeof body.isActivated === 'boolean' ? body.isActivated : null;
const messages = Array.isArray(body.messages) ? body.messages : [];

if (success === true || isActivated === true) {
  process.stdout.write(JSON.stringify({
    verdict: 'PASS',
    success: success ?? true, isActivated: isActivated ?? null, messages,
    reasons: ['Activate response indicates success. Confirm via the Phase-7 BotDefinition verify read.'],
  }, null, 2) + '\n');
  process.exit(0);
}

if (success === false || isActivated === false) {
  const msgSnippet = messages
    .map((m) => `${m?.code ?? m?.errorCode ?? 'ERROR'}: ${m?.message ?? ''}`.trim())
    .join(' | ')
    .slice(0, 800);
  const missingAction = /does not exist|not found|no such action|invocable action/i.test(msgSnippet);
  const reasons = [
    `Activate returned success=false — the agent was NOT activated. Verbatim: ${msgSnippet}`,
  ];
  if (missingAction) {
    reasons.push('At least one referenced invocable action is missing on this org. Prefer running scripts/classify-action-availability.mjs BEFORE activate (Phase 2c) to catch this without a wasted create/publish; if it slipped through, hand off to service-itsm-agentic-setup-itsm-agentforce-permset-assign.');
  }
  process.stdout.write(JSON.stringify({
    verdict: 'FAIL',
    success: false, isActivated: isActivated ?? false, messages,
    reasons,
  }, null, 2) + '\n');
  process.exit(0);
}

// Body present but no success/isActivated fields — surface + rely on verify.
process.stdout.write(JSON.stringify({
  verdict: 'CANNOT-CONFIRM',
  success: null, isActivated: null, messages,
  reasons: ['Activate body had no success/isActivated field — surface it and rely on the Phase-7 verify read.'],
}, null, 2) + '\n');
