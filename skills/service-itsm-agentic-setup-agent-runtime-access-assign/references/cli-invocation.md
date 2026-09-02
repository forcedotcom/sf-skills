# CLI Invocation — service-itsm-agentic-setup-agent-runtime-access-assign

Every read and write uses the **Salesforce CLI (`sf`)** against the CLI's stored
session for `--target-org <alias>`. **Never extract the access token** from
`sf org display` — hand-building a raw HTTP request bypasses the CLI session and
leaks a bearer token into shell context.

## `--json` rule

- `sf data query` **takes** `--json` → `{status, result:{records:[...]}}` envelope. That is what the classifier scripts expect.
- `sf api request rest` does **not** — its raw stdout body is already JSON. Passing `--json` errors on some endpoints.
- `sf org assign permset` **takes** `--json` → `result:{successes:[...], failures:[...]}`.

## Phase 1 — discovery reads

Platform feature permsets (see `permset-topology.md` for the fixed six Names):

```bash
sf data query \
  -q "SELECT Id, Name, Label, LicenseId FROM PermissionSet WHERE Name IN ('EinsteinGPTPromptTemplateUser','EinsteinGPTPromptTemplateManager','GenieUserEnhancedSecurity','GenieAdmin','UnifiedCatalogCommunityUser','UnifiedCatalogAdmin')" \
  --target-org <alias> --json
```

Activated agents (an agent is activated iff the `BotVersions` child returns ≥1 row):

```bash
sf data query \
  -q "SELECT Id, DeveloperName, MasterLabel, (SELECT Status FROM BotVersions WHERE Status='Active') FROM BotDefinition WHERE Type='InternalCopilot'" \
  --target-org <alias> --json
```

## Phase 2 — identity read

```bash
sf api request rest "/services/data/v67.0/" --method GET --target-org <alias>
```

`identity` is a URL ending in `/<orgId>/<userId>`; take the trailing `005…`
segment via `scripts/resolve-target-user.mjs`. Do NOT call `USER_ID()` (Apex-only)
or `/chatter/users/me` (403 when Chatter is off).

The resolver returns only `{ userId, identity, verdict }` — it carries no name. To
label the running-user option **"Me — <name>"** (fall back to just **"Me"** if this
returns nothing), read the name explicitly. Then query active org users with the
fields the ranker needs (`Profile.Name`, `Profile.UserLicense.Name`) and hand them
to `rank-candidate-users.mjs`, which filters out service/integration/bot/agent
accounts and returns up to five real candidates ranked for the `<audience>`
(`fulfiller` ⇒ standard-license users first; `employee` ⇒ Unified Employee users
first; `any` ⇒ input order):

The running-user query also selects `Profile.Name` + `Profile.UserLicense.Name` —
the Unified Catalog gate (Phase 3) needs the target user's license/profile:

```bash
sf data query -q "SELECT Name, Profile.Name, Profile.UserLicense.Name FROM User WHERE Id = '<userId>'" \
  --target-org <alias> --json > /tmp/itsm-running-user.json 2>/dev/null || true

sf data query -q "SELECT Id, Name, Username, Profile.Name, Profile.UserLicense.Name FROM User WHERE IsActive = true ORDER BY LastLoginDate DESC NULLS LAST LIMIT 25" \
  --target-org <alias> --json > /tmp/itsm-candidate-users.json 2>/dev/null || true

node "<skill_dir>/scripts/rank-candidate-users.mjs" /tmp/itsm-candidate-users.json <audience> <userId>
```

The `AskUserQuestion` picker takes at most four options, so offer **"Me — <name>"**
(recommended) plus the **top three** ranked candidates; its built-in **"Other"**
free-text option covers any username not listed. Determine `<audience>` from the
agent this grant is for (named in the request/handoff, or the Phase-1 activated
set) — a Fulfiller agent is run by IT staff (standard license), an Employee agent
by end employees (Unified Employee).

Named user (or any chosen/typed option) — also select the profile + license so the
Unified Catalog gate can run for this user. **Capture each selected user to its own
file**, keyed by username — never a single shared path: the target-user picker is a
multi-select, so a fixed file would clobber earlier users and mis-gate them against
the last user's license/profile:

```bash
# Run once per selected user; each writes a distinct, username-keyed file.
sf data query -q "SELECT Id, Username, Name, IsActive, Profile.Name, Profile.UserLicense.Name FROM User WHERE Username = '<username>'" \
  --target-org <alias> --json > "/tmp/itsm-target-user-<username>.json"
```

## Phase 3 — Unified Catalog per-user tier gate

The Unified Catalog PSLs are license-**shape** gated: the Community User tier can
be held only by a **Unified Employee** user and the Admin tier only by a **System
Administrator**. Before asking the Unified Catalog tier, run the gate **once per
selected target user** against **that user's own capture**
(`/tmp/itsm-running-user.json` for the running user,
`/tmp/itsm-target-user-<username>.json` for each named user) plus the Phase-1
availability capture, and **retain each user's `offer[]`/`omit` with that user's
assignment plan** — never reuse one user's result for another. Offer only the tiers
in `offer[]`, and on `omit` skip Unified Catalog for that user as "not applicable for
this user's license/profile — skipped":

```bash
node "<skill_dir>/scripts/classify-platform-permset-availability.mjs" /tmp/itsm-platform-permsets.json > /tmp/itsm-availability.json
# Running user:
node "<skill_dir>/scripts/gate-unified-catalog-tiers.mjs" /tmp/itsm-availability.json /tmp/itsm-running-user.json
# Each named user — against that user's own capture:
node "<skill_dir>/scripts/gate-unified-catalog-tiers.mjs" /tmp/itsm-availability.json "/tmp/itsm-target-user-<username>.json"
```

## Phase 4 — idempotency reads

Agent Access permset + its existing `BotDefinition` grants (second query only
when the permset exists — else pass `NO-PERMSET` to the classifier):

```bash
sf data query -q "SELECT Id, Name, Label FROM PermissionSet WHERE Name='Agent_Access'" \
  --target-org <alias> --json > /tmp/agent-access.json

sf data query -q "SELECT SetupEntityId FROM SetupEntityAccess WHERE ParentId='<permsetId>' AND SetupEntityType='BotDefinition'" \
  --target-org <alias> --json > /tmp/sea.json
```

Per user + permset (feature tier or `Agent_Access`). PSLA query only when the
selected tier's `needsPsl:true`:

```bash
sf data query -q "SELECT Id FROM PermissionSetAssignment WHERE AssigneeId='<userId>' AND PermissionSetId='<permsetId>'" \
  --target-org <alias> --json > /tmp/psa.json

sf data query -q "SELECT Id FROM PermissionSetLicenseAssign WHERE AssigneeId='<userId>' AND PermissionSetLicenseId='<licenseId>'" \
  --target-org <alias> --json > /tmp/psla.json
```

## Phase 6 — writes

**Create `Agent_Access`** (only if `needsCreate`). `Name` is the API name;
`Label` is the display label:

```bash
sf api request rest "/services/data/v67.0/sobjects/PermissionSet" \
  --method POST \
  --body '{"Name":"Agent_Access","Label":"Agent Access"}' \
  --target-org <alias>
```

Response: `{"id":"0PS...","success":true,"errors":[]}`. Capture `id` — it is the
`ParentId` for the grants.

**Grant each chosen agent** (`SetupEntityId` = the `BotDefinition` Id). Send
`ParentId` + `SetupEntityId` ONLY — `SetupEntityType` is not creatable:

```bash
sf api request rest "/services/data/v67.0/sobjects/SetupEntityAccess" \
  --method POST \
  --body '{"ParentId":"<permsetId>","SetupEntityId":"<botDefinitionId>"}' \
  --target-org <alias>
```

`DUPLICATE_VALUE` here ⇒ that agent is already granted; treat as success.

**PSL first, then permset** for a license-gated feature tier (`needsPsl:true`).
Use the selected tier's own `LicenseId` as `PermissionSetLicenseId`:

```bash
sf api request rest "/services/data/v67.0/sobjects/PermissionSetLicenseAssign" \
  --method POST \
  --body '{"AssigneeId":"<userId>","PermissionSetLicenseId":"<licenseId>"}' \
  --target-org <alias>

# Running user (the default target): OMIT --on-behalf-of; the command assigns to
# the authenticated user.
sf org assign permset --name "<permsetName>" --target-org <alias> --json
# A NAMED target user: pass their resolved <username> — NOT a 005 Id.
sf org assign permset --name "<permsetName>" --on-behalf-of "<username>" \
  --target-org <alias> --json
```

> **`--on-behalf-of` resolves by `Username`/alias, not a `005…` user Id.** Passing
> a user Id fails to match. For the running user (the default target) omit the flag
> entirely; for a named user pass the `<username>` resolved by the
> `WHERE Username=` query. Do **not** substitute a `$USERNAME` shell variable — in
> zsh it is a read-only builtin bound to the OS user and will silently mis-target.

**`Agent_Access` assignment** per user (standalone — no PSL):

```bash
# Running user (default): OMIT --on-behalf-of.
sf org assign permset --name "Agent_Access" --target-org <alias> --json
# Named user: --on-behalf-of "<username>" (Username, never a 005 Id).
sf org assign permset --name "Agent_Access" --on-behalf-of "<username>" \
  --target-org <alias> --json
```

`sf org assign permset` response: `result.successes[]` / `result.failures[]`; a
`failure.message` matching `Duplicate id`/`already has` is idempotent success.

## Phase 7 — verify read-backs

Re-run the Phase-4 `PermissionSetAssignment` / `PermissionSetLicenseAssign`
queries for each target user, and the `SetupEntityAccess` query for
`Agent_Access`, and confirm each intended row is now present.

## Common error responses (surface verbatim)

| Status / errorCode | Meaning | Handling |
|---|---|---|
| `400 DUPLICATE_VALUE` on any POST | Row already exists | Idempotent success; not a failure |
| `400 INSUFFICIENT_ACCESS` on a PSL POST | Seat exhausted | STOP that write; tell the user no seats are available |
| `400`/`404` on `SetupEntityAccess` POST with `SetupEntityType` in body | Field not creatable | Remove `SetupEntityType`; send `ParentId`+`SetupEntityId` only |
| `401 Unauthorized` | CLI session expired | `sf org login web --alias <alias>` and retry |
| `404 Not Found` on `sf org assign permset` | Permset name absent on this org | Re-run Phase 1 discovery; org state may have changed |
