# Stage 2 — Starter Config Deploy

Deploys the full Life Sciences Cloud Starter Configuration to a target org in a sequenced, recoverable workflow with interactive component selection. This is Stage 2 of the `life-sciences-fieldsalesrep-coordinate` workflow; the coordinator invokes it after prerequisites (Stage 1) pass.

## Stage Scope

- **In scope**: Deploying all starter config components (StandardValueSets, objects, productSpecificationTypes, productSpecificationRecTypes, quickActions, profiles, LifeSciConfigRecords, LifeSciMetadataRecords, trigger handlers, page layouts, flexipages, application file updates)
- **Out of scope**: Territory setup (Stage 3), user assignment (Stage 4), prerequisite validation (Stage 1), package installation

---

## Required Inputs

Gather before proceeding:

- **Target org**: The org alias or username to deploy to (from `sf config get target-org` or user-specified)

---

## Source Components (must be present in the CWD)

All components and data deployed in this stage come from the `.lsc-starter-config/LSStarterConfig/` subtree of the public repo <https://github.com/SalesforceLabs/LSStarterConfig.git>. **This stage does NOT download or delete that folder** — it expects `.lsc-starter-config/LSStarterConfig/` to already be present in the current working directory. The coordinator (`life-sciences-fieldsalesrep-coordinate`) downloads it once at the start of the run and deletes it once at the end. This stage uses these subfolders:

| Subfolder | Used by |
|---|---|
| `.lsc-starter-config/LSStarterConfig/PackageComponents/` | Steps 1–6, 9–13 (metadata: standardValueSets, objects, product specs, quick actions, profiles, layouts, flexipages, application) |
| `.lsc-starter-config/LSStarterConfig/LSConfig/lifeSciConfigRecord/` | Step 7 (LifeSciConfigCategories + LifeSciConfigRecords) |
| `.lsc-starter-config/LSStarterConfig/LSConfig/lifeSciMetadataRecord/` | Step 8 (LifeSciMetadataRecords via plan file) |

The deploy paths below (`.lsc-starter-config/LSStarterConfig/...`) resolve relative to the CWD. **`.lsc-starter-config/LSStarterConfig/` contains its own `sfdx-project.json`** (it pins `sourceApiVersion: 65.0`) — that is the project root all deploy steps must run from (see the working-directory note in Phase 1).

> **If `.lsc-starter-config/LSStarterConfig/` is not present, stop — do NOT download it here.** This embedded stage is a pure consumer of the shared folder; the coordinator (`life-sciences-fieldsalesrep-coordinate`) is the sole owner of the single download (at the start of the run) and the single delete (at the end). Report that the shared config folder is missing and must be provisioned by the coordinator before this stage runs, then halt.

---

## Deployment Order (MANDATORY — do not reorder)

**This order is required. Each step depends on artifacts created by earlier steps — running out of order causes deploy failures that are hard to diagnose.** Always execute steps 1 → 13 in sequence. Do not skip a dependency step, and do not run a later step until the step it depends on has verified success.

The critical dependency chain (proven in practice):

```text
Objects + RecordTypes (Step 2)
        └── LSC Custom Profile (Step 6)        # profile references RecordTypes; fails if objects not deployed first
                └── LifeSciConfigRecords (Step 7)  # 177 of 301 records assign config to the profile; fail if profile absent
```

| Order | Step | Depends on | Verification gate before proceeding |
|-------|------|-----------|--------------------------------------|
| 1 | StandardValueSets | — | Deploy succeeded |
| 2 | Objects (incl. RecordTypes) | — | Deploy succeeded; RecordTypes queryable |
| 3 | ProductSpecificationTypes | Objects | Deploy succeeded |
| 4 | ProductSpecificationRecTypes | ProductSpecificationTypes | Deploy succeeded |
| 5 | QuickActions | Objects | Deploy succeeded |
| 6 | LSC Custom Profile (skeleton) | Objects/RecordTypes | **Query the org to confirm the profile exists** |
| 7 | LifeSciConfigRecords | **Profile (Step 6)** | **Profile confirmed present before running** |
| 8 | LifeSciMetadataRecords | LifeSciConfigRecords | Categories → Records → FieldValues in order |
| 9 | TriggerHandlers | Objects | Handlers exist |
| 10 | PageLayouts | Objects | Deploy succeeded |
| 11 | ProfileLayoutAssignments | PageLayouts + Profile | Only assign deployed layouts |
| 12 | FlexiPages | Objects | Deploy succeeded |
| 13 | ApplicationUpdate | FlexiPages | Only reference deployed flexipages |

> **Why the skeleton profile first (Step 6), not the full profile:** the full `LSC Custom Profile` references RecordTypes and layouts. Deploying it standalone before objects fails with `no RecordType named Account.Business found`. The skeleton profile has no layout assignments, so it deploys cleanly after objects (Step 2); layout assignments are added later in Step 11. Deploying the config records (Step 7) before the profile exists fails every profile-assigned record with `Enter an assignment level and an assignment ID.`

---

## State Tracking

Maintain a deployment state object throughout the workflow to enable pause/resume and partial-deploy recovery. Read `references/stage-2-starter-config-state-tracking.md` for the full state-object schema, the failure/recovery prompt, and the progress-display formats. On failure at any step, present the recovery options from that reference and wait for the user's choice before continuing.

---

## Workflow

### Phase 1 — Deploy Foundation Components (Steps 1–6)

Read `references/stage-2-starter-config-deploy-commands.md` for exact CLI commands for each step.

> **Working directory (required for ALL deploy steps 1–13):** Run every `sf project deploy start` command from **inside the `.lsc-starter-config/LSStarterConfig/` project root** (the directory holding `sfdx-project.json`). `sf` only searches the current directory and its ancestors for `sfdx-project.json`, which pins `sourceApiVersion: 65.0`. Run from anywhere else and `sf` silently falls back to API 60.0, and the profile deploys (Steps 6 and 11) fail with `Property 'viewAllFields' not valid in version 60.0`. `cd .lsc-starter-config/LSStarterConfig` first; the `.lsc-starter-config/LSStarterConfig/...` paths in the commands below are shown from the CWD for readability — once you are inside `.lsc-starter-config/LSStarterConfig`, drop that prefix from `--source-dir` (e.g. `--source-dir PackageComponents/objects`).

**Step 1: Deploy StandardValueSets**
```bash
sf project deploy start --source-dir .lsc-starter-config/LSStarterConfig/PackageComponents/standardValueSets --target-org <org>
```

**Step 2: Deploy Objects**
```bash
sf project deploy start --source-dir .lsc-starter-config/LSStarterConfig/PackageComponents/objects --target-org <org>
```

**Step 3: Deploy Product Specification Types**
```bash
sf project deploy start --source-dir .lsc-starter-config/LSStarterConfig/PackageComponents/productSpecificationTypes --target-org <org>
```

**Step 4: Deploy Product Specification Record Types**
```bash
sf project deploy start --source-dir .lsc-starter-config/LSStarterConfig/PackageComponents/productSpecificationRecTypes --target-org <org>
```

**Step 5: Deploy Quick Actions**
```bash
sf project deploy start --source-dir .lsc-starter-config/LSStarterConfig/PackageComponents/quickActions --target-org <org>
```

**Step 6: Deploy LSC Custom Profile (Skeleton)**
```bash
sf project deploy start --source-dir .lsc-starter-config/LSStarterConfig/PackageComponents/profiles/SkeletonProfile --target-org <org>
```

> Deploy the **skeleton** profiles (`profiles/SkeletonProfile/`), not the full `profiles/*.profile-meta.xml`. The full profile carries layout assignments that don't exist yet and will fail. Do NOT deploy the profile before Step 2 (Objects) — it references RecordTypes and will fail with `no RecordType named Account.Business found`.

**Verification gate (required before Step 7):** confirm the profile landed in the org:
```bash
sf data query --query "SELECT Id, Name FROM Profile WHERE Name = 'LSC Custom Profile'" --target-org <org> --json
```
The query must return exactly one record. If it returns zero, do NOT proceed to Step 7 — the config records will fail. Re-run Step 6 (and confirm Step 2 succeeded) first.

After each step, verify deployment success. If a step fails, pause and present recovery options.

### Phase 2 — Deploy Config Records (Steps 7–8)

**Step 7: Deploy LifeSciConfigCategories and LifeSciConfigRecords**

> **Prerequisite gate:** the `LSC Custom Profile` MUST exist in the org (verified at end of Step 6). About 177 of the ~301 config records assign config to `Custom-LSC Custom Profile`; if the profile is absent every one of those fails with `Enter an assignment level and an assignment ID.` while the ~124 org-level records still succeed — a confusing partial deploy. Deployment is an upsert, so re-running after the profile exists is safe.

```bash
sf project deploy start -d .lsc-starter-config/LSStarterConfig/LSConfig/lifeSciConfigRecord --target-org <org>
```

> **STOP-GATE (deploy result).** `sf project deploy start` reports per-component pass/fail. Confirm **zero component failures** in the deploy result — do NOT eyeball "mostly succeeded." If any components failed with `Enter an assignment level and an assignment ID.`, the `LSC Custom Profile` was absent when the ~177 profile-scoped records deployed (the confusing partial deploy this Step warns about). Fix the profile (Step 6), then re-run this Step (upsert-safe) until the deploy reports **0 failures**. A partial config deploy leaves the org subtly misconfigured.

**Step 8: Deploy LifeSciMetadataRecords**

Deploy the JSON data files via the Composite Tree API using the **plan file** (the files use cross-file `@references` that only resolve through the plan). Run from inside the metadata-record directory:
```bash
cd .lsc-starter-config/LSStarterConfig/LSConfig/lifeSciMetadataRecord
sf data import tree --plan LifeSciMetadataCategory-plan.json --target-org <org> --json
```
The plan sequences LifeSciMetadataCategory → LifeSciMetadataRecord → LifeSciMetadataFieldValue with refs resolved. Do NOT import the files individually with `--files` — the references won't resolve. Expected: 101 records (10 + 10 + 81). Read `references/stage-2-starter-config-lifesci-metadata-deploy.md` for details.

> **STOP-GATE (import count).** `sf data import tree` returns one result row per created record. Count them — the total MUST be **101** (10 LifeSciMetadataCategory + 10 LifeSciMetadataRecord + 81 LifeSciMetadataFieldValue). If fewer, a `@reference` failed to resolve (usually because the import ran outside the metadata-record directory, or a category/record row failed and orphaned its children). Do NOT proceed to Phase 3 with a short count — re-run the plan from inside `.lsc-starter-config/LSStarterConfig/LSConfig/lifeSciMetadataRecord` until the import reports 101 created.

### Phase 3 — Activate Trigger Handlers (Step 9)

**Step 9: Activate Trigger Handlers**

Handlers are `LifeScienceTriggerHandler` records — a **Tooling API** entity (not a managed custom object). Read `references/stage-2-starter-config-trigger-handlers.md` for the full list of 28 handler `DeveloperName`s and the **safe batch-activation loop** — use one of the safe-loop patterns there (`jq` over the JSON, or an **unquoted** `for id in $IDS`); do NOT hand-roll a `while read` over an echoed ID list. The per-record update is:
```bash
sf data update record --sobject LifeScienceTriggerHandler --record-id <Id> --values "IsActive=true" --target-org <org> --use-tooling-api
```

Do NOT use `lsc4ce__TriggerHandler__c` — that sobject does not exist. All queries/updates require `--use-tooling-api`. Activating all 28 with sequential per-handler `sf` calls can exceed 2 minutes; query all inactive IDs at once and skip handlers already `IsActive=true`.

> **STOP-GATE (activation count).** After the loop, re-query and count active handlers **scoped to the 28** (a bare `WHERE IsActive = true` counts every active handler in the org, not just these):
> ```bash
> sf data query --query "SELECT COUNT(Id) active FROM LifeScienceTriggerHandler WHERE IsActive = true AND DeveloperName IN (<the 28 names>)" --target-org <org> --use-tooling-api --json
> ```
> The `active` count MUST equal the full handler count (28). If it is fewer, the activation is INCOMPLETE — the most common cause is a `while read`/newline-split loop dropping the final record when the ID list has no trailing newline (the "27 of 28" bug). Identify the straggler(s) by name (query the same 28 with `IsActive = false`), activate each missing one individually, and re-run this count until it equals 28. Do NOT proceed to Phase 4 while any handler is inactive — a missing handler silently breaks the automation it backs.

### Phase 4 — Interactive Layout Deployment (Step 10–11)

**Step 10: Deploy Page Layouts**

> **Interaction gate (required):** Do NOT deploy layouts until the user has selected which ones. Never default to "all" without an explicit user choice — present the list and wait for a response before proceeding.

1. List all available layouts from `.lsc-starter-config/LSStarterConfig/PackageComponents/layouts/`:

```markdown
Available Page Layouts:
 1. Account - HCO Account Layout
 2. ActivityPlanTerritory - Activity Plan Territory Layout
 3. Case - LSC Case Layout
 4. CommSubscription - Communication Subscription Layout
 5. CommSubscriptionChannelType - Communication Subscription Channel Type Layout
 6. CommSubscriptionConsent - Communication Subscription Consent Layout
 7. HealthcareProvider - Healthcare Provider Layout
 8. Inquiry - LSC Inquiry Layout
 9. InquiryQuestion - LSC Inquiry Question Layout
10. InquiryQuestionAnswer - LSC Inquiry Question Answer Layout
11. PersonAccount - Person Account HCP Layout
12. ProviderVisit - LSC Provider Visit Layout
13. ProviderVisitProdDiscussion - Product Feedback
14. Visit - LSC Visit Layout
```

2. Ask the user which layouts to deploy (accept numbers, ranges, or "all"). Present the list **neutrally** — do NOT recommend, rank, or single out layouts as "most relevant for field sales rep" (or for any persona). The selection is entirely the user's. Just list the layouts and the reply format, then wait.
3. Deploy only the selected layouts by copying them to a temporary directory and deploying:
```bash
sf project deploy start --source-dir <temp-dir-with-selected-layouts> --target-org <org>
```

**Step 11: Update Profile Layout Assignments**

After layouts are deployed, update the layout assignments in both profile files under `.lsc-starter-config/LSStarterConfig/PackageComponents/profiles/SkeletonProfile/`:
- `LSC Custom Profile.profile-meta.xml`
- `Admin.profile-meta.xml`

Add `<layoutAssignments>` entries for each deployed layout. Read `references/stage-2-starter-config-profile-layout-assignments.md` for the mapping of layouts to objects/record types.

> **No confirmation for this edit.** Updating the profile files is a mechanical consequence of the layout selection already made in Step 10 — the user has already chosen the layouts, and these `<layoutAssignments>` entries are the required mapping for that choice. Do NOT print the assignment block for review, and do NOT ask the user to confirm editing the profiles. Insert the entries directly (before `</Profile>` in each file) and proceed to deploy. The only interaction gate in this Step is the layout selection in Step 10; there is no separate approval for writing the profiles. `references/stage-2-starter-config-profile-layout-assignments.md` lists the full set of `<layoutAssignments>` blocks (one per layout + record-type combination). Before deploying, confirm **every** mapping for the layouts you deployed is present in BOTH profile files (`LSC Custom Profile.profile-meta.xml` and `Admin.profile-meta.xml`) — count the `<layoutAssignments>` blocks in each file against the reference. A missing assignment does not fail the deploy; it silently leaves that object rendering the wrong (or default) layout for the profile. Do NOT deploy a profile with fewer assignment blocks than the reference specifies for the deployed layout set.

Deploy the updated profiles:
```bash
sf project deploy start --source-dir .lsc-starter-config/LSStarterConfig/PackageComponents/profiles/SkeletonProfile --target-org <org>
```

### Phase 5 — Interactive FlexiPage Deployment (Steps 12–13)

**Step 12: Deploy FlexiPages**

> **Interaction gate (required):** Do NOT deploy flexipages until the user has selected which ones. Never default to "all" without an explicit user choice — present the list and wait for a response before proceeding.

1. List all available flexipages from `.lsc-starter-config/LSStarterConfig/PackageComponents/flexipages/`:

```markdown
Available FlexiPages:
1. Account_Plan3
2. Account_Plan_Objective_Record_Page3
3. CPVisitLandingPage
4. Contact_Point_Address_Record_Page
5. Goal_Definition1
6. Home_Page_LSC_Default
7. LSCAccountHCP
8. LSC_Inquiry
```

2. Ask the user which flexipages to deploy (accept numbers, ranges, or "all"). Present the list **neutrally** — do NOT recommend, rank, or single out pages as "most relevant for field sales rep" (or for any persona). The selection is entirely the user's; suggesting a subset biases the choice and misrepresents which pages a workflow needs. Just list the pages and the reply format, then wait.
3. Deploy only the selected flexipages:
```bash
sf project deploy start --source-dir <temp-dir-with-selected-flexipages> --target-org <org>
```

**Step 13: Update and Deploy Application File**

After flexipages are deployed, update `.lsc-starter-config/LSStarterConfig/PackageComponents/applications/lsc4ce__lifeSciencesCommercial.app-meta.xml`:

1. Keep only `<actionOverrides>` whose `<content>` matches a selected flexipage (or its `lsc4ce__` prefixed equivalent).
2. Keep only `<profileActionOverrides>` for **LSC Custom Profile** and **Admin** profiles whose `<content>` matches a selected flexipage.
3. Read `references/stage-2-starter-config-application-flexipage-mapping.md` for the full content-to-flexipage mapping.

Deploy the updated application file:
```bash
sf project deploy start --source-dir .lsc-starter-config/LSStarterConfig/PackageComponents/applications --target-org <org>
```

> **Do not delete the `.lsc-starter-config/LSStarterConfig/` folder** — this stage neither downloads nor removes it. The coordinator (`life-sciences-fieldsalesrep-coordinate`) owns the single download (at start) and single delete (at end) of the shared folder.

---

## Progress Display

After each step completes, display step progress; at the end show a final summary. See `references/stage-2-starter-config-state-tracking.md` for the exact progress and summary formats.

---

## Rules / Constraints

| Constraint | Rationale |
|-----------|-----------|
| Require `.lsc-starter-config/LSStarterConfig/` to already be present in the CWD; do NOT download or delete it | All components/data come from the repo, but the shared folder's download/cleanup is owned by `life-sciences-fieldsalesrep-coordinate` (one download at start, one delete at end) |
| Run deploys from inside `.lsc-starter-config/LSStarterConfig/` (the `sfdx-project.json` root, API 65.0) | `sf` finds the project file only in the CWD/ancestors; running elsewhere falls back to API 60.0 and profile deploys fail |
| Deploy strictly in order 1→13; never reorder or skip a dependency step | Later steps consume artifacts from earlier ones. Key chain: Objects (2) → Profile (6) → Config Records (7). See "Deployment Order (MANDATORY)". |
| Confirm the profile exists (query the org) before deploying config records (Step 7) | 177 config records assign to the profile and fail silently-per-record if it is absent |
| Always ask before deploying layouts and flexipages | User may not need all components |
| Show progress after each step | Long workflow needs visibility |
| Pause on failure with recovery options | Partial deployments should be recoverable |
| Update application file only for selected flexipages | Avoid deploying references to undeployed pages |
| Update profile layout assignments only for deployed layouts | Profile must reference only existing layouts |
| Use --target-org for every CLI command | Explicit org targeting avoids accidental deployments |

---

## Gotchas

| Issue | Resolution |
|-------|------------|
| LifeSciConfigRecord deploy fails with `Enter an assignment level and an assignment ID.` (often ~177 records) | The `LSC Custom Profile` is not in the org. Ensure Step 6 succeeded and the verification query returns 1 record, then re-run Step 7 (upsert-safe) |
| Standalone profile deploy fails with `no RecordType named Account.Business found` | The profile references RecordTypes. Deploy Objects (Step 2) first; use the skeleton profile at Step 6 |
| Profile deploy fails with `Property 'viewAllFields' not valid in version 60.0` | The command was run outside the `.lsc-starter-config/LSStarterConfig/` root, so `sf` didn't find `sfdx-project.json` and fell back to API 60.0. `cd .lsc-starter-config/LSStarterConfig` and re-run — the project pins API 65.0 (required for LSC profile permissions) |
| `sObject type 'lsc4ce__TriggerHandler__c' is not supported` | Handlers are the Tooling entity `LifeScienceTriggerHandler` (fields `DeveloperName`/`IsActive`); query and update with `--use-tooling-api` |
| Metadata records fail with reference-resolution error | Use the `--plan LifeSciMetadataCategory-plan.json` import, not per-file `--files`; the plan resolves cross-file `@references` |
| Application deploy fails with "flexipage not found" | Ensure selected flexipages were deployed in Step 12 before Step 13 |
| Layout deploy fails with "object/field not found" | Ensure Step 2 (objects) completed successfully |
| LifeSciMetadataRecord deploy order matters | Categories must be deployed before Records, Records before FieldValues |
| JSON data deploy uses Composite Tree API, not metadata deploy | Use `sf data import tree` for JSON files, not `sf project deploy start` |

---

## Output Expectations

Deliverables:
- All foundation metadata deployed (StandardValueSets, objects, product specs, quick actions, profile)
- LifeSciConfigRecords and LifeSciMetadataRecords deployed
- Trigger handlers activated
- User-selected page layouts deployed with profile assignments updated
- User-selected flexipages deployed with application file updated
- Progress summary showing all steps completed

---

## Reference File Index

| File | When to read |
|------|-------------|
| `references/stage-2-starter-config-state-tracking.md` | Throughout — deployment state schema, failure/recovery prompt, and progress-display formats |
| `references/stage-2-starter-config-deploy-commands.md` | During Phase 1 — exact CLI commands and expected outputs |
| `references/stage-2-starter-config-lifesci-metadata-deploy.md` | During Phase 2 — JSON deploy sequence and commands |
| `references/stage-2-starter-config-trigger-handlers.md` | During Phase 3 — handler names and activation method |
| `references/stage-2-starter-config-profile-layout-assignments.md` | During Phase 4 — layout-to-object/recordType mapping for profile updates |
| `references/stage-2-starter-config-application-flexipage-mapping.md` | During Phase 5 — flexipage content mapping for actionOverrides |
