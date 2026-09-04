# Orchestration Flow

## Dependency Diagram

```text
┌───────────────────────────────────────────────────────────────────┐
│                    LIFE SCIENCES CLOUD SETUP                       │
└───────────────────────────────────────────────────────────────────┘

Stage 1: life-sciences-prerequisites-validate
├── Validates: org settings, permissions, OWD, features
├── Gate: All 13 checks pass (or user explicitly skips)
└── Outputs: Confirmation that org is ready

        │
        ▼

Stage 2: Starter Config Deploy (references/stage-2-starter-config-overview.md)
├── Deploys: StandardValueSets, objects, profiles, config records,
│            trigger handlers, layouts, flexipages, application
├── Gate: LSC Custom Profile exists in org (query confirms)
└── Outputs: Profile ID for user provisioning

        │
        ▼

Stage 3: life-sciences-territory-configure
├── Creates: Territory Type, Territory Model, 3-level hierarchy
├── Activates: Territory Model (Planning → Active)
├── Gate: Model state = Active, Level-3 territory queryable
└── Outputs: Territory2 ID and DeveloperName for user assignment

        │
        ▼

Stage 4: User Provisioning (references/stage-4-user-provisioning-overview.md)
├── Creates: Active user with LSC Custom Profile
├── Assigns: 4 permission sets
├── Assigns: New user + admin to level-3 territory
├── Gate: All assignments verified
└── Outputs: User ID, rep username for visit login

        │
        ▼

Stage 5: Visit Creation (references/stage-5-visit-creation-overview.md)
├── Logs in: as the rep user from Stage 4 (sf org login web)
├── Creates (rep): Account, HealthcareProvider, Visit, ProviderVisit,
│                  product detailing/discussion
├── Creates (admin): territory associations, product master data
├── Generates: mobile metadata cache (Connect API, admin)
├── Gate: at least one Visit record exists
└── Outputs: Visit ID, confirmation of records + metadata cache
```

---

## Gate Verification Queries

### After Stage 1 — Prerequisites

No automated query — the prerequisites skill produces a pass/fail table. Gate on all PASS or explicit user override.

### After Stage 2 — Starter Config

```bash
sf data query --query "SELECT Id, Name FROM Profile WHERE Name = 'LSC Custom Profile'" --target-org <org> --json
```

Expected: exactly 1 record returned.

### After Stage 3 — Territory

```bash
sf data query --query "SELECT Id, Name, DeveloperName, Territory2Model.DeveloperName, Territory2Model.State FROM Territory2 WHERE ParentTerritory2.ParentTerritory2Id != null AND Territory2Model.State = 'Active'" --target-org <org> --json
```

Expected: at least 1 record (the level-3 territory in an Active model).

### After Stage 4 — User Provisioning

```bash
sf data query --query "SELECT Id, Name, Username, Profile.Name, IsActive FROM User WHERE Username = '<username>'" --target-org <org> --json
```

Expected: 1 record with `Profile.Name = 'LSC Custom Profile'` and `IsActive = true`.

```bash
sf data query --query "SELECT PermissionSet.Label FROM PermissionSetAssignment WHERE AssigneeId = '<userId>' AND PermissionSet.Label IN ('Life Sciences Core', 'Life Sciences Field Sales Representative', 'Health Cloud Starter')" --target-org <org> --json
```

Expected: 3 records.

```bash
sf data query --query "SELECT User.Name FROM UserTerritory2Association WHERE Territory2Id = '<territoryId>'" --target-org <org> --json
```

Expected: at least 2 records (new user + admin).

### After Stage 5 — Visit Creation

```bash
sf data query --query "SELECT Id, Subject, TerritoryId FROM Visit ORDER BY CreatedDate DESC LIMIT 1" --target-org <org> --json
```

Expected: at least 1 Visit record (created against the level-3 territory).

Optionally confirm the metadata cache job ran:

```bash
sf data query --query "SELECT Id, Status, LastModifiedDate FROM LifeSciMobileMetadataRecord ORDER BY LastModifiedDate DESC LIMIT 1" --target-org <org> --json
```

Expected: a record whose `Status` has transitioned from `ValidationCompleted` to **`Active`** after the async job runs — `Active` is the success state (verified against the org). A transition to `Inactive`, or records stuck at `ValidationCompleted`, means the job failed or never ran — check `IntegrationErrorMessage` and Setup → Apex Jobs.

---

## Resume Logic

When the user re-runs the orchestrator after a partial completion:

| Stage | How to detect completion | Query |
|------|------------------------|-------|
| 1 | Cannot detect programmatically | Ask user |
| 2 | Profile exists | `SELECT Id FROM Profile WHERE Name = 'LSC Custom Profile'` |
| 3 | Active model + L3 territory | `SELECT Id FROM Territory2 WHERE ParentTerritory2.ParentTerritory2Id != null AND Territory2Model.State = 'Active'` |
| 4 | User exists with correct profile | `SELECT Id FROM User WHERE Username = '<username>' AND Profile.Name = 'LSC Custom Profile'` |
| 5 | A Visit record exists | `SELECT Id FROM Visit LIMIT 1` |

If a stage is detected as complete, show the user what was found and ask: "Stage N appears complete (<evidence>). Skip it? (yes/no)"

---

## Timing Expectations

| Stage | Typical Duration | Notes |
|------|-----------------|-------|
| 1 - Prerequisites | 1-2 minutes | Read-only queries |
| 2 - Starter Config | 5-15 minutes | 13 deploy steps, interactive layout/flexipage selection |
| 3 - Territory Setup | 2-5 minutes | Interactive name confirmation + deploy + activation |
| 4 - User Provisioning | 2-3 minutes | Interactive user detail collection + creates |
| 5 - Visit Creation | 3-6 minutes | Interactive rep login + record creation + async metadata cache |
| **Total** | **13-31 minutes** | Depends on user interaction speed |
