# Orchestration Flow (KAM)

## Dependency Diagram

```text
┌───────────────────────────────────────────────────────────────────┐
│              LIFE SCIENCES CLOUD KAM END-TO-END SETUP              │
└───────────────────────────────────────────────────────────────────┘

Setup: download .lsc-starter-config/LSStarterConfig (coordinator, once)
        │
        ▼
Stage 1: life-sciences-prerequisites-validate
├── Validates: org settings, permissions, OWD, features
├── Gate: All checks pass (or user explicitly skips)
└── Outputs: Confirmation that org is ready
        │
        ▼
Stage 2: Starter Config Deploy (references/stage-2-starter-config-overview.md)
├── Deploys: StandardValueSets (10 confirmed), objects, profiles, config records
│            (incl. KAMSettings + SprintSettings), trigger handlers,
│            4 KAM layouts, 6 KAM flexipages, application
├── Gate: LSC Custom Profile exists in org (query confirms)
└── Outputs: Profile ID; KAM/Sprint config records written
        │
        ▼
Stage 3: life-sciences-territory-configure
├── Creates (or reuses) Territory Type, Territory Model, 3-level hierarchy
├── Activates: Territory Model (Planning → Active)
├── Gate: Model state = Active, Level-3 territory queryable
└── Outputs: Level-3 Territory2 ID + name  ← reused in Stages 5 and 6
        │
        ▼
Stage 4: Participant Role & Sprint (references/stage-4-participant-role-and-sprint.md)
├── Creates: ParticipantRole "Rep Execution Specialist", Sprint "Sprint 1 …"
├── Gate: ParticipantRole (IsActive) + Sprint (Not Started) exist
└── Outputs: Role ID, Sprint ID
        │
        ▼
Stage 5: KAM Data & Plan Templates (references/stage-5-data-and-plan-templates-overview.md) — as ADMIN
├── Part A creates: Account, HealthcareProvider, ObjectTerritory2Association,
│            ProviderAcctTerritoryInfo, Product2, LifeSciMarketableProduct,
│            ContactPointAddress, ProductTerritoryAvailability (on Stage-3 territory)
├── Part B creates: 2 GoalDefinition, GoalDefinitionProduct, ActionPlanTemplate
│            (+ auto Version), 3 ActionPlanTemplateItem, ActionPlanTemplateAssignment;
│            publishes ActionPlanTemplate (status → Final);
│            shares goals + template + both PATI records to the leaf-territory Group
│            (2 GoalDefinitionShare + 1 ActionPlanTemplateShare + 2 ProviderAcctTerritoryInfoShare)
├── Gate: Account + LifeSciMarketableProduct + ProductTerritoryAvailability exist,
│         Final ActionPlanTemplateVersion + ActionPlanTemplateAssignment exist,
│         and the leaf-territory shares exist
└── Outputs: Account ID, LifeSciMarketableProduct ID, ActionPlanTemplateVersion ID
        │
        ▼
Stage 6: KAM User Provisioning (references/stage-6-user-provisioning-overview.md)
├── Creates: Active user (username contains "kam") on LSC Custom Profile
├── Assigns: 4 permission sets (HealthCloudStarter, LifeSciencesKeyAccountManager, LifeSciencesFieldSalesRepresentative, LifeSciencesCore)
├── Assigns: KAM user + admin to the Stage-3 level-3 territory
├── Generates: mobile metadata cache (Connect API, admin)
├── Gate: user active, 4 permsets, territory assigned, metadata cache Active
└── Outputs: KAM username, login URL
```

---

## Gate Verification Queries

### After Stage 1 — Prerequisites
No automated query — the prerequisites skill produces a pass/fail table. Gate on all PASS or explicit user override.

### After Stage 2 — Starter Config
```bash
sf data query --query "SELECT Id, Name FROM Profile WHERE Name = 'LSC Custom Profile'" --target-org <org> --json
```
Expected: exactly 1 record.

### After Stage 3 — Territory
```bash
sf data query --query "SELECT Id, Name, DeveloperName, Territory2Model.State FROM Territory2 WHERE ParentTerritory2.ParentTerritory2Id != null AND Territory2Model.State = 'Active'" --target-org <org> --json
```
Expected: at least 1 record (the level-3 territory in an Active model). Capture its Id + Name.

### After Stage 4 — Participant Role & Sprint
```bash
sf data query --query "SELECT Id, DeveloperName, IsActive FROM ParticipantRole WHERE DeveloperName = 'Rep_Execution_Specialist'" --target-org <org> --json
sf data query --query "SELECT Id, Name, Status FROM Sprint ORDER BY CreatedDate DESC LIMIT 1" --target-org <org> --json
```
Expected: ParticipantRole `IsActive=true`; Sprint with `Status='Not Started'`.

### After Stage 5 — KAM Data & Plan Templates

Part A (data):
```bash
sf data query --query "SELECT Id FROM LifeSciMarketableProduct ORDER BY CreatedDate DESC LIMIT 1" --target-org <org> --json
sf data query --query "SELECT Id, ProductId, TerritoryId FROM ProductTerritoryAvailability ORDER BY CreatedDate DESC LIMIT 1" --target-org <org> --json
```
Expected: a LifeSciMarketableProduct and a ProductTerritoryAvailability on the Stage-3 territory. Capture the LifeSciMarketableProduct Id.

Part B (plan templates):
```bash
sf data query --query "SELECT Id, ActionPlanTemplateId, Status FROM ActionPlanTemplateVersion WHERE Status = 'Final' ORDER BY CreatedDate DESC LIMIT 1" --target-org <org> --json
sf data query --query "SELECT Id FROM ActionPlanTemplateAssignment ORDER BY CreatedDate DESC LIMIT 1" --target-org <org> --json
sf data query --query "SELECT Id, ParentId, UserOrGroupId FROM GoalDefinitionShare WHERE RowCause = 'Manual' ORDER BY CreatedDate DESC LIMIT 2" --target-org <org> --json
sf data query --query "SELECT Id, ParentId, UserOrGroupId FROM ActionPlanTemplateShare WHERE RowCause = 'Manual' ORDER BY CreatedDate DESC LIMIT 1" --target-org <org> --json
sf data query --query "SELECT Id, ParentId, UserOrGroupId FROM ProviderAcctTerritoryInfoShare WHERE RowCause = 'Manual' ORDER BY CreatedDate DESC LIMIT 2" --target-org <org> --json
```
Expected: a `Final` ActionPlanTemplateVersion, an ActionPlanTemplateAssignment, and the leaf-territory shares (2 GoalDefinitionShare + 1 ActionPlanTemplateShare + 2 ProviderAcctTerritoryInfoShare) whose `UserOrGroupId` is the Stage-3 territory Group.

### After Stage 6 — User Provisioning
```bash
sf data query --query "SELECT Id, Name, Username, Profile.Name, IsActive FROM User WHERE Username = '<username>'" --target-org <org> --json
sf data query --query "SELECT COUNT(Id) c FROM PermissionSetAssignment WHERE AssigneeId = '<userId>' AND PermissionSet.IsOwnedByProfile = false" --target-org <org> --json
sf data query --query "SELECT User.Name FROM UserTerritory2Association WHERE Territory2Id = '<territoryId>'" --target-org <org> --json
```
Expected: user `IsActive=true` on `LSC Custom Profile`; permset count **4**; ≥2 territory associations (KAM user + admin).

Confirm the metadata cache reached `Active`:
```bash
sf data query --query "SELECT Id, Status, LastModifiedDate FROM LifeSciMobileMetadataRecord ORDER BY LastModifiedDate DESC LIMIT 1" --target-org <org> --json
```
Expected: `Status='Active'` after the async job runs. `Inactive`, or stuck at `ValidationCompleted`, means failure — check `IntegrationErrorMessage` and Setup → Apex Jobs.

---

## Resume Logic

When the user re-runs the orchestrator after a partial completion:

| Stage | How to detect completion | Query |
|------|------------------------|-------|
| 1 | Cannot detect programmatically | Ask user |
| 2 | Profile exists | `SELECT Id FROM Profile WHERE Name = 'LSC Custom Profile'` |
| 3 | Active model + L3 territory | `SELECT Id FROM Territory2 WHERE ParentTerritory2.ParentTerritory2Id != null AND Territory2Model.State = 'Active'` |
| 4 | Role + Sprint exist | `SELECT Id FROM ParticipantRole WHERE DeveloperName='Rep_Execution_Specialist'`; `SELECT Id FROM Sprint LIMIT 1` |
| 5 | Data + published template + territory shares exist | `SELECT Id FROM ProductTerritoryAvailability LIMIT 1`; `SELECT Id FROM ActionPlanTemplateVersion WHERE Status='Final' LIMIT 1`; `SELECT Id FROM ActionPlanTemplateShare WHERE RowCause='Manual' LIMIT 1` |
| 6 | KAM user exists | `SELECT Id FROM User WHERE Username LIKE '%kam%' AND Profile.Name = 'LSC Custom Profile'` |

If a stage is detected as complete, show the user what was found and ask: "Stage N appears complete (<evidence>). Skip it? (yes/no)"

---

## Timing Expectations

| Stage | Typical Duration | Notes |
|------|-----------------|-------|
| 1 - Prerequisites | 1-2 minutes | Read-only queries |
| 2 - Starter Config | 6-16 minutes | 13 deploy steps + SVS confirmations + KAM/Sprint config records |
| 3 - Territory Setup | 2-5 minutes | Interactive name confirmation + deploy + activation (or reuse) |
| 4 - Participant Role & Sprint | 1-2 minutes | 2 record creates + confirmation |
| 5 - Data & Plan Templates | 6-12 minutes | Part A: 8 object creates from CSVs (admin); Part B: goals, template, items, publish, assignment |
| 6 - User Provisioning | 3-6 minutes | User + permsets + territory + async metadata cache |
| **Total** | **19-43 minutes** | Depends on user interaction speed |
