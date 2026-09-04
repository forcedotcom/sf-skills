# Stage 2 — Starter Config Deploy (KAM)

Deploys the Life Sciences Cloud Starter Configuration to a target org in a sequenced, recoverable workflow with interactive component selection, then writes the KAM- and Sprint-specific picklist values into the org-level config records. This is Stage 2 of the `life-sciences-kam-coordinate` workflow; the coordinator invokes it after prerequisites (Stage 1) pass.

## Stage Scope

- **In scope**: Deploying all starter config components (StandardValueSets, objects, productSpecificationTypes, productSpecificationRecTypes, quickActions, profiles, LifeSciConfigRecords, LifeSciMetadataRecords, trigger handlers, page layouts, flexipages, application file updates) plus the KAM/Sprint config-record picklist edits
- **Out of scope**: Territory setup (Stage 3), participant role/sprint records (Stage 4), data & plan templates (Stage 5), user provisioning (Stage 6), prerequisite validation (Stage 1), package installation

---

## Required Inputs

- **Target org**: The org alias or username to deploy to (from `sf config get target-org` or user-specified)

---

## Source Components (must be present in the CWD)

All components and data deployed in this stage come from the `.lsc-starter-config/LSStarterConfig/` subtree of <https://github.com/SalesforceLabs/LSStarterConfig.git>. **This stage does NOT download or delete that folder** — it expects `.lsc-starter-config/LSStarterConfig/` to already be present in the CWD. The coordinator (`life-sciences-kam-coordinate`) downloads it once at the start of the run and deletes it once at the end.

| Subfolder | Used by |
|---|---|
| `.lsc-starter-config/LSStarterConfig/PackageComponents/` | Steps 1–6, 9–13 (standardValueSets, objects, product specs, quick actions, profiles, layouts, flexipages, application) |
| `.lsc-starter-config/LSStarterConfig/LSConfig/lifeSciConfigRecord/` | Step 7 (LifeSciConfigCategories + LifeSciConfigRecords) |
| `.lsc-starter-config/LSStarterConfig/LSConfig/lifeSciMetadataRecord/` | Step 8 (LifeSciMetadataRecords via plan file) |

**`.lsc-starter-config/LSStarterConfig/` contains its own `sfdx-project.json`** (pins `sourceApiVersion: 65.0`) — that is the project root all deploy steps must run from (see the working-directory note in Phase 1).

> **If `.lsc-starter-config/LSStarterConfig/` is not present, stop — do NOT download it here.** This embedded stage is a pure consumer of the shared folder; the coordinator is the sole owner of the single download (start) and single delete (end). Report that the shared config folder is missing and must be provisioned by the coordinator, then halt.

---

## Deployment Order (MANDATORY — do not reorder)

Each step depends on artifacts created by earlier steps. Always execute 1 → 13 in sequence, then run the KAM/Sprint config-record edits (Step 14). Do not skip a dependency step, and do not run a later step until the step it depends on has verified success.

The critical dependency chain:

```text
Objects + RecordTypes (Step 2)
        └── LSC Custom Profile (Step 6)        # profile references RecordTypes; fails if objects not deployed first
                └── LifeSciConfigRecords (Step 7)  # 177 records assign config to the profile; fail if profile absent
                        └── KAM/Sprint config-record edits (Step 14)  # update lifeSciConfigRecord picklist values
```

| Order | Step | Depends on | Verification gate before proceeding |
|-------|------|-----------|--------------------------------------|
| 1 | StandardValueSets | — | **Values confirmed with admin (3 grouped confirmations) BEFORE deploy**, then deploy succeeded |
| 2 | Objects (incl. RecordTypes) | — | Deploy succeeded; RecordTypes queryable |
| 3 | ProductSpecificationTypes | Objects | Deploy succeeded |
| 4 | ProductSpecificationRecTypes | ProductSpecificationTypes | Deploy succeeded |
| 5 | QuickActions | Objects | Deploy succeeded |
| 6 | LSC Custom Profile (skeleton) | Objects/RecordTypes | **Query the org to confirm the profile exists** |
| 7 | LifeSciConfigRecords | **Profile (Step 6)** | **Profile confirmed present before running** |
| 8 | LifeSciMetadataRecords | LifeSciConfigRecords | Categories → Records → FieldValues in order |
| 9 | TriggerHandlers | Objects | Handlers exist |
| 10 | PageLayouts (KAM: 4) | Objects | Deploy succeeded |
| 11 | ProfileLayoutAssignments | PageLayouts + Profile | Only assign deployed layouts |
| 12 | FlexiPages (KAM: 6) | Objects | Deploy succeeded |
| 13 | ApplicationUpdate | FlexiPages | Only reference deployed flexipages |
| 14 | KAM/Sprint config-record edits | LifeSciConfigRecords (Step 7) | Both config records updated & re-deployed |

> **Why the skeleton profile first (Step 6):** the full `LSC Custom Profile` references RecordTypes and layouts and fails to deploy standalone. The skeleton has no layout assignments; assignments are added in Step 11. Deploying config records (Step 7) before the profile exists fails every profile-assigned record with `Enter an assignment level and an assignment ID.`

---

## State Tracking

Maintain a deployment state object throughout to enable pause/resume and partial-deploy recovery. Read `references/stage-2-starter-config-state-tracking.md` for the full state-object schema, the failure/recovery prompt, and the progress-display formats. On failure at any step, present the recovery options and wait for the user's choice before continuing.

---

## Workflow

### Phase 1 — Deploy Foundation Components (Steps 1–6)

Read `references/stage-2-starter-config-deploy-commands.md` for exact CLI commands for each step.

> **Working directory (required for ALL deploy steps 1–13):** Run every `sf project deploy start` from **inside `.lsc-starter-config/LSStarterConfig/`** (the directory holding `sfdx-project.json`). `sf` only searches the CWD/ancestors for `sfdx-project.json`, which pins `sourceApiVersion: 65.0`. Run elsewhere and `sf` silently falls back to API 60.0, and the profile deploys (Steps 6, 11) fail with `Property 'viewAllFields' not valid in version 60.0`. `cd .lsc-starter-config/LSStarterConfig` first; once inside, drop that prefix from `--source-dir`.

**Step 1: Confirm the picklist values with the admin, THEN deploy StandardValueSets.** Confirmation happens *before* the deploy: the admin approves (or edits) the values first, then the confirmed values are written into the `*.standardValueSet-meta.xml` files and deployed. Step 1 is the single source of truth for both the org's picklists and the Step 14 config-record edits, so it must run up front.

Present the values in **three business-framed confirmations** — grouped by the objects the admin recognizes, not one-by-one by metadata API name. For each group, fetch the current values (from the StandardValueSet files, or query the org) and show them alongside the setup-guide example defaults; the admin either accepts the defaults or edits any of them.

**Confirmation A — Account Plan Stakeholder fields.** Three fields on the Account Plan Stakeholder object:

| Field (admin-facing) | StandardValueSet | Setup-guide example values |
|---|---|---|
| Role Type | `StakeholderRoleType` | Internal / External |
| Influencer Level | `StakeholderInfluenceLevel` | District / National / International |
| Strength | `StakeholderStrength` | Low / Medium / High |

Example prompt: *"On the Account Plan Stakeholder object I'll set Role Type, Influencer Level, and Strength. The setup guide suggests Internal/External · District/National/International · Low/Medium/High. Use those, or define your own?"*

**Confirmation B — Plan status values.** The status values the plans use:

| Field (admin-facing) | StandardValueSet | Setup-guide example values |
|---|---|---|
| Territory Business Plan status | `TerritoryBusinessPlanStatus` | Not Started / In Progress / Completed / Deferred |
| Account Plan status | `AccountPlanStatus` | Not Started / In Progress / Completed / Deferred |
| Account Plan Objective status | `AccPlanObjectiveStatus` | Not Started / In Progress / Completed / Deferred |
| Sprint status | `SprintStatus` | Not Started / In Progress / Completed / Deferred |

Example prompt: *"Next, the status values for Territory Business Plan, Account Plan, Account Plan Objective, and Sprint — Not Started / In Progress / Completed / Deferred. Use those, or define your own?"*

**Confirmation C — Assessment Task category.** Shown separately, after the status values:

| Field (admin-facing) | StandardValueSet | Setup-guide example values |
|---|---|---|
| Assessment Task category | `AssessmentTaskCategory` | Approve / Survey / Claim |

Example prompt: *"Finally, the Assessment Task categories — Approve / Survey / Claim. Use those, or define your own?"*

> **The remaining two StandardValueSets — `ActionPlanState` and `GoalAssignmentStatus` — deploy with their shipped defaults; do NOT prompt the admin for them.** They are internal plumbing consumed only by the Step 14 config records (`NotStartedStatusValueForAP` / `CompletionStatusValueForAP` ← `ActionPlanState`; `CompletionStatusValueForGA` ← `GoalAssignmentStatus`), not object-level picklists the admin manages. Their shipped defaults already include the "Not Started" / "Completed" members Step 14 needs.

After all three confirmations, write any edited values into the corresponding `*.standardValueSet-meta.xml` files, then deploy the StandardValueSets directory (command in `references/stage-2-starter-config-deploy-commands.md`). The confirmed values from Confirmations A, B, and C feed the Step 14 config-record edits.

> **Keep Step 14 defaults valid:** the Step 14 config records default to `Completed` / `Not Started` members. If the admin edits a status set to remove either member, carry the admin's replacement through to Step 14 so the config-record values stay members of the deployed set.

Steps 2–9 are unchanged from the shared deploy sequence — see `references/stage-2-starter-config-deploy-commands.md`, `references/stage-2-starter-config-lifesci-metadata-deploy.md` (Step 8), and `references/stage-2-starter-config-trigger-handlers.md` (Step 9). The Step 6 profile-exists gate and the Step 7 / Step 8 / Step 9 STOP-GATEs (0 config failures; 101 imported records; all 28 handlers active) apply exactly as written there.

### Phase 4 — Layout Deployment (Steps 10–11) — KAM: 4 layouts (deployed automatically)

**Step 10: Deploy Page Layouts.** Deploy all four KAM layouts automatically — do **NOT** ask the admin which to deploy. These four are the complete KAM layout set, so there is nothing to choose among; a selection prompt only adds friction. The four deployed:

```markdown
Page Layouts deployed (KAM):
 1. Account - HCO Account Layout
 2. PersonAccount - Person Account HCP Layout
 3. HealthcareProvider - Healthcare Provider Layout
 4. ActionPlan - Action Plan Layout
```

Copy all four layouts to a temp directory and deploy.

**Step 11: Update Profile Layout Assignments.** Add `<layoutAssignments>` for each deployed layout to BOTH profile files under `.lsc-starter-config/LSStarterConfig/PackageComponents/profiles/SkeletonProfile/` (`LSC Custom Profile.profile-meta.xml`, `Admin.profile-meta.xml`). This is a mechanical consequence of the Step 10 selection — do NOT print the block for review or ask to confirm the profile edit. Mapping + full XML: `references/stage-2-starter-config-profile-layout-assignments.md`. Then re-deploy the profiles.

### Phase 5 — FlexiPage Deployment (Steps 12–13) — KAM: 6 flexipages (deployed automatically)

**Step 12: Deploy FlexiPages.** Deploy all six KAM flexipages automatically — do **NOT** ask the admin which to deploy. These six are the complete KAM flexipage set. The six deployed:

```markdown
FlexiPages deployed (KAM):
1. Home_Page_LSC_Default
2. LSCAccountHCP
3. Contact_Point_Address_Record_Page
4. Account_Plan_Objective_Record_Page3
5. Account_Plan3
6. Goal_Definition1
```

Deploy all six flexipages from a temp directory.

**Step 13: Update and Deploy Application File.** Keep only `<actionOverrides>`/`<profileActionOverrides>` matching the deployed flexipages. Mapping: `references/stage-2-starter-config-application-flexipage-mapping.md`. Deploy the updated application file.

### Phase 6 — KAM & Sprint Config Records (Step 14)

**Step 14: Update the KAM and Sprint org-level config records.** Using the values confirmed in Step 1, edit the picklist values in `KAMSettings_OrgLevel.lifeSciConfigRecord` and `SprintSettings_OrgLevel.lifeSciConfigRecord`, then re-deploy the config records. Full field-by-field mapping and deploy command: **`references/stage-2-starter-config-kam-config-records.md`**.

> **Do not delete the `.lsc-starter-config/LSStarterConfig/` folder** — this stage neither downloads nor removes it. The coordinator owns the single download (start) and single delete (end).

---

## Rules / Constraints

| Constraint | Rationale |
|-----------|-----------|
| Require `.lsc-starter-config/LSStarterConfig/` present in CWD; do NOT download or delete it | The shared folder's download/cleanup is owned by the coordinator (one download at start, one delete at end) |
| Run deploys from inside `.lsc-starter-config/LSStarterConfig/` (API 65.0) | Running elsewhere falls back to API 60.0 and profile deploys fail |
| Deploy strictly in order 1→14; never reorder or skip a dependency step | Later steps consume earlier artifacts. Key chain: Objects (2) → Profile (6) → Config Records (7) → KAM/Sprint edits (14) |
| Confirm the profile exists (query the org) before Step 7 | 177 config records assign to the profile and fail per-record if it is absent |
| Confirm the KAM StandardValueSet values with the admin BEFORE deploying them (Step 1), in three business-framed groups; `ActionPlanState`/`GoalAssignmentStatus` keep shipped defaults (no prompt) | The confirmed values seed both the org picklists and the Step 14 config-record edits, so they must be settled before deploy |
| Deploy the full KAM subset of layouts (4) and flexipages (6) automatically — do NOT prompt to select | These are the complete KAM sets; there is nothing to choose among, so a selection prompt only adds friction |
| Use --target-org for every CLI command | Explicit org targeting avoids accidental deployments |

---

## Gotchas

| Issue | Resolution |
|-------|------------|
| LifeSciConfigRecord deploy fails with `Enter an assignment level and an assignment ID.` | The `LSC Custom Profile` is not in the org. Ensure Step 6 succeeded (query returns 1), then re-run Step 7 (upsert-safe) |
| Standalone profile deploy fails with `no RecordType named Account.Business found` | Deploy Objects (Step 2) first; use the skeleton profile at Step 6 |
| Profile deploy fails with `Property 'viewAllFields' not valid in version 60.0` | Command was run outside `.lsc-starter-config/LSStarterConfig/`; `cd` in and re-run (project pins API 65.0) |
| `sObject type 'lsc4ce__TriggerHandler__c' is not supported` | Handlers are the Tooling entity `LifeScienceTriggerHandler`; query/update with `--use-tooling-api` |
| Metadata records fail with reference-resolution error | Use the `--plan LifeSciMetadataCategory-plan.json` import, not per-file `--files` |
| KAM/Sprint config edit not taking effect | Config records are upsert on deploy — confirm you edited the correct `attributes`/`picklistValues` and re-deployed the `lifeSciConfigRecord` directory (see the config-records reference) |

---

## Reference File Index

| File | When to read |
|------|-------------|
| `references/stage-2-starter-config-state-tracking.md` | Throughout — deployment state schema, failure/recovery prompt, progress formats |
| `references/stage-2-starter-config-deploy-commands.md` | Phase 1 — exact CLI commands and expected outputs |
| `references/stage-2-starter-config-lifesci-metadata-deploy.md` | Step 8 — JSON deploy sequence and commands |
| `references/stage-2-starter-config-trigger-handlers.md` | Step 9 — handler names and activation method |
| `references/stage-2-starter-config-profile-layout-assignments.md` | Step 11 — KAM 4-layout mapping for profile updates |
| `references/stage-2-starter-config-application-flexipage-mapping.md` | Step 13 — KAM 6-flexipage content mapping |
| `references/stage-2-starter-config-kam-config-records.md` | Step 14 — KAM/Sprint picklist config-record edits |
