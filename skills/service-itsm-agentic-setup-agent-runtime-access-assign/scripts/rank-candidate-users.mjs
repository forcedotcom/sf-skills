#!/usr/bin/env node
// Ranks REAL, human candidate users to offer as selectable options behind the
// Phase-2 AskUserQuestion when the caller did not name a target user. This is a
// presentation aid, never a gating decision — it keeps the offered list
// deterministic (no editorializing down to one name) and audience-appropriate.
//
// Inputs (argv):
//   1. users.json     — capture of `sf data query --json` selecting active users
//                        with Id, Name, Username, Profile.Name, Profile.UserLicense.Name.
//   2. audience       — 'fulfiller' | 'employee' | 'any' (anything else ⇒ 'any').
//                       A Fulfiller agent is run by IT staff on a STANDARD license;
//                       an Employee agent by end employees on a UNIFIED EMPLOYEE
//                       license — so the matching cohort is surfaced first.
//   3. runningUserId  — optional; the "Me" user, excluded here (offered separately
//                       as the recommended option).
//
// Output (stdout JSON):
//   { candidates: [ { Id, Name, Username, profile, cohort } ], audience, total, note }
//   at most 5 candidates; service/integration/bot/agent accounts removed. Exit is
//   always 0 on a parseable body (empty candidates ⇒ offer "Me" + free-text only);
//   exit 2 only on missing argv.

import { readFileSync } from 'node:fs';

// Non-human / service accounts are never good runtime-access targets. Matched on
// profile name, license name, username, OR display name so a mislabeled record
// on any one field is still filtered.
const SERVICE_RE = /integration|automated process|einstein agent|analytics cloud|salesforceiq|\binsights\b|chatter (free|external)|guest|portal|sites|\bbot\b|botuser|digitalagent/i;

// The Unified Employee cohort — the human tier an Employee agent's users belong to.
// It is defined by the Unified Employee USER LICENSE, which is the authoritative
// signal; the profile name is only a defensive fallback (a custom profile carrying
// the license must still rank as Unified Employee).
const UNIFIED_RE = /unified\s*employee/i;

function readEnvelope(path) {
  try {
    const text = readFileSync(path, 'utf8').trim();
    if (!text) return { ok: false, reason: `empty file: ${path}` };
    const data = JSON.parse(text);
    if (data && typeof data.status === 'number' && data.status !== 0) {
      return { ok: false, reason: `sf data query at ${path} failed with status ${data.status}` };
    }
    const records = Array.isArray(data?.result?.records) ? data.result.records : null;
    if (!records) return { ok: false, reason: `missing result.records[] at ${path}` };
    return { ok: true, records };
  } catch (e) {
    return { ok: false, reason: `unreadable/invalid JSON at ${path}: ${e?.message ?? e}` };
  }
}

function emit(obj) {
  process.stdout.write(JSON.stringify(obj, null, 2) + '\n');
}

const [usersPath, audienceArg, runningUserId] = process.argv.slice(2);
if (!usersPath) {
  process.stderr.write('usage: node rank-candidate-users.mjs <users.json> [fulfiller|employee|any] [runningUserId]\n');
  process.exit(2);
}
const audience = (audienceArg === 'fulfiller' || audienceArg === 'employee') ? audienceArg : 'any';

const env = readEnvelope(usersPath);
if (!env.ok) {
  emit({ candidates: [], audience, total: 0, note: `${env.reason} — offer "Me" plus free-text entry only.` });
  process.exit(0);
}

const profileName = (r) => `${r?.Profile?.Name ?? ''}`;
const licenseName = (r) => `${r?.Profile?.UserLicense?.Name ?? ''}`;
const isService = (r) =>
  SERVICE_RE.test(profileName(r)) || SERVICE_RE.test(licenseName(r)) ||
  SERVICE_RE.test(`${r?.Username ?? ''}`) || SERVICE_RE.test(`${r?.Name ?? ''}`);
const cohortOf = (r) =>
  (UNIFIED_RE.test(licenseName(r)) || UNIFIED_RE.test(profileName(r)) ? 'unified-employee' : 'standard');

const humans = env.records
  .filter((r) => r && typeof r.Id === 'string')
  .filter((r) => r.Id !== runningUserId)
  .filter((r) => !isService(r))
  .map((r) => ({ Id: r.Id, Name: r.Name ?? r.Username, Username: r.Username, profile: profileName(r), cohort: cohortOf(r) }));

// Rank the audience-matching cohort first, preserving input order within a cohort
// (the query already orders by most-recent login).
const prefer = audience === 'employee' ? 'unified-employee' : audience === 'fulfiller' ? 'standard' : null;
const ranked = prefer
  ? [...humans.filter((u) => u.cohort === prefer), ...humans.filter((u) => u.cohort !== prefer)]
  : humans;

const candidates = ranked.slice(0, 5);
const note = candidates.length === 0
  ? 'No non-service human users found besides the running user — offer "Me" plus free-text entry only.'
  : `Offering ${candidates.length} candidate(s)${prefer ? `, ${prefer} cohort first (audience: ${audience})` : ''}.`;

emit({ candidates, audience, total: humans.length, note });
