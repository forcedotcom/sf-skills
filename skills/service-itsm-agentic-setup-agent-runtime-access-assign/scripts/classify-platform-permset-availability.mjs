#!/usr/bin/env node
// Deterministic availability classifier for the platform feature permsets an
// ITSM agent's actions need at RUNTIME (so a user can exercise the agent).
//
// Reads ONE input:
//   - PermissionSet query capture (from `sf data query --json`) filtered to the
//     six known platform feature permset `Name` values across three features,
//     each with a "use" tier (lighter, user/agent-facing) and an "admin" tier:
//
//       Feature            use tier                          admin tier
//       -----------------  --------------------------------  --------------------------------
//       Prompt Templates   EinsteinGPTPromptTemplateUser     EinsteinGPTPromptTemplateManager
//       Data Cloud         GenieUserEnhancedSecurity         GenieAdmin
//       Unified Catalog    UnifiedCatalogCommunityUser       UnifiedCatalogAdmin
//
// No single org is guaranteed to have all three features provisioned, so the
// classifier reports which tiers are actually PRESENT (a row exists) and which
// are ABSENT (feature not provisioned on this org — skip it, do not fail).
//
// `needsPsl` is derived PER ROW from `LicenseId !== null` — the write path POSTs
// a PermissionSetLicenseAssign using the row's own `LicenseId`; PSL names are
// never hard-coded. `displayLabel` prefers the org's actual `Label`, falling
// back to a canonical label when the row is absent.
//
// Usage:
//   node classify-platform-permset-availability.mjs <permsets.json>
//
// Emits a single JSON object to stdout:
//   { features: [ { feature, tiers: { use, admin }, anyPresent } ],
//     provisionedFeatures: [...], absentFeatures: [...],
//     verdict: "ASSIGNABLE" | "NONE-PROVISIONED" | "CANNOT-CONFIRM",
//     reasons: [...] }
// where each tier is { tier, name, displayLabel, present, Id, LicenseId, needsPsl }.
// Exit is always 0 on parseable bodies; verdict carries the decision. Exit 2 on
// missing argv.

import { readFileSync } from 'node:fs';

// The fixed catalog. `label` is the canonical fallback; the org's own Label wins
// when the row is present (e.g. GenieAdmin ships as "Data Cloud Architect" on
// some orgs, "Data Cloud Admin" on others — render whatever the org says).
const CATALOG = [
  {
    feature: 'Prompt Templates',
    use: { name: 'EinsteinGPTPromptTemplateUser', label: 'Prompt Template User' },
    admin: { name: 'EinsteinGPTPromptTemplateManager', label: 'Prompt Template Manager' },
  },
  {
    feature: 'Data Cloud',
    use: { name: 'GenieUserEnhancedSecurity', label: 'Data Cloud User' },
    admin: { name: 'GenieAdmin', label: 'Data Cloud Admin' },
  },
  {
    feature: 'Unified Catalog',
    use: { name: 'UnifiedCatalogCommunityUser', label: 'Unified Catalog Community User' },
    admin: { name: 'UnifiedCatalogAdmin', label: 'Unified Catalog Admin' },
  },
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
  process.stderr.write('usage: node classify-platform-permset-availability.mjs <permsets.json>\n');
  process.exit(2);
}

const ps = readEnvelope(psPath);
if (!ps.ok) {
  process.stdout.write(JSON.stringify({
    features: [],
    provisionedFeatures: [],
    absentFeatures: CATALOG.map((f) => f.feature),
    verdict: 'CANNOT-CONFIRM',
    reasons: [ps.reason],
  }, null, 2) + '\n');
  process.exit(0);
}

// Index the query rows by PermissionSet.Name for O(1) lookup.
const byName = new Map();
for (const r of ps.records) {
  if (r && typeof r.Name === 'string') byName.set(r.Name, r);
}

function tierOf(tier, spec) {
  const row = byName.get(spec.name);
  const present = !!row;
  return {
    tier,
    name: spec.name,
    displayLabel: (present && typeof row.Label === 'string' && row.Label) ? row.Label : spec.label,
    present,
    Id: present ? (row.Id ?? null) : null,
    LicenseId: present ? (row.LicenseId ?? null) : null,
    needsPsl: present ? ((row.LicenseId ?? null) !== null) : false,
  };
}

const features = CATALOG.map((f) => {
  const use = tierOf('use', f.use);
  const admin = tierOf('admin', f.admin);
  return { feature: f.feature, tiers: { use, admin }, anyPresent: use.present || admin.present };
});

const provisionedFeatures = features.filter((f) => f.anyPresent).map((f) => f.feature);
const absentFeatures = features.filter((f) => !f.anyPresent).map((f) => f.feature);

const reasons = [];
let verdict;
if (provisionedFeatures.length === 0) {
  verdict = 'NONE-PROVISIONED';
  reasons.push('None of the three platform features (Prompt Templates, Data Cloud, Unified Catalog) is provisioned on this org — no runtime action-execution permset can be assigned.');
  reasons.push('This does NOT block the Agent Access concern; continue there so users can still open the activated agents.');
} else {
  verdict = 'ASSIGNABLE';
  reasons.push(`Provisioned feature(s) with an assignable tier: ${provisionedFeatures.join(', ')}.`);
  if (absentFeatures.length > 0) {
    reasons.push(`Not provisioned on this org (report as unavailable, do not assign): ${absentFeatures.join(', ')}.`);
  }
  reasons.push('For EACH provisioned feature, ask the user which tier to assign (use/agent vs admin) — do not auto-select a tier.');
  const standalone = [];
  for (const f of features) {
    for (const t of ['use', 'admin']) {
      const row = f.tiers[t];
      if (row.present && !row.needsPsl) standalone.push(row.name);
    }
  }
  if (standalone.length > 0) {
    reasons.push(`Standalone tier(s) with no backing LicenseId (assign skips PSL SOQL/POST if selected): ${standalone.join(', ')}.`);
  }
}

process.stdout.write(JSON.stringify({
  features,
  provisionedFeatures,
  absentFeatures,
  verdict,
  reasons,
}, null, 2) + '\n');
