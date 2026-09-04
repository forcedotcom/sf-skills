---
name: life-sciences-fieldsalesrep-coordinate
description: "Use this skill to run the full end-to-end Life Sciences Cloud setup workflow for field sales rep in sequence. Trigger when the user says 'set up Life Sciences Cloud end to end', 'run the full LSC setup', 'orchestrate Life Sciences Cloud configuration', 'complete LSC setup', 'Life Sciences Cloud full install', 'set up Life Sciences Cloud end to end for field sales rep', 'run the full LSC setup for field sales rep', 'orchestrate Life Sciences Cloud configuration for field sales rep', 'complete LSC setup for field sales rep', or 'Life Sciences Cloud full install for field sales rep'. Executes five stages in order: prerequisites validation, starter config deployment, territory configuration, user provisioning, and sample visit creation — gating each stage on the success of the previous one. DO NOT TRIGGER when: user wants to run only one specific stage (prerequisites, config deploy, territory setup, user provisioning, or visit creation individually)."
metadata:
  version: "1.0"
  minApiVersion: "65.0"
  domains: ["Life Sciences"]
  relatedSkills:
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

# Life Sciences Cloud End-to-End Orchestrator

Runs the complete Life Sciences Cloud setup workflow as five **stages** in strict sequence, gating each on the success of the previous stage. Each stage delegates to a child skill or a reference workflow, organized internally into **phases** and **steps** (defined under Execution Order below).

## Scope Guard (evaluate FIRST)

Serve **only** requests for the full end-to-end LSC setup. A single stage/phase/step is **never** invokable here — never silently expand a partial ask into the whole flow. Before any work:

- **Unrelated** to LSC setup (at start or mid-run) → do not attempt it. Tell the user you did not understand the request and show what you can help with (full end-to-end LSC setup, or standalone `life-sciences-prerequisites-validate` / `life-sciences-territory-configure`); stop.
- Stage with its **own standalone skill** — prerequisites (Stage 1) or territory config (Stage 3) → redirect to `life-sciences-prerequisites-validate` / `life-sciences-territory-configure`; stop.
- Stage with **no standalone skill** — config deploy (2), user provisioning (4), visit creation (5) → explain these run only as part of the full flow, not on their own; stop. Do **not** launch the full flow unless the user then asks for it.

Continue only for the complete end-to-end setup: orchestrating the full flow (prerequisites → config deploy → territory → user provisioning → visit creation) in order with gates. Each stage's actual work is delegated to child skills / reference files.

---

## Required Inputs

Gather before proceeding:

- **Target org**: The org to deploy to — selected by the user from the list of connected orgs, or a freshly authenticated org (see Phase 0). Never assume a default org silently; always have the user confirm or select the target org before any stage runs.

---

## Execution Order (MANDATORY)

> **Terminology:** **Stage** = one of the 5 units of work (1–5), each delegated to a child skill or a reference workflow; **Phase** = a named group of work inside a stage; **Step** = an atomic action inside a phase. So "Stage 2 › Phase 1 › Step 3" reads top-to-bottom.

Run in this order, each gated on the previous (see the full dependency diagram in `references/orchestration-flow.md`):

| # | Stage | Runs | Gate (must pass to advance) | Output |
|---|-------|------|------------------------------|--------|
| — | **Setup**: download `.lsc-starter-config/LSStarterConfig` | — | Folder present (MANDATORY — hard stop) | Shared source folder in CWD |
| 1 | Prerequisites Validation | `life-sciences-prerequisites-validate` skill | All prerequisites PASS | Org confirmed ready |
| 2 | Starter Config Deploy | `references/stage-2-starter-config-overview.md` | All 13 deploy steps succeed | LSC Custom Profile exists |
| 3 | Territory Configuration | `life-sciences-territory-configure` skill | Territory model Active + L3 territory | Level-3 territory ID + name |
| 4 | User Provisioning | `references/stage-4-user-provisioning-overview.md` | User created, permsets + territory assigned | Rep username |
| 5 | Sample Visit Creation | `references/stage-5-visit-creation-overview.md` | Visit + supporting records created; metadata cache generated | — |

---

## Workflow

### Phase 0 — Org Selection (MANDATORY, runs first)

Before presenting the workflow, establish which org to use. Do this **every time** the user asks to set up Life Sciences Cloud — do not silently reuse the current default org.

1. **List connected orgs**:

   ```bash
   sf org list --json
   ```

   Parse the result and present the authenticated orgs (non-expired) to the user as a numbered list — include alias, username, org type (Dev Hub / Sandbox / Scratch / Production), and the default marker if any:

   ```text
   Connected Orgs — select the target for Life Sciences Cloud setup
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
     1. ls-dev        alice@example.com          (Dev Hub)   [default]
     2. ls-sandbox    alice@example.com.sandbox  (Sandbox)
     3. partial-scr   test-xyz@example.com       (Scratch)

     N. Log in to a fresh org (opens a browser to authenticate a new org)
   ```

2. **Ask the user to choose**: "Which org would you like to use? Enter a number, or choose **N** to log in to a fresh org."

3. **Handle the selection**:
   - **Existing org chosen** → capture its username/alias as the target org for all subsequent steps.
   - **Fresh org chosen (option N)** → authenticate a new org interactively: ask for the login URL (My Domain / instance URL, e.g. `https://mydomain.my.salesforce.com`; `https://login.salesforce.com` for production, `https://test.salesforce.com` for a sandbox) and an alias (e.g. `ls-setup`), then **run the login command yourself**:

        ```bash
        sf org login web --instance-url <user-supplied-url> --alias <user-supplied-alias> --set-default
        ```

     Do not hand the command to the user to run — execute it directly. It opens a browser on the user's machine for them to complete the web login interactively; the command then returns. After it finishes, re-run `sf org list --json` to confirm the new org, then use it as the target org.

4. **Confirm the target org** back to the user before proceeding: "Using **<alias>** (<username>) as the target org for Life Sciences Cloud setup." Store this in `OrchestrationState.targetOrg`.

> If `sf org list` returns no authenticated orgs, go straight to the fresh-org login flow (option N) — there is nothing to select from.

### Phase 1 — Introduction and Confirmation

1. **Present the workflow** to the user:

   ```text
   Life Sciences Cloud — Full Setup Workflow
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

   This will execute 5 stages in sequence. Each stage is internally
   organized into phases and steps.

   Stage 1: Validate Prerequisites
            Checks org settings, permissions, and features

   Stage 2: Deploy Starter Configuration
            Deploys objects, profiles, config records, layouts, flexipages

   Stage 3: Configure Territories
            Creates territory type, model, and 3-level hierarchy

   Stage 4: Provision Field Sales Rep User
            Creates user, assigns profile/permsets, assigns to territory

   Stage 5: Create Sample Visit
            Logs in as the rep, creates account/provider/visit records,
            generates the mobile metadata cache

   Target org: <org>
   ```

2. **Ask for confirmation**: "Ready to begin the full Life Sciences Cloud setup? (yes/no)"

3. **Download the shared source folder ONCE (MANDATORY — hard gate, before any stage).** Both Stage 2 (Starter Config Deploy — metadata + config records) and Stage 5 (Sample Visit Creation — Data CSVs) read from `.lsc-starter-config/LSStarterConfig/`; those stages do NOT download or delete it — the orchestrator owns a single download here and a single delete in Phase 8. Sparse-checkout only that subtree (the repo is large) into the CWD:

   ```bash
   git clone --no-checkout --depth 1 --filter=blob:none \
     https://github.com/SalesforceLabs/LSStarterConfig.git lsstarter-tmp
   cd lsstarter-tmp && git sparse-checkout init --cone \
     && git sparse-checkout set Codey/LSStarterConfig && git checkout && cd ..
   mv lsstarter-tmp/Codey ./.lsc-starter-config && rm -rf lsstarter-tmp
   ```

   > `.lsc-starter-config/LSStarterConfig/` contains its own `sfdx-project.json` (pins `sourceApiVersion: 65.0`) — the deploy step (Phase 3) must run from inside it. If the folder already exists in the CWD (from a prior run), reuse it (skip the download).

4. **Download gate — verify the folder exists before proceeding.** Confirm the download succeeded by checking that `.lsc-starter-config/LSStarterConfig/sfdx-project.json` and `.lsc-starter-config/LSStarterConfig/Data/` are present (e.g. `ls .lsc-starter-config/LSStarterConfig/sfdx-project.json .lsc-starter-config/LSStarterConfig/Data`).
   - If present → set `sourceFolderDownloaded: true` in `OrchestrationState` and proceed to Phase 2.
   - If the download failed or the folder/contents are missing → **STOP. Do NOT proceed to any stage** — every stage depends on this folder. Report the failure and stop:

     ```text
     STOP: Setup cannot start — source download failed

     Could not download .lsc-starter-config/LSStarterConfig from
     https://github.com/SalesforceLabs/LSStarterConfig.git
     Likely: no network / GitHub unreachable, git < 2.25 (no sparse-checkout),
     or insufficient disk space / write permission in the CWD.

     Mandatory prerequisite — no stage can run without it. Fix the cause and
     re-run, or download the folder manually into the CWD, then re-run.
     ```

     Leave `sourceFolderDownloaded: false` and do not advance the workflow.

### Phase 2 — Execute Stage 1: Prerequisites Validation

5. **Run the prerequisites validation** following the `life-sciences-prerequisites-validate` skill workflow exactly.

6. **Gate check**: Review the results.
   - If ALL prerequisites pass → proceed to Stage 2
   - If ANY prerequisite fails → **stop** and present the failure report

   ```text
   STOP: Stage 1 FAILED — Prerequisites not met
   
   <show the prerequisite failure table>
   
   Please resolve the failed prerequisites and re-run this workflow.
   ```

   Ask the user: "Would you like to continue anyway (skip failed prerequisites), or stop and fix them first?"
   - If user says stop → end the workflow
   - If user says continue → proceed with a warning that later stages may fail

### Phase 3 — Execute Stage 2: Starter Config Deploy

7. **Run the starter config deployment** following `references/stage-2-starter-config-overview.md` exactly (all 13 steps in order); read its own reference files as directed.

8. **Gate check**: Verify the LSC Custom Profile exists:
   ```bash
   sf data query --query "SELECT Id, Name FROM Profile WHERE Name = 'LSC Custom Profile'" --target-org <org> --json
   ```
   - If profile exists → proceed to Stage 3
   - If profile not found → **stop** and report deployment failure

### Phase 4 — Execute Stage 3: Territory Configuration

9. **Run the territory configuration** following the `life-sciences-territory-configure` skill workflow exactly.

10. **Gate check**: Verify the territory model is Active and level-3 territory exists:
   ```bash
   sf data query --query "SELECT Id, Name, DeveloperName, Territory2Model.State FROM Territory2 WHERE ParentTerritory2.ParentTerritory2Id != null AND Territory2Model.State = 'Active'" --target-org <org> --json
   ```
   - If level-3 territory found with Active model → capture the territory ID and name, proceed to Stage 4
   - If not found → **stop** and report the issue

### Phase 5 — Execute Stage 4: User Provisioning

11. **Run the user provisioning** following `references/stage-4-user-provisioning-overview.md` exactly; read its own reference file as directed. Pass the territory information captured from Stage 3.

12. **Gate check**: Verify the user exists, has the correct profile, **all 4** permission sets, and territory assignment. Capture the **rep username** — Stage 5 logs in as this user.

    > **STOP-GATE (Stage 4 completeness).** Do NOT accept "user created" as passing this gate — verify all four facets and STOP if any is short:
    > ```bash
    > sf data query --query "SELECT COUNT(Id) c FROM PermissionSetAssignment WHERE AssigneeId = '<newUserId>' AND PermissionSet.IsOwnedByProfile = false" --target-org <org> --json
    > ```
    > The permset count MUST be **4** ({LifeSciencesCore, LifeSciencesFieldSalesRepresentative, HealthCloudStarter, LifeSciencesKeyAccountManager}); the user MUST be `IsActive=true` on the `LSC Custom Profile`; and a `UserTerritory2Association` to the level-3 territory MUST exist. If the permset count is < 4 or any facet is missing, Stage 4 did not fully complete — re-run the missing part of `references/stage-4-user-provisioning-overview.md` (its own Phase 4/5 stop-gates cover this) before advancing to Stage 5. A rep missing a permset silently fails visit creation downstream with confusing permission errors.

### Phase 6 — Execute Stage 5: Sample Visit Creation

13. **Run the visit creation** following `references/stage-5-visit-creation-overview.md` exactly; read its own reference files as directed. Pass the rep username captured from Stage 4. This stage:
    - Logs in as the rep user (`sf org login web`) and creates account, healthcare provider, and visit records (rep-owned), plus territory associations and product master data (admin-owned).
    - Generates the mobile metadata cache via the Connect API (admin-owned).

    > This stage uses **two identities** — the rep user (from Stage 4) for visit records and the admin for product master data and metadata cache generation. Follow the child skill's rep/admin split exactly.

14. **Gate check**: Verify at least one Visit record was created:
    ```bash
    sf data query --query "SELECT Id, Name, AccountId FROM Visit ORDER BY CreatedDate DESC LIMIT 1" --target-org <org> --json
    ```
    - If a Visit exists → proceed to the final summary
    - If no Visit found → **stop** and report the visit-creation failure

### Phase 7 — Final Summary

15. **Display the complete workflow summary** — a "Life Sciences Cloud Setup Complete" header followed by one block per stage (substitute actual values from the run):
    - **Stage 1**: all org prerequisites confirmed.
    - **Stage 2**: objects/profiles/config records deployed, `<N>` layouts + `<N>` flexipages deployed, 28 trigger handlers activated.
    - **Stage 3**: Territory Model `<model name>` (Active); Level-3 Territory `<territory name>`.
    - **Stage 4**: User `<firstName> <lastName>` (`<username>`); Profile `LSC Custom Profile`; permission sets Life Sciences Core, Life Sciences Field Sales Representative, Health Cloud Starter, Life Sciences Key Account Management; Territory `<territory name>`; admin also assigned to the territory.
    - **Stage 5**: Account + Healthcare Provider created; Visit `<subject>` (Territory `<territory name>`); product detailing/discussion records; mobile metadata cache generated (Connect API).

    Close with: "The org is ready for Life Sciences Cloud field sales workflows."

### Phase 8 — Cleanup (delete the shared source folder ONCE)

16. **After the final summary** (all 5 stages complete), delete the `.lsc-starter-config` folder downloaded in Phase 1 to leave the working directory clean. Run from the CWD (the parent of `.lsc-starter-config/`):

    ```bash
    rm -rf .lsc-starter-config
    ```

    Do this **silently** — do NOT print a cleanup line or mention the folder deletion in the final output. **Skip if the workflow stopped on a failure and the user may resume** — keep the folder until the flow completes so a resumed stage can still read it. This is the single deletion for the whole flow; the child skills never delete it.

---

## State Tracking

Maintain overall orchestration state:

```text
OrchestrationState = {
  targetOrg: string,
  sourceFolderDownloaded: boolean,   // .lsc-starter-config/LSStarterConfig downloaded in Phase 1, deleted in Phase 8
  stages: [
    { name: "Prerequisites", status: "pending|running|passed|failed|skipped" },
    { name: "StarterConfig", status: "pending|running|passed|failed" },
    { name: "TerritorySetup", status: "pending|running|passed|failed", territoryId?: string, territoryName?: string },
    { name: "UserProvisioning", status: "pending|running|passed|failed", userId?: string, username?: string },
    { name: "VisitCreation", status: "pending|running|passed|failed", visitId?: string }
  ]
}
```

---

## Idempotent Stage Transitions & Mid-Flow Changes

Stages are **not re-entrant**. Before executing any stage, check its `status` in `OrchestrationState`: `running` → reply "Stage N is already in progress" and take no action; `passed` → ask for explicit confirmation before re-running; `failed` → re-run (intentional recovery); `pending` → advance. Transition status to `running` at execution **start** (not on user input) so accidental double-confirms never run a stage twice.

If the user requests a change to an earlier stage's inputs **while a later stage is in progress or pending**, run an impact assessment first: acknowledge without applying, identify affected vs. unaffected stages, present options (re-run affected / apply going forward only / cancel), and wait for the decision. Surface destructive-change warnings (an activated territory model can't be deleted; an existing user/records remain).

The full behavior matrix, impact-assessment template, per-change impact mapping, and destructive-change warnings are in `references/state-machine-and-changes.md`.

---

## Rules / Constraints

| Constraint | Rationale |
|-----------|-----------|
| Always run Phase 0 org selection first; list connected orgs and let the user pick or log in to a fresh org | User must explicitly choose the target org; never silently reuse the default |
| Download `.lsc-starter-config/LSStarterConfig` exactly once (Phase 1, MANDATORY hard gate) and delete it exactly once (Phase 8); child skills never download or delete it | Both child skills read from the shared folder — proceeding without it guarantees downstream failures |
| Execute stages strictly in order 1→5, gating each on prior success | Each stage depends on outputs from previous stages; prevents cascading failures |
| Never skip Stages 2 or 3, or Stage 4 before Stage 5 | User provisioning depends on profile + territory; visit creation logs in as the Stage-4 rep |
| Follow each child skill's workflow exactly; capture outputs (IDs, names) for later stages | Child skills have their own confirmations; avoids redundant re-queries |
| Never re-execute a `running`/`passed` stage without explicit confirmation; transition status to `running` at execution start, not on user input | Race-free idempotency against duplicate "Proceed" messages |
| Perform impact assessment before applying mid-flow changes | User must see what will break/redo before committing to a change |

---

## Gotchas

| Issue | Resolution |
|-------|------------|
| Source download fails in Phase 1 (network/git/disk) | Hard stop — do NOT run any stage. Report the failure (see Phase 1 download gate); fix the cause or download `.lsc-starter-config/LSStarterConfig` manually into the CWD, then re-run |
| No connected orgs found | `sf org list` returns none — go straight to the fresh-org login (`sf org login web`) in Phase 0 |
| Fresh-org / rep login needs a browser | Run `sf org login web` yourself (Phase 0 org auth, Stage 5 rep login) — don't hand it to the user. It opens a browser on the user's machine; they complete the web login there and the command returns |
| Artifacts exist from a prior run (profile, territory, user, config) | The child skills are idempotent/upsert-safe and detect existing records — query the org to confirm, then skip or re-run safely |
| Visit creation uses two identities (rep + admin) | Product master data and metadata cache are admin-owned; follow the child skill's rep/admin split |
| Stage re-triggered, or user changes an earlier input mid-flow | See the transition matrix and impact assessment in `references/state-machine-and-changes.md` |

---

## Resume / Partial Re-run

If the user may have already completed some stages (e.g. from a prior session), ask which, then **verify each claimed-complete stage by querying the org** (Stage 1 = ask; 2 = `LSC Custom Profile`; 3 = active model + L3 territory; 4 = user with correct profile/permsets; 5 = a `Visit` record). Skip verified stages and resume from the first incomplete one. Exact detection queries per stage are in `references/orchestration-flow.md` → Resume Logic.

---

## Output Expectations

Deliverables:
- `.lsc-starter-config/LSStarterConfig` folder downloaded once (Phase 1) and removed once (Phase 8) — both done silently; not reported in the final summary
- All 5 stages executed successfully (or user-acknowledged skips)
- Full summary of what was created/configured
- Org ready for Life Sciences Cloud field sales workflows

---

## Reference File Index

| File | When to read |
|------|-------------|
| `references/orchestration-flow.md` | At start — the dependency diagram, per-stage gate verification queries, resume-detection queries, and timing expectations |
| `references/state-machine-and-changes.md` | When a stage is re-triggered or the user changes an earlier input mid-flow — the full transition behavior matrix, impact-assessment template + mapping, and destructive-change warnings |
| `references/stage-2-starter-config-overview.md` | During Stage 2 (Phase 3) — the full 13-step starter-config deploy workflow; it points to its own sibling references as needed |
| `references/stage-4-user-provisioning-overview.md` | During Stage 4 (Phase 5) — the full field-sales-rep user provisioning workflow; it points to its own sibling reference as needed |
| `references/stage-5-visit-creation-overview.md` | During Stage 5 (Phase 6) — the full sample-visit creation workflow; it points to its own sibling references as needed |
