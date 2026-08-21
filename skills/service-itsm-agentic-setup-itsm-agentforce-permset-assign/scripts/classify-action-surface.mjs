#!/usr/bin/env node
// Deterministic verify-phase classifier for the ITSM Intelligence permset-assign flow.
//
// Reads the `/services/data/v67.0/actions/custom/generatePromptResponse`
// response capture and decides whether the ITSM Intelligence prompt-template
// invocable actions (Fulfiller-only — `svc_itsm_intelligence__*`) are
// surfaced for the running user. Replaces the prose "grep the response for
// svc_itsm_intelligence__" step in Phase 4 (A9 — deterministic decisions
// belong in scripts). Employee agent actions (`svc_emp_intelligence__*`)
// are out of scope for this skill.
//
// Rules:
//   - Accepts both response shapes for `actions`:
//       (a) legacy `{ actions: [ { name, ... }, ... ] }`
//       (b) newer  `{ actions: { <fullyQualifiedName>: {...}, ... } }`
//     Either wrapped by `data.result` (CLI envelope) or at top level.
//   - If `expectedActions` (CSV of specific action API names) is provided,
//     partition each into `present` / `missing` by exact name match on the
//     extracted names. `verdict`:
//       * SURFACED — every expected action is present.
//       * PARTIAL  — at least one is present but not all.
//       * MISSING  — none are present.
//   - If `expectedActions` is omitted, look for AT LEAST ONE action name
//     starting with `svc_itsm_intelligence__`.
//       * SURFACED — one or more found; `present` lists them, `missing` is [].
//       * MISSING  — none found; `missing` is [] (no explicit expectation set).
//   - Envelope missing/failed / unexpected shape ⇒ CANNOT-CONFIRM.
//
// Usage:
//   node classify-action-surface.mjs <generate-prompt-response.json> [expectedActions-csv]
//
// Emits a single JSON object to stdout:
//   { present: [name, ...],
//     missing: [name, ...],
//     totalItsmActionsSeen: <int>,
//     verdict: "SURFACED" | "PARTIAL" | "MISSING" | "CANNOT-CONFIRM",
//     reasons: [...] }
// Exit is always 0 on parseable bodies; verdict carries the decision.

import { readFileSync } from 'node:fs';

const [responsePath, expectedCsv] = process.argv.slice(2);
if (!responsePath) {
  process.stderr.write('usage: node classify-action-surface.mjs <generate-prompt-response.json> [expectedActions-csv]\n');
  process.exit(2);
}

function emit(verdict, extras, reasons) {
  process.stdout.write(JSON.stringify({
    present: extras.present ?? [],
    missing: extras.missing ?? [],
    totalItsmActionsSeen: extras.totalItsmActionsSeen ?? 0,
    verdict,
    reasons,
  }, null, 2) + '\n');
  process.exit(0);
}

let text;
try {
  text = readFileSync(responsePath, 'utf8').trim();
} catch (e) {
  emit('CANNOT-CONFIRM', {}, [`unreadable file at ${responsePath}: ${e?.message ?? e}`]);
}
if (!text) emit('CANNOT-CONFIRM', {}, [`empty file: ${responsePath}`]);

let data;
try {
  data = JSON.parse(text);
} catch (e) {
  emit('CANNOT-CONFIRM', {}, [`invalid JSON at ${responsePath}: ${e?.message ?? e}`]);
}
if (!data || typeof data !== 'object') {
  emit('CANNOT-CONFIRM', {}, [`non-object JSON at ${responsePath}`]);
}
if (typeof data.status === 'number' && data.status !== 0) {
  emit('CANNOT-CONFIRM', {}, [`sf api request at ${responsePath} failed with status ${data.status}`]);
}

// The generatePromptResponse endpoint has two observed response shapes; accept
// both so a valid surface never mis-classifies as CANNOT-CONFIRM:
//   (a) legacy `{ actions: [ { name, ... }, ... ] }`
//   (b) newer  `{ actions: { <fullyQualifiedName>: {...}, ... } }`
// Both forms may also be wrapped by the CLI envelope under `data.result`.
function extractNames(actionsField) {
  if (Array.isArray(actionsField)) {
    return actionsField
      .map((a) => (a && typeof a.name === 'string' ? a.name : null))
      .filter((n) => n !== null);
  }
  if (actionsField && typeof actionsField === 'object') {
    return Object.keys(actionsField);
  }
  return null;
}
const names = extractNames(data.actions) ?? extractNames(data.result?.actions);
if (names === null) {
  emit('CANNOT-CONFIRM', {}, [
    `response body has no \`actions\` array or object — expected the /actions/custom/generatePromptResponse envelope. Confirm the CLI wrote the full body to ${responsePath}.`,
  ]);
}

const itsmNames = names.filter((n) => n.startsWith('svc_itsm_intelligence__'));

const expected = (expectedCsv ?? '')
  .split(',')
  .map((s) => s.trim())
  .filter(Boolean);

if (expected.length > 0) {
  const present = expected.filter((e) => names.includes(e));
  const missing = expected.filter((e) => !names.includes(e));
  let verdict;
  if (missing.length === 0) verdict = 'SURFACED';
  else if (present.length === 0) verdict = 'MISSING';
  else verdict = 'PARTIAL';
  const reasons = [
    `Checked ${expected.length} expected action name(s): ${present.length} present, ${missing.length} missing.`,
  ];
  if (missing.length > 0) {
    reasons.push(`Missing: ${missing.join(', ')}. A permset write can succeed while the target action set is still ungated by the assigned permset (cache, wrong permset). Do not report success.`);
  }
  if (itsmNames.length > 0 && (present.length !== itsmNames.length || missing.length > 0)) {
    reasons.push(`Response contains ${itsmNames.length} svc_itsm_intelligence__ action(s) overall: ${itsmNames.slice(0, 20).join(', ')}${itsmNames.length > 20 ? ', …' : ''}.`);
  }
  emit(verdict, { present, missing, totalItsmActionsSeen: itsmNames.length }, reasons);
}

// No explicit expectation — surface if ANY ITSM Intelligence action is present.
if (itsmNames.length === 0) {
  emit('MISSING', { present: [], missing: [], totalItsmActionsSeen: 0 }, [
    'No `svc_itsm_intelligence__` invocable actions were returned for this user. Assignment may have succeeded but the actions are not surfaced — try a session refresh, or the assigned persona permset does not gate the target actions.',
  ]);
}
emit('SURFACED', { present: itsmNames, missing: [], totalItsmActionsSeen: itsmNames.length }, [
  `Found ${itsmNames.length} ITSM Intelligence invocable action(s) surfaced for this user.`,
]);
