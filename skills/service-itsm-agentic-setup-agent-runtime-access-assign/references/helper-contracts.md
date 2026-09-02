# Helper Script Contracts — service-itsm-agentic-setup-agent-runtime-access-assign

All seven scripts are deterministic, side-effect-free JSON classifiers (A9). Each
reads one or more `sf data query --json` / `sf api request rest` captures and
emits a single JSON object to stdout. Exit is `0` on any parseable body — the
verdict is carried in the payload. Exit `2` is a usage error (missing args); the
scripts never exit non-zero on a workflow-blocking condition — that is the
caller's job based on the emitted `verdict`.

## `scripts/classify-platform-permset-availability.mjs`

Which platform features are provisioned, and each tier's `present` + `needsPsl`.

### Input

1. `permsets.json` — `sf data query --json` capture of `PermissionSet` filtered
   to the six known feature-tier `Name` values (see `permset-topology.md`).

### Output

```json
{
  "features": [
    { "feature": "Prompt Templates",
      "tiers": {
        "use":   { "tier":"use",   "name":"EinsteinGPTPromptTemplateUser",    "displayLabel":"Prompt Template User",    "present":true, "Id":"0PS…", "LicenseId":"0PL…", "needsPsl":true },
        "admin": { "tier":"admin", "name":"EinsteinGPTPromptTemplateManager", "displayLabel":"Prompt Template Manager", "present":true, "Id":"0PS…", "LicenseId":"0PL…", "needsPsl":true }
      },
      "anyPresent": true }
  ],
  "provisionedFeatures": ["Prompt Templates","Data Cloud"],
  "absentFeatures": ["Unified Catalog"],
  "verdict": "ASSIGNABLE",
  "reasons": ["..."]
}
```

- `displayLabel` prefers the org's own `Label`; falls back to a canonical label only when the row is absent.
- `needsPsl` is per row (`LicenseId !== null`). Read it from the SELECTED tier.

| verdict | Meaning | Caller action |
|---|---|---|
| `ASSIGNABLE` | ≥1 feature provisioned | Ask a tier per provisioned feature; skip + report absent features |
| `NONE-PROVISIONED` | no feature permset present | Report it; still continue to the Agent Access concern |
| `CANNOT-CONFIRM` | query envelope unparseable | Surface `reasons[]` verbatim and stop |

**Never auto-select a tier.** Present use/agent vs admin and let the user pick.

## `scripts/gate-unified-catalog-tiers.mjs`

Per **target user**, which **Unified Catalog** tiers are eligible to offer — or
whether to omit Unified Catalog for that user. The Unified Catalog PSLs are
license-**shape** gated (not seat-gated): the Community User tier can be held only
by a **Unified Employee**-licensed user, and the Admin tier is meaningful only for
a **System Administrator**. Offering a tier the user's license/profile can never
hold is a hard write-time failure, so this gate runs *before* the tier prompt.

### Input (two positional args)

1. `availability.json` — the `classify-platform-permset-availability.mjs` output
   capture (carries the Unified Catalog `use`/`admin` tier objects with
   `present`/`Id`/`LicenseId`/`needsPsl`).
2. `user.json` — a `sf data query --json` capture of the **one** target user,
   selecting `Profile.Name` and `Profile.UserLicense.Name`.

### Output

```json
{
  "feature": "Unified Catalog",
  "provisioned": true,
  "user": { "profile":"System Administrator", "license":"Salesforce", "unifiedEmployee":false, "sysAdmin":true },
  "offer": [ { "tier":"admin", "name":"UnifiedCatalogAdmin", "Id":"0PS…", "LicenseId":"0PL…", "needsPsl":true } ],
  "omit": false,
  "note": "..."
}
```

- `offer[]` is the subset of **present** UC tiers this user is eligible for: `use`
  (`UnifiedCatalogCommunityUser`) only when `unifiedEmployee`; `admin`
  (`UnifiedCatalogAdmin`) only when `sysAdmin`. Feed those tier objects straight to
  the tier prompt / write path.
- `omit:true` (empty `offer[]`) ⇒ do **not** present Unified Catalog for this user;
  report it "not applicable for this user's license/profile — skipped" (never a
  failed write). Run the gate **once per target user**, each against **that user's
  own capture file** (the target-user picker is a multi-select — capture each user to
  a distinct `/tmp/itsm-target-user-<username>.json`, never a shared path that a later
  lookup would clobber), and retain each user's result with that user's assignment
  plan — different users can differ.
- Fails **closed**: an unreadable availability or user capture ⇒ `omit:true` (better
  to skip than to offer a tier that will fail); the reason is in `note`. Always exits
  `0` on parseable bodies; exit `2` only on missing argv.

## `scripts/resolve-target-user.mjs`

Extracts the running user's `005…` Id from the API-root `identity` URL.

### Input

1. `api-root.json` — capture of `sf api request rest "/services/data/v67.0/" --method GET`.

### Output

`{ userId, identity, verdict: "RESOLVED" | "CANNOT-CONFIRM", reasons }`. The
trailing path segment must match `^005[A-Za-z0-9]{12}([A-Za-z0-9]{3})?$` (15 or
18 chars). Any other shape ⇒ `CANNOT-CONFIRM` (surface verbatim; do NOT fall back
to prose parsing).

## `scripts/rank-candidate-users.mjs`

Up to five real, non-service candidate users to OFFER as selectable options when
the caller did not name a target user. A presentation aid, never a gating decision.

### Input (three positional args)

1. `users.json` — `sf data query --json` capture selecting active users with
   `Id, Name, Username, Profile.Name, Profile.UserLicense.Name`.
2. `audience` — `fulfiller` | `employee` | `any` (anything else ⇒ `any`). A
   Fulfiller agent is run by IT staff on a **standard** license; an Employee agent
   by end employees on a **Unified Employee** license — the matching cohort is
   surfaced first.
3. `runningUserId` (optional) — the "Me" user, excluded from candidates (it is
   offered separately as the recommended option).

### Output

```json
{
  "candidates": [ { "Id":"005…", "Name":"Ada Lovelace", "Username":"ada@example.com", "profile":"Standard User", "cohort":"standard" } ],
  "audience": "fulfiller",
  "total": 3,
  "note": "Offering 3 candidate(s), standard cohort first (audience: fulfiller)."
}
```

- Service/integration/bot/agent accounts (matched on profile, license, username,
  or display name) are filtered out; `candidates[]` is capped at five.
- `cohort` is `unified-employee` when the user's Unified Employee **license**
  (`Profile.UserLicense.Name`) matches — or, defensively, their `Profile.Name` — else
  `standard`. The license is the authoritative signal, so a custom profile carrying
  the license still ranks as Unified Employee. The audience-matching cohort is ranked
  first; input order (the query orders by most-recent login) is preserved within a cohort.
- Empty `candidates[]` (no non-service humans, or an unreadable capture) ⇒ offer
  **"Me"** plus the free-text **"Other"** option only. Always exits `0` on a
  parseable body; exit `2` only on missing argv.
- The `AskUserQuestion` picker takes ≤4 options, so offer **"Me"** plus the **top
  three** candidates; the rest stay reachable via **"Other"**.

## `scripts/classify-activated-agents.mjs`

The activated-agent candidate list for the `Agent_Access` grants.

### Input

1. `bot-definitions.json` — capture of the `BotDefinition` + `(SELECT Status FROM BotVersions WHERE Status='Active')` query.

### Output

```json
{
  "agents": [ { "Id":"0Xx…", "DeveloperName":"IT_Service_Fulfiller_Agent", "MasterLabel":"IT Service Fulfiller Agent", "active": true } ],
  "activatedAgents": [ { "Id":"0Xx…", "DeveloperName":"…", "MasterLabel":"…" } ],
  "inactiveAgents": [],
  "verdict": "AGENTS-FOUND" | "NONE-ACTIVE" | "CANNOT-CONFIRM",
  "reasons": ["..."]
}
```

An agent is `active` iff its `BotVersions` child subquery returns ≥1 row. Only
`activatedAgents[]` are offered for the multi-select.

| verdict | Meaning | Caller action |
|---|---|---|
| `AGENTS-FOUND` | ≥1 activated agent | Present `activatedAgents[]` for multi-select |
| `NONE-ACTIVE` | no activated agent (none exist, or none active) | Report it; if features are also `NONE-PROVISIONED`, stop |
| `CANNOT-CONFIRM` | query envelope unparseable | Surface `reasons[]` verbatim and stop |

## `scripts/classify-agent-access-state.mjs`

Whether `Agent_Access` must be created and which chosen agents still need a grant.

### Input (three positional args)

1. `agent-access-permset.json` — `PermissionSet WHERE Name='Agent_Access'` capture.
2. `sea-existing.json` **OR** the sentinel `NO-PERMSET`:
   - permset present ⇒ pass the `SetupEntityAccess WHERE ParentId=<permsetId> AND SetupEntityType='BotDefinition'` capture.
   - permset absent ⇒ pass `NO-PERMSET` (no parent to query yet).
3. `chosenAgentIds-csv` — comma-separated `BotDefinition` Ids the user selected.

### Output

```json
{
  "permsetExists": false, "permsetId": null,
  "chosenAgentIds": ["0Xx…","0Xx…"],
  "grantedAgentIds": [], "missingAgentIds": ["0Xx…","0Xx…"],
  "needsCreate": true, "needsGrants": true,
  "verdict": "NEEDS-WORK" | "ALREADY-COMPLETE" | "CANNOT-CONFIRM",
  "reasons": ["..."]
}
```

| verdict | Meaning | Caller action |
|---|---|---|
| `NEEDS-WORK` | permset missing and/or ≥1 chosen agent ungranted | Confirm-to-write, then create (if `needsCreate`) + grant each `missingAgentIds` |
| `ALREADY-COMPLETE` | permset exists and grants every chosen agent | No `SetupEntityAccess` write; still assign the permset to the user(s) if needed |
| `CANNOT-CONFIRM` | envelope unparseable, or a contradictory `NO-PERMSET`/empty-chosen input | Surface `reasons[]` verbatim and stop |

## `scripts/classify-assignment-state.mjs`

Per user + permset idempotency (feature tier OR `Agent_Access`).

### Input (two positional args)

1. `psa-existing.json` — `PermissionSetAssignment` capture for the target user + permset Id.
2. `psla-existing.json` **OR** the sentinel `NO-PSL`:
   - selected tier `needsPsl:true` ⇒ pass the `PermissionSetLicenseAssign` capture.
   - standalone (`Agent_Access`, or any `needsPsl:false` tier) ⇒ pass `NO-PSL`; `licenseAssigned` is reported `null`.

### Output

`{ permsetAssigned, licenseAssigned, needsWrite, verdict, reasons }`.

| verdict | Meaning | Caller action |
|---|---|---|
| `NEEDS-WRITE` | permset (or, when `needsPsl:true`, its license) missing | Confirm-to-write, then assign (PSL first if `needsPsl:true`; permset only if `false`) |
| `ALREADY-ASSIGNED` | all applicable rows present | Skip the write; go to verify |
| `CANNOT-CONFIRM` | a query envelope was unparseable | Surface `reasons[]` verbatim and stop |

## Why deterministic classifiers?

Every decision that gates a write or a success report lives in a script, not in
prose. Model interpretation of `records[].length === 0` is a documented source of
false-positive skips ("empty, so nothing exists — proceed") when the real cause
was an auth failure that returned an empty envelope. The scripts distinguish a
real empty result from a failed read and carry the difference in the verdict.
