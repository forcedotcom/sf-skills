---
name: life-sciences-kam-coordinate
description: "Use this skill to run the full end-to-end Life Sciences Cloud setup workflow for a key account management (KAM) user in sequence. Trigger when the user says 'set up Life Sciences Cloud end to end for kam user', 'run the full LSC setup for kam user', 'orchestrate Life Sciences Cloud configuration for kam user', 'complete LSC setup for kam user', or 'Life Sciences Cloud full install for kam user'. Executes six stages in order: prerequisites validation, starter config deployment, territory configuration, participant role and sprint creation, KAM data and plan-template (goals, tasks, measures) creation, and KAM user provisioning — gating each stage on the success of the previous one. DO NOT TRIGGER when: the user wants to run only one specific stage individually, or when the request targets a field sales rep rather than a KAM user (use life-sciences-fieldsalesrep-coordinate for that persona)."
metadata:
  version: "1.0"
  minApiVersion: "65.0"
  domains: ["Life Sciences"]
  relatedSkills:
    - life-sciences-fieldsalesrep-coordinate
    - life-sciences-prerequisites-validate
    - life-sciences-territory-configure
  cliTools:
    - tool: ["git"]
      semver: ">=2.25.0"
    - tool: ["jq"]
      semver: ">=1.6"
    - tool: ["sf"]
      semver: ">=2.0.0"
---

# Life Sciences Cloud KAM End-to-End Orchestrator

Runs the complete Life Sciences Cloud setup for a **key account management (KAM)** user as six **stages** in strict sequence, gating each on the previous stage's success. Each stage delegates to a child skill or reference workflow (see Execution Order).

## Scope Guard (evaluate FIRST)

Serve **only** requests for the full end-to-end LSC setup **for a KAM user**. A single stage/phase/step is **never** invokable here — never silently expand a partial ask into the whole flow. Before any work:

- **Field sales rep persona** (not KAM) → redirect to `life-sciences-fieldsalesrep-coordinate`; stop.
- **Unrelated** to LSC setup (at start or mid-run) → do not attempt it; say you did not understand and show what you can help with (full end-to-end LSC KAM setup, or standalone `life-sciences-prerequisites-validate` / `life-sciences-territory-configure`); stop.
- **Single stage with its own standalone skill** — prerequisites (1) or territory config (3) → redirect to that skill; stop.
- **Single stage with no standalone skill** — config deploy (2), participant role/sprint (4), data and plan templates (5), user provisioning (6) → explain these run only inside the full flow; stop. Do **not** launch the full flow unless the user then asks.

Continue only for the complete end-to-end KAM setup: the full flow in order with gates, each stage's work delegated to child skills / reference files.

---

## Required Inputs

- **Target org**: the org to deploy to — selected by the user from connected orgs or a freshly authenticated org (Phase 0). Never assume a default org silently; the user confirms or selects it before any stage runs.

---

## Execution Order (MANDATORY)

> **Terminology:** **Stage** = one of the 6 units of work, each delegated to a child skill/reference; **Phase** = a named group inside a stage; **Step** = an atomic action inside a phase.

Run in this order, each gated on the previous (dependency diagram in `references/orchestration-flow.md`):

| # | Stage | Runs | Gate (must pass to advance) | Output |
|---|-------|------|------------------------------|--------|
| — | **Setup**: download `.lsc-starter-config/LSStarterConfig` | — | Folder present (MANDATORY — hard stop) | Shared source folder in CWD |
| 1 | Prerequisites Validation | `life-sciences-prerequisites-validate` skill | All prerequisites PASS | Org confirmed ready |
| 2 | Starter Config Deploy | `references/stage-2-starter-config-overview.md` | 13 deploy steps + KAM config records succeed | LSC Custom Profile + KAM/Sprint settings |
| 3 | Territory Configuration | `life-sciences-territory-configure` skill | Territory model Active + L3 territory | Level-3 territory ID + name |
| 4 | Participant Role & Sprint | `references/stage-4-participant-role-and-sprint.md` | Participant role + sprint created | Role + Sprint IDs |
| 5 | KAM Data & Plan Templates | `references/stage-5-data-and-plan-templates-overview.md` | Account/HCP/product/territory data created + goals, template (Final), items, assignment created + goals/template/PATI shared to the leaf territory | Account + product master data + published ActionPlanTemplate |
| 6 | KAM User Provisioning | `references/stage-6-user-provisioning-overview.md` | User created, permsets + territory assigned; metadata cache generated | KAM username |

---

## Workflow

### Phase 0 — Org Selection (MANDATORY, runs first)

Establish which org to use **every time** — never silently reuse the default org.

1. **List connected orgs** with `sf org list --json`, then present the authenticated (non-expired) orgs as a numbered list (alias, username, org type, default marker), plus an option **N** to log in to a fresh org.
2. **Ask the user to choose** a number or **N**.
3. **Handle the selection**:
   - **Existing org** → capture its username/alias as the target org.
   - **Fresh org (N)** → ask for the login URL (`https://login.salesforce.com`, `https://test.salesforce.com`, or a My Domain URL) and an alias, then **run the login command yourself**: `sf org login web --instance-url <url> --alias <alias> --set-default`. Do not hand the command to the user to run — execute it directly. It opens a browser on the user's machine for them to complete the login interactively; the command then returns. After it finishes, re-run `sf org list --json` to confirm.
4. **Confirm the target org** back to the user and store it in `OrchestrationState.targetOrg`.

> If `sf org list` returns no authenticated orgs, go straight to the fresh-org login (option N).

### Phase 1 — Introduction and Confirmation

1. **Present the workflow** to the user — a "Life Sciences Cloud — Full KAM Setup Workflow" header, the target org, and the 6 stages in order with a one-line summary each: (1) Validate Prerequisites; (2) Deploy Starter Configuration (objects, profiles, config records incl. KAM & Sprint settings, layouts, flexipages); (3) Configure Territories; (4) Create Participant Role & Sprint; (5) Create KAM Data & Plan Templates (account, provider, product, territory data + goals, tasks, measures, published action plan template); (6) Provision KAM User (profile/permsets/territory + mobile metadata cache).

2. **Ask for confirmation**: "Ready to begin the full LSC KAM setup? (yes/no)"

3. **Download the shared source folder FRESH (MANDATORY — hard gate, before any stage).** Stages 2 (metadata + config records) and 5 (Data CSVs) read from `.lsc-starter-config/LSStarterConfig/`; those stages do NOT download or delete it — the orchestrator owns one fresh download here and one delete in Phase 9. **Always re-pull — never reuse an existing folder** (a stale copy would skip newly added components). Delete any pre-existing `.lsc-starter-config` first, then sparse-checkout the subtree fresh:

   ```bash
   rm -rf .lsc-starter-config lsstarter-tmp
   git clone --no-checkout --depth 1 --filter=blob:none \
     https://github.com/SalesforceLabs/LSStarterConfig.git lsstarter-tmp
   cd lsstarter-tmp && git sparse-checkout init --cone \
     && git sparse-checkout set Codey/LSStarterConfig && git checkout && cd ..
   mv lsstarter-tmp/Codey ./.lsc-starter-config && rm -rf lsstarter-tmp
   ```

   > `.lsc-starter-config/LSStarterConfig/` has its own `sfdx-project.json` (pins `sourceApiVersion: 65.0`) — deploy steps must run from inside it.

4. **Download gate — verify before proceeding.** Confirm `.lsc-starter-config/LSStarterConfig/sfdx-project.json` and `.lsc-starter-config/LSStarterConfig/Data/` exist (e.g. `ls .lsc-starter-config/LSStarterConfig/sfdx-project.json .lsc-starter-config/LSStarterConfig/Data`).
   - If present → set `sourceFolderDownloaded: true` and proceed to Phase 2.
   - If missing/failed → **STOP. Do NOT proceed to any stage** — every stage depends on this folder. Report the failure (likely: no network / GitHub unreachable, git < 2.25, or disk/permission), leave `sourceFolderDownloaded: false`, and do not advance. Fix the cause and re-run, or download the folder manually into the CWD.

### Phase 2 — Execute Stage 1: Prerequisites Validation

5. **Run the prerequisites validation** following the `life-sciences-prerequisites-validate` skill workflow exactly.

6. **Gate check**: If ALL prerequisites pass → proceed to Stage 2. If ANY fails → **stop**, present the failure table, and ask: "Continue anyway (skip failed prerequisites), or stop and fix them first?" Stop → end the workflow. Continue → proceed with a warning that later stages may fail.

### Phase 3 — Execute Stage 2: Starter Config Deploy

7. **Run the starter config deployment** following `references/stage-2-starter-config-overview.md` exactly (all 13 deploy steps + the KAM/Sprint config-record edits); read its own reference files as directed. The KAM adaptation deploys only the KAM-relevant layouts (4) and flexipages (6) — all of them, automatically, with no selection prompt — and confirms the StandardValueSet picklist values with the admin (three business-framed groups) BEFORE deploying them, then writes those confirmed values into the `KAMSettings_OrgLevel` and `SprintSettings_OrgLevel` config records.

8. **Gate check**: Verify the LSC Custom Profile exists:
   ```bash
   sf data query --query "SELECT Id, Name FROM Profile WHERE Name = 'LSC Custom Profile'" --target-org <org> --json
   ```
   - If profile exists → proceed to Stage 3. If not found → **stop** and report deployment failure.

### Phase 4 — Execute Stage 3: Territory Configuration

9. **Run the territory configuration** following the `life-sciences-territory-configure` skill workflow exactly. If an active territory model already exists, use it and show the hierarchy rather than creating a new one.

10. **Gate check**: Verify the territory model is Active and a level-3 territory exists:
    ```bash
    sf data query --query "SELECT Id, Name, DeveloperName, Territory2Model.State FROM Territory2 WHERE ParentTerritory2.ParentTerritory2Id != null AND Territory2Model.State = 'Active'" --target-org <org> --json
    ```
    - If found → **capture the level-3 territory ID + name** (`OrchestrationState.territoryId`) and tell the user this leaf territory is the single territory reused for Stage 5 (ProductTerritoryAvailability) and Stage 6 (UserTerritory2Association for both admin and KAM user). Proceed to Stage 4.
    - If not found → **stop** and report the issue.

### Phase 5 — Execute Stage 4: Participant Role & Sprint

11. **Create the participant role and sprint** following `references/stage-4-participant-role-and-sprint.md` exactly. Only the `MasterLabel`/`Name` fields are confirmed with the admin; all other fields are auto-derived and shown for confirmation.

12. **Gate check**: Verify a `ParticipantRole` (`DeveloperName = 'Rep_Execution_Specialist'`, `IsActive = true`) and a `Sprint` (Status `Not Started`) exist. If either is missing → **stop** and report.

### Phase 6 — Execute Stage 5: KAM Data & Plan Templates

Both parts run as the admin, in order, from the single reference `references/stage-5-data-and-plan-templates-overview.md` (Part A = data, Part B = plan templates).

13. **Create the KAM data (Part A)** following the reference exactly. Pass the Stage-3 level-3 territory. Creates (from the Data CSVs): Account, HealthcareProvider, ObjectTerritory2Association, ProviderAcctTerritoryInfo, Product2, LifeSciMarketableProduct, ContactPointAddress, ProductTerritoryAvailability.

14. **Part A gate check**: Verify the Account, `LifeSciMarketableProduct`, and `ProductTerritoryAvailability` (on the Stage-3 territory) exist; capture the `LifeSciMarketableProduct` ID (Part B uses it). If any missing → **stop**.

15. **Create the goals, tasks, measures, and action plan template (Part B)** following the same reference exactly (stay on the admin login). Creates 2 `GoalDefinition` records, a `GoalDefinitionProduct`, an `ActionPlanTemplate` (+ auto `ActionPlanTemplateVersion`), 3 `ActionPlanTemplateItem` records, publishes the template (status → Final), creates an `ActionPlanTemplateAssignment`, and shares the 2 `GoalDefinition` records, the `ActionPlanTemplate`, and both `ProviderAcctTerritoryInfo` records to the Stage-3 leaf-territory **Group** (5 manual shares total) so the KAM user reaches them through the territory. Only the record **names** are confirmed with the admin.

16. **Part B gate check**: Verify the template is published (a `Final` `ActionPlanTemplateVersion` exists), an `ActionPlanTemplateAssignment` exists, and the leaf-territory shares exist (2 `GoalDefinitionShare` + 1 `ActionPlanTemplateShare` + 2 `ProviderAcctTerritoryInfoShare` whose `UserOrGroupId` is the Stage-3 territory Group). If not → **stop**.

### Phase 7 — Execute Stage 6: KAM User Provisioning

17. **Provision the KAM user** following `references/stage-6-user-provisioning-overview.md` exactly. Pass the Stage-3 level-3 territory. Creates a user whose username contains `kam`, assigns the permission sets **Health Cloud Starter**, **Life Sciences Key Account Management**, **Life Sciences Field Sales Representative**, and **Life Sciences Core**, assigns **both the admin and the KAM user** to the level-3 territory (confirm with admin — MUST be the same territory used for ProductTerritoryAvailability in Stage 5), and generates the mobile metadata cache via the Connect API.

18. **Gate check (STOP-GATE — Stage 6 completeness).** Do NOT accept "user created" as passing. Verify the user is `IsActive=true` on `LSC Custom Profile`, has a `UserTerritory2Association` to the Stage-3 territory, the metadata cache reached `Status='Active'`, and the assigned-permset count is **4** ({HealthCloudStarter, LifeSciencesKeyAccountManager, LifeSciencesFieldSalesRepresentative, LifeSciencesCore}):
    ```bash
    sf data query --query "SELECT COUNT(Id) c FROM PermissionSetAssignment WHERE AssigneeId = '<newUserId>' AND PermissionSet.IsOwnedByProfile = false" --target-org <org> --json
    ```
    If < 2, or the territory assignment or metadata cache is missing, re-run the missing part before finishing.

### Phase 8 — Final Summary, Cleanup & On-Device Validation

19. **Display the complete workflow summary** — a "Life Sciences Cloud KAM Setup Complete" header, then one block per stage with actual values: (1) prerequisites confirmed; (2) objects/profiles/config records deployed, KAM & Sprint settings written, layouts + flexipages, 28 trigger handlers; (3) Territory Model `<model>` (Active) + Level-3 `<territory>`; (4) Participant Role `Rep Execution Specialist` + Sprint `<name>`; (5) Account + HCP, product master data, ProductTerritoryAvailability on `<territory>`, 2 Goal Definitions, ActionPlanTemplate `<name>` (Final) + 3 items + assignment, goals + template + 2 PATI shared to territory `<territory>`; (6) User `<name>` (`<username>`) on `LSC Custom Profile`, permsets Health Cloud Starter + Life Sciences Key Account Management + Life Sciences Field Sales Representative + Life Sciences Core, Territory `<territory>` (admin + KAM), mobile metadata cache generated. Close: "The org is ready for Life Sciences Cloud key account management workflows."

20. **Cleanup — delete the shared source folder ONCE.** After the final summary (all 6 stages complete), run from the CWD:

    ```bash
    rm -rf .lsc-starter-config
    ```

    Do this **silently** — do NOT print a cleanup line or mention the deletion. **Skip if the workflow stopped on a failure and the user may resume** — keep the folder so a resumed stage can still read it. This is the single deletion for the whole flow; child skills never delete it.

21. **Display the on-device (iPad) validation script and await confirmation.** Once the metadata cache is `Status='Active'` and the summary is shown, display the script **verbatim** from `references/stage-6-ipad-validation-script.md` (the login uses the Stage-6 KAM user's credentials), then **wait for the user to confirm** the on-device steps succeeded. Once confirmed, the setup is complete.

---

## State Tracking

Maintain overall orchestration state:

```text
OrchestrationState = {
  targetOrg: string,
  sourceFolderDownloaded: boolean,   // downloaded in Phase 1, deleted in Phase 9
  territoryId?: string, territoryName?: string,   // captured in Stage 3, reused in Stages 5 & 6
  stages: [
    { name: "Prerequisites",       status: "pending|running|passed|failed|skipped" },
    { name: "StarterConfig",       status: "pending|running|passed|failed" },
    { name: "TerritorySetup",      status: "pending|running|passed|failed", territoryId?: string, territoryName?: string },
    { name: "ParticipantSprint",   status: "pending|running|passed|failed", roleId?: string, sprintId?: string },
    { name: "DataAndPlanTemplates",status: "pending|running|passed|failed", accountId?: string, marketableProductId?: string, templateVersionId?: string },
    { name: "UserProvisioning",    status: "pending|running|passed|failed", userId?: string, username?: string }
  ]
}
```

---

## Idempotent Stage Transitions & Mid-Flow Changes

Stages are **not re-entrant**. Before executing any stage, check its `status`: `running` → reply "Stage N is already in progress" and take no action; `passed` → ask explicit confirmation before re-running; `failed` → re-run (recovery); `pending` → advance. Set `running` at execution **start** (not on user input) so accidental double-confirms never run a stage twice.

If the user requests a change to an earlier stage's inputs **while a later stage is in progress/pending**, run an impact assessment first: acknowledge without applying, identify affected vs. unaffected stages, present options (re-run affected / apply forward only / cancel), and wait for the decision. Surface destructive-change warnings (an activated territory model can't be deleted; an existing user/records/published template remain).

The full behavior matrix, impact-assessment template, per-change impact mapping, and destructive-change warnings are in `references/state-machine-and-changes.md`.

---

## Rules / Constraints

- **Org**: run Phase 0 org selection first; never silently reuse the default org.
- **Shared folder**: download `.lsc-starter-config/LSStarterConfig` exactly once (Phase 1 hard gate), delete it exactly once (Phase 9); child skills never touch it — Stages 2 and 5 read it, so proceeding without it fails downstream.
- **Order**: execute stages strictly 1→6, gating each on prior success; capture each stage's outputs (IDs, names) for later stages.
- **Territory invariant**: reuse the SAME Stage-3 level-3 territory (`OrchestrationState.territoryId`) for Stage 5 (ProductTerritoryAvailability) and Stage 6 (user alignment), or the KAM user sees no data.
- **Confirmation**: confirm only the fields each stage marks admin-confirmable; auto-derive the rest and show for confirmation.
- **Idempotency**: never re-execute a `running`/`passed` stage without confirmation (set `running` at execution start); impact-assess before applying mid-flow changes.

---

## Gotchas

| Issue | Resolution |
|-------|------------|
| Source download fails in Phase 1 | Hard stop — do NOT run any stage. Fix the cause or download `.lsc-starter-config/LSStarterConfig` manually into the CWD, then re-run |
| No connected orgs found | Go straight to the fresh-org login (`sf org login web`) in Phase 0 |
| Artifacts exist from a prior run | Child skills/references are idempotent/upsert-safe — query to confirm, then skip or re-run |
| Stage re-triggered, or earlier input changed mid-flow | See `references/state-machine-and-changes.md` |

---

## Resume / Partial Re-run

If the user may have already completed some stages, ask which, then **verify each claimed-complete stage by querying the org** (1 = ask; 2 = `LSC Custom Profile`; 3 = active model + L3 territory; 4 = `ParticipantRole` + `Sprint`; 5 = Account + `ProductTerritoryAvailability` + `Final` version + assignment; 6 = `kam` user + permsets + territory), skip verified stages, and resume from the first incomplete one. Exact per-stage queries: `references/orchestration-flow.md` → Resume Logic.

---

## Reference File Index

| File | When to read |
|------|-------------|
| `references/orchestration-flow.md` | At start — dependency diagram, gate + resume-detection queries, timing |
| `references/state-machine-and-changes.md` | On a re-triggered stage or a mid-flow input change |
| `references/stage-2-starter-config-overview.md` | Stage 2 — 13-step deploy + KAM/Sprint config records (points to sibling refs) |
| `references/stage-4-participant-role-and-sprint.md` | Stage 4 — participant role + sprint |
| `references/stage-5-data-and-plan-templates-overview.md` | Stage 5 — KAM data creation (Part A, points to its data ref) + goals, tasks, measures, action plan template (Part B) |
| `references/stage-6-user-provisioning-overview.md` | Stage 6 — user provisioning + metadata cache (points to sibling refs) |
| `references/stage-6-ipad-validation-script.md` | Final step — on-device (iPad) validation script shown after the metadata cache is Active |
