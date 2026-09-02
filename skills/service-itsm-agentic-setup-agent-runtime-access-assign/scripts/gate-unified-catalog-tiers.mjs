#!/usr/bin/env node
// Per-target-user eligibility gate for the Unified Catalog feature tiers. The
// Unified Catalog PSLs are license-SHAPE gated (not seat-gated): the Community
// User tier can be held only by a Unified Employee-licensed user, and the Admin
// tier is meaningful only for a System Administrator. Offering a tier the user's
// license/profile can never hold produces a hard license-shape failure at write
// time, so this gate decides which UC tiers to OFFER for a given user — or to omit
// Unified Catalog for that user entirely. A pre-write eligibility gate, evaluated
// per target user; it never writes.
//
// Inputs (argv):
//   1. availability.json — the classify-platform-permset-availability.mjs output
//      capture (carries the Unified Catalog tiers with present/Id/LicenseId/needsPsl).
//   2. user.json         — a `sf data query --json` capture of the ONE target user,
//      selecting Profile.Name and Profile.UserLicense.Name.
//
// Output (stdout JSON):
//   { feature:"Unified Catalog", provisioned,
//     user:{ profile, license, unifiedEmployee, sysAdmin },
//     offer:[ <tier objects from the availability classifier> ], omit, note }
//   offer[] is the subset of PRESENT UC tiers this user is eligible for:
//     - "use"   (UnifiedCatalogCommunityUser) → only when the user is Unified Employee
//     - "admin" (UnifiedCatalogAdmin)         → only when the user is System Administrator
//   omit=true (offer empty) ⇒ do NOT present Unified Catalog for this user; report it
//   "not applicable for this user's license/profile — skipped" (never a failed write).
//   Fails CLOSED: an unreadable user capture yields omit=true (better to skip than to
//   offer a tier that will fail). Exit 0 on parseable bodies; exit 2 on missing argv.

import { readFileSync } from 'node:fs';

// The Unified Employee cohort (Community User tier) and the System Administrator
// profile (Admin tier) — the only two cohorts whose license/profile shape can hold
// a Unified Catalog tier.
const UNIFIED_RE = /unified\s*employee/i;
const SYSADMIN_RE = /system\s*administrator/i;

function readJson(path) {
  try {
    const text = readFileSync(path, 'utf8').trim();
    if (!text) return { ok: false, reason: `empty file: ${path}` };
    return { ok: true, data: JSON.parse(text) };
  } catch (e) {
    return { ok: false, reason: `unreadable/invalid JSON at ${path}: ${e?.message ?? e}` };
  }
}

function emit(obj) {
  process.stdout.write(JSON.stringify(obj, null, 2) + '\n');
}

const [availPath, userPath] = process.argv.slice(2);
if (!availPath || !userPath) {
  process.stderr.write('usage: node gate-unified-catalog-tiers.mjs <availability.json> <user.json>\n');
  process.exit(2);
}

const avail = readJson(availPath);
const userEnv = readJson(userPath);

// Locate the Unified Catalog feature block emitted by the availability classifier.
const ucFeature = avail.ok && Array.isArray(avail.data?.features)
  ? avail.data.features.find((f) => f.feature === 'Unified Catalog')
  : null;
const useTier = ucFeature?.tiers?.use ?? null;
const adminTier = ucFeature?.tiers?.admin ?? null;
const provisioned = !!(useTier?.present || adminTier?.present);

// The one target user's profile + license (result.records[0]).
const rec = userEnv.ok ? (userEnv.data?.result?.records?.[0] ?? null) : null;
const profile = `${rec?.Profile?.Name ?? ''}`;
const license = `${rec?.Profile?.UserLicense?.Name ?? ''}`;
const unifiedEmployee = UNIFIED_RE.test(license) || UNIFIED_RE.test(profile);
const sysAdmin = SYSADMIN_RE.test(profile);

const offer = [];
if (useTier?.present && unifiedEmployee) offer.push(useTier);
if (adminTier?.present && sysAdmin) offer.push(adminTier);

const omit = offer.length === 0;
let note;
if (!avail.ok) {
  note = `availability capture unreadable (${avail.reason}) — cannot gate Unified Catalog; omit for this user.`;
} else if (!provisioned) {
  note = 'Unified Catalog is not provisioned on this org — skip it (already handled by the availability classifier).';
} else if (!userEnv.ok) {
  note = `target-user capture unreadable (${userEnv.reason}) — cannot confirm the user's cohort; omit Unified Catalog for this user.`;
} else if (omit) {
  note = `This user (license "${license || '?'}", profile "${profile || '?'}") is neither a Unified Employee (Community User tier) nor a System Administrator (Admin tier) — omit Unified Catalog for this user; report "not applicable for this user's license/profile — skipped".`;
} else {
  note = `Offer the ${offer.map((t) => t.tier).join(' + ')} tier(s) for Unified Catalog (unifiedEmployee=${unifiedEmployee}, sysAdmin=${sysAdmin}).`;
}

emit({
  feature: 'Unified Catalog',
  provisioned,
  user: { profile, license, unifiedEmployee, sysAdmin },
  offer,
  omit,
  note,
});
