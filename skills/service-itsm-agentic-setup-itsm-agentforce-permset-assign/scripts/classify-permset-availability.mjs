#!/usr/bin/env node
// Deterministic branch classifier for the Fulfiller persona permset-assign flow.
//
// Reads ONE input:
//   - PermissionSet query capture (from `sf data query --json`) for the four
//     Core-shipped Fulfiller persona permsets:
//       * IncidentFulfiller
//       * ProblemFulfillerPermSet
//       * ChangeRequestFulfillerPermSet
//       * ReleaseManagerPermSet
//     (namespace `force`, not a managed-package namespace)
//
// Rules (A9):
//   - `verdict:"ASSIGN"`      — ≥1 of the four personas is present. Caller
//                                asks the user which persona to assign; do NOT
//                                auto-select.
//   - `verdict:"HAND-OFF"`    — none of the four present. The ITSM AddOn(s)
//                                are not provisioned; permset-assign is a
//                                no-op. Hand off to the studio validate skill
//                                so the AddOn(s) can be enabled first.
//   - `verdict:"CANNOT-CONFIRM"` — query envelope missing / unparseable.
//
// Usage:
//   node classify-permset-availability.mjs <permsets.json>
//
// Emits a single JSON object to stdout:
//   { personasFound: [Name, ...],
//     personasMissing: [Name, ...],
//     candidates: [{ Id, Name, Label, LicenseId, needsPsl }, ...],
//     verdict: "ASSIGN" | "HAND-OFF" | "CANNOT-CONFIRM",
//     reasons: [...] }
// `candidates` includes only rows for the four known persona Names; unrelated
// rows in the query result are filtered out. `needsPsl` is derived per-row
// from `LicenseId !== null`. Exit is always 0 on parseable bodies; verdict
// carries the branch decision. Exit 2 on missing argv.

import { readFileSync } from 'node:fs';

const KNOWN_PERSONAS = [
  'IncidentFulfiller',
  'ProblemFulfillerPermSet',
  'ChangeRequestFulfillerPermSet',
  'ReleaseManagerPermSet',
];

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

const [psPath] = process.argv.slice(2);
if (!psPath) {
  process.stderr.write('usage: node classify-permset-availability.mjs <permsets.json>\n');
  process.exit(2);
}

const ps = readEnvelope(psPath);
if (!ps.ok) {
  process.stdout.write(JSON.stringify({
    personasFound: [],
    personasMissing: [...KNOWN_PERSONAS],
    candidates: [],
    verdict: 'CANNOT-CONFIRM',
    reasons: [ps.reason],
  }, null, 2) + '\n');
  process.exit(0);
}

// Filter to only the five known persona Names — drop any unrelated rows.
const knownRows = ps.records.filter((r) => KNOWN_PERSONAS.includes(r?.Name));
const foundNames = knownRows.map((r) => r.Name);
const personasFound = KNOWN_PERSONAS.filter((n) => foundNames.includes(n));
const personasMissing = KNOWN_PERSONAS.filter((n) => !foundNames.includes(n));

const candidates = knownRows.map((r) => ({
  Id: r.Id ?? null,
  Name: r.Name ?? null,
  Label: r.Label ?? null,
  LicenseId: r.LicenseId ?? null,
  needsPsl: (r.LicenseId ?? null) !== null,
}));

const reasons = [];
let verdict;
if (personasFound.length === 0) {
  verdict = 'HAND-OFF';
  reasons.push('None of the four Core-shipped Fulfiller persona permsets (IncidentFulfiller, ProblemFulfillerPermSet, ChangeRequestFulfillerPermSet, ReleaseManagerPermSet) is present on this org — the ITSM AddOn(s) are not provisioned.');
  reasons.push('Permset-assign cannot fix this; hand off to service-itsm-agentic-setup-agentforce-studio-validate.');
} else {
  verdict = 'ASSIGN';
  reasons.push(`Found ${personasFound.length} of 4 Fulfiller persona permset(s) on this org: ${personasFound.join(', ')}.`);
  if (personasMissing.length > 0) {
    reasons.push(`Not provisioned (AddOn(s) missing for these personas): ${personasMissing.join(', ')}.`);
  }
  const standalone = candidates.filter((c) => !c.needsPsl).map((c) => c.Name);
  if (standalone.length > 0) {
    reasons.push(`Standalone-permset flow (no backing LicenseId — Phase 2 skips PSL SOQL/POST if selected): ${standalone.join(', ')}.`);
  }
  reasons.push('Caller MUST ask the user which persona to assign before Phase 2 — do not auto-select. A Fulfiller commonly needs only one persona (e.g. only Incident).');
}

process.stdout.write(JSON.stringify({
  personasFound,
  personasMissing,
  candidates,
  verdict,
  reasons,
}, null, 2) + '\n');
