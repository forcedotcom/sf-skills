# Platform Feature Permset Topology + Agent Access Mechanism

This skill grants a **user** two kinds of access after an ITSM agent is
activated:

1. the **runtime action-execution permissions** the agent's actions call, and
2. **access to the activated agents themselves** via a custom `Agent_Access`
   permission set.

## 1. Platform feature permsets (runtime action execution)

Verified live against real orgs. Each feature has a lighter **use/agent** tier
(enough to *use* the feature at runtime) and a full **admin** tier. All shipped
tiers observed are **license-gated** (`LicenseId != null` → `needsPsl:true`), but
the write path never assumes this — it reads `needsPsl` per row.

| Feature | use/agent tier (PermissionSet.Name) | admin tier (PermissionSet.Name) | Notes |
|---|---|---|---|
| Prompt Templates | `EinsteinGPTPromptTemplateUser` ("Prompt Template User") | `EinsteinGPTPromptTemplateManager` ("Prompt Template Manager") | both tiers share one PSL (`EinsteinGPTPromptTemplatesPsl`) |
| Data Cloud | `GenieUserEnhancedSecurity` ("Data Cloud User") | `GenieAdmin` (ships as "Data Cloud Architect" or "Data Cloud Admin") | both tiers share one PSL (`GenieDataPlatformStarterPsl`) |
| Unified Catalog | `UnifiedCatalogCommunityUser` ("Unified Catalog Community User") | `UnifiedCatalogAdmin` ("Unified Catalog Admin") | tiers are backed by per-tier PSLs (`UnifiedCatalogCommunityUserPsl` / `UnifiedCatalogAdminPsl`). **`UnifiedCatalogAgent` is NOT the human tier** — its shipped Description reads "Enables the *agent* to run service process", i.e. it is the agent's own bot-runtime identity permset, not what a human user assigns to exercise the agent |

### Key facts

- **No single org has all three features.** On a Prompt-Template + Data-Cloud
  org, the two Unified Catalog rows simply do not exist — the classifier reports
  Unified Catalog `absent` and the skill skips it. This is expected, not a
  failure. Detect-if-present / assign-what-is-there / report-the-rest is the
  whole point of the availability classifier.
- **Display label comes from the org.** `GenieAdmin` renders as "Data Cloud
  Architect" on some orgs and "Data Cloud Admin" on others — the classifier
  prefers the row's own `Label` and falls back to the canonical label only when
  the row is absent. Never hard-code the label in user-facing text.
- **`needsPsl` is per row, from `LicenseId`.** The PSL POST uses the selected
  tier's own `LicenseId` as `PermissionSetLicenseId` — PSL *names* above are for
  human orientation only and are never queried by name in the write path.
- **Unified Catalog user tier = `UnifiedCatalogCommunityUser`, not `UnifiedCatalogAgent`.**
  The three shipped standard permsets and their productized `Description` are:
  `UnifiedCatalogAgent` = "Enables the **agent** to run service process" (the
  agent's own bot-runtime identity — a machine tier, not a human one);
  `UnifiedCatalogCommunityUser` = "Enables the **Community User** to **run**
  unified catalog service process" (the human RUN tier — what a user, including a
  Unified Employee user, assigns to exercise the agent's Unified Catalog actions);
  `UnifiedCatalogAdmin` = "Enables the user to **setup** unified catalog" (the
  admin/config tier). There is no plain `UnifiedCatalogUser`. So the human tiers
  are `UnifiedCatalogCommunityUser` (use) + `UnifiedCatalogAdmin` (admin);
  `UnifiedCatalogAgent` is deliberately excluded (it belongs to the agent's own
  user, provisioned elsewhere, not to the human being granted access here).
- `DataCloudAISpecialist` also exists but is not one of this skill's tiers.
- **Unified Catalog tiers are license-SHAPE gated per target user.** Unlike Prompt
  Templates and Data Cloud (offered to any user), the two Unified Catalog PSLs can
  only be held by specific cohorts: `UnifiedCatalogCommunityUser` (the Community
  User / use tier) requires a **Unified Employee** license, and `UnifiedCatalogAdmin`
  (the Admin tier) is meaningful only for a **System Administrator**. Offering a UC
  tier to a user whose license/profile can't hold it is a hard write-time failure
  (a license-shape limit, not a seat shortage — retrying won't help). So
  `scripts/gate-unified-catalog-tiers.mjs` runs per target user and offers the
  Community User tier only to a Unified Employee user, the Admin tier only to a
  System Administrator, and **omits Unified Catalog entirely** for any other user
  (reported "not applicable for this user's license/profile — skipped", never a
  failed write). This gate is Unified-Catalog-specific; the other two features are
  not cohort-gated.

### Fixed-lookup discovery query (Phase 1)

```sql
SELECT Id, Name, Label, LicenseId
FROM PermissionSet
WHERE Name IN (
  'EinsteinGPTPromptTemplateUser',
  'EinsteinGPTPromptTemplateManager',
  'GenieUserEnhancedSecurity',
  'GenieAdmin',
  'UnifiedCatalogCommunityUser',
  'UnifiedCatalogAdmin'
)
```

## 2. Agent access via `Agent_Access` + `SetupEntityAccess`

An Agentforce / NGA agent is a **`BotDefinition`** record with
`Type = 'InternalCopilot'`. A permission set grants access to a specific agent
through a **`SetupEntityAccess`** row — exactly like granting Apex-class access:

```text
SetupEntityAccess {
  ParentId:      <permission set Id>,   // the Agent_Access permset
  SetupEntityId: <BotDefinition Id>     // the agent (0Xx… key prefix)
}
```

### Load-bearing details (verified via `sf sobject describe`)

- **`PermissionSet` is createable over the standard data API** (`createable:true`)
  with just `Name` + `Label`. Create `Agent_Access` with a POST to
  `/sobjects/PermissionSet` — no Tooling API, no Metadata XML, no deploy.
- **`SetupEntityAccess` is createable** with `ParentId` + `SetupEntityId`
  (both required, both `createable:true`).
- **`SetupEntityType` is NOT createable** (`createable:false`, picklist). It is
  derived from the `SetupEntityId` key prefix (`0Xx` → `BotDefinition`). Sending
  it in the POST body errors — omit it. It IS filterable on the read, so the
  idempotency query uses `WHERE ... AND SetupEntityType='BotDefinition'`.
- `SetupEntityAccess` is **not updateable** — grants are add/remove only, so the
  idempotent path is "read existing grants, add the missing ones".

### Activated-agent discovery query (Phase 1)

Only agents with an **active** version should be offered — a draft/inactive
agent has nothing to exercise yet:

```sql
SELECT Id, DeveloperName, MasterLabel,
       (SELECT Status FROM BotVersions WHERE Status='Active')
FROM BotDefinition
WHERE Type='InternalCopilot'
```

An agent is activated iff its `BotVersions` child subquery returns ≥1 row.

## Codesearch / verification note

The feature-permset matrix and the `SetupEntityAccess`/`BotDefinition` mechanism
were verified live. The Unified Catalog **user** tier was corrected from
`UnifiedCatalogAgent` to `UnifiedCatalogCommunityUser` after the shipped
`PermissionSet.Description` fields showed `UnifiedCatalogAgent` is the agent's own
bot-runtime permset ("Enables the agent to run service process"), while
`UnifiedCatalogCommunityUser` is the human run tier ("Enables the Community User
to run unified catalog service process"). If the shipped permset Names, their
`Description`, or the `SetupEntityAccess` create-field set drift on a future
release, re-verify with `sf sobject describe --sobject SetupEntityAccess` and
`SELECT Name, Label, Description, LicenseId FROM PermissionSet WHERE Name LIKE 'UnifiedCatalog%'`
before changing the fixed lists in `scripts/`.
