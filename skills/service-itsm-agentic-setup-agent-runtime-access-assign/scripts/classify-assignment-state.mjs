#!/usr/bin/env node
// Deterministic idempotency classifier for the agent-runtime-access-assign flow.
//
// Reads the `sf data query --json` captures:
//   - PermissionSetAssignment (permset ↔ user) for the target user + permset
//   - PermissionSetLicenseAssign (PSL ↔ user) for the target user + PSL
//     — ONLY when the selected permset actually has a backing license.
//       Pass the sentinel `NO-PSL` in place of the PSLA path when the selected
//       permset has no backing `LicenseId` (a standalone permset such as the
//       custom `Agent_Access` set — no PSL query, no PSL POST).
// and decides whether the assign write should be skipped for this user+permset.
//
// Rules (A9):
//   - needsPsl AND both rows present ⇒ needsWrite=false (already fully assigned).
//   - needsPsl AND either row missing ⇒ needsWrite=true (assign the missing
//     piece; the workflow assigns PSL before permset regardless of which one is
//     currently missing to preserve the write-order invariant).
//   - !needsPsl (pslaPath === "NO-PSL"):
//       * permsetAssigned ⇒ needsWrite=false (nothing to write).
//       * !permsetAssigned ⇒ needsWrite=true (assign the permset only — skip the
//         PSL POST).
//     `licenseAssigned` is reported as null in this branch (not applicable).
//   - Query envelope missing/failed ⇒ CANNOT-CONFIRM; surface it and stop.
//
// Usage:
//   node classify-assignment-state.mjs <psa-existing.json> <psla-existing.json | NO-PSL>
//
// Emits a single JSON object to stdout:
//   { permsetAssigned, licenseAssigned, needsWrite,
//     verdict: "NEEDS-WRITE" | "ALREADY-ASSIGNED" | "CANNOT-CONFIRM",
//     reasons: [...] }
// Exit is always 0 on parseable bodies; verdict carries the decision.

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

const argv = process.argv.slice(2).filter((a) => !!a);
if (argv.length < 2) {
  process.stderr.write('usage: node classify-assignment-state.mjs <psa-existing.json> <psla-existing.json | NO-PSL>\n');
  process.exit(2);
}
const [psaPath, pslaArg] = argv;
const needsPsl = pslaArg !== 'NO-PSL';

const psa = readEnvelope(psaPath);
const psla = needsPsl ? readEnvelope(pslaArg) : { ok: true, records: [], skipped: true };

const readErrors = [psa, psla].filter((r) => !r.ok).map((r) => r.reason);
if (readErrors.length) {
  process.stdout.write(JSON.stringify({
    permsetAssigned: null, licenseAssigned: null, needsWrite: null,
    verdict: 'CANNOT-CONFIRM',
    reasons: readErrors,
  }, null, 2) + '\n');
  process.exit(0);
}

const permsetAssigned = psa.records.length > 0;
const licenseAssigned = needsPsl ? psla.records.length > 0 : null;
const needsWrite = needsPsl
  ? !(permsetAssigned && licenseAssigned)
  : !permsetAssigned;

const verdict = needsWrite ? 'NEEDS-WRITE' : 'ALREADY-ASSIGNED';
const reasons = [
  `PermissionSetAssignment: ${permsetAssigned ? 'present' : 'missing'} (${psa.records.length} row${psa.records.length === 1 ? '' : 's'}).`,
  needsPsl
    ? `PermissionSetLicenseAssign: ${licenseAssigned ? 'present' : 'missing'} (${psla.records.length} row${psla.records.length === 1 ? '' : 's'}).`
    : 'PermissionSetLicenseAssign: not applicable — the selected permission set has no backing LicenseId (standalone-permset flow; PSL SOQL + POST are skipped).',
];
reasons.push(
  needsWrite
    ? (needsPsl
      ? 'At least one assignment is missing — proceed to the confirm-to-write gate, then assign (PSL first, permset second).'
      : 'Permission set assignment is missing — proceed to the confirm-to-write gate, then assign the permset ONLY (skip the PSL POST).')
    : (needsPsl
      ? 'Both the permission set and its backing license are already assigned to this user — skip the write, go straight to verify.'
      : 'The permission set is already assigned to this user (no backing license required) — skip the write, go straight to verify.')
);

process.stdout.write(JSON.stringify({
  permsetAssigned, licenseAssigned, needsWrite, verdict, reasons,
}, null, 2) + '\n');
