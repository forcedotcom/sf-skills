---
name: sales-agentforce-pipeline-management-configure
description: "Use to configure, set up, or repair the Sales Management agent and Agentforce Pipeline Management in a Salesforce org. Automates metadata creation for flows, prompt templates, permission sets, and data source configuration. TRIGGER when: user wants to enable Pipeline Management, configure Sales pipeline features, set up the Sales Management agent for opportunity field updates (including autonomous updates), connect enabled data sources like Einstein Conversation Insights or Einstein Activity Capture, customize opportunity stage descriptions, configure post-meeting suggestions, verify or audit configuration status, fix partially configured orgs, or troubleshoot Pipeline Management metadata issues. DO NOT TRIGGER when: user wants to build a custom agent (use agentforce-generate), configure general Agentforce tracing (use platform-tracing-agentforce-configure), work with non-Sales agents, or enable Einstein Conversation Insights or Einstein Activity Capture from scratch (provisioning is out of scope)."
metadata:
  version: "1.0"
  minApiVersion: "67.0"
  relatedSkills:
    - "agentforce-generate"
    - "platform-tracing-agentforce-configure"
  cliTools:
    - tool: ["curl"]
      semver: ">=7.0.0"
    - tool: ["jq"]
      semver: ">=1.6.0"
    - tool: ["python3"]
      semver: ">=3.10.0"
    - tool: ["sf"]
      semver: ">=2.139.6"
---

# Agentforce Pipeline Management Configuration

Configure Agentforce Pipeline Management end-to-end in a Salesforce org. This skill handles both greenfield orgs (zero configuration) and partially configured orgs that need repair or completion.

## Scope

- **In scope**: Enabling Pipeline Management, configuring the Sales Management agent, activating/customizing flows (Process Field Update Suggestions, Get Opportunity Grounding Data, Get AI Recommendations from Call Transcripts), prompt template configuration, permission set assignment, data source setup, opportunity stage descriptions, autonomous field update configuration, and partial-org repair.
- **Out of scope**: Building custom agents from scratch (use `agentforce-generate`). Einstein Conversation Insights or Einstein Activity Capture initial provisioning (those are separate products). Slack app installation. Custom Apex triggers on Opportunity Team Member.

---

## Prerequisites

### You must verify (scripts cannot check or change these)

1. **Edition**: Enterprise, Performance, Unlimited, or Developer Edition with Agentforce for Sales add-on (or Agentforce 1 Sales Edition). Setup **probes** this up front (Step 0) — it fails fast with a license/edition message on an org that can't run Pipeline Management, before asking anything — but edition/license provisioning itself is still admin-owned.
2. **User permissions**: The executing user needs `View Setup` AND (`Modify All Data` OR `Customize Application`), `Manage AI Agents` AND (`Manage Agentforce Employee Agents` OR `Customize Application`), and `Assign Permission Sets`.

### Enabled automatically by `scripts/setup-all.sh`

The following settings are toggled by setup automatically — do not enable them manually before running the script.

- **Einstein Generative AI** (`EinsteinGptSettings.enableEinsteinGptPlatform`) — **required**; must be on before Agentforce Agent.
- **Agentforce Agent** (`EinsteinCopilotSettings.enableEinsteinGptCopilot`) — **required**; depends on Einstein Generative AI.
- **Agentforce Studio / Agent Platform** (`AgentPlatformSettings.enableAgentPlatform`) — **required**; depends on Agentforce Agent and gates the Deal Agent. Core rejects `SalesDealAgentSettings.enableDealAgent` when this is off, surfacing as an opaque Deal Agent activation failure.
- **Enhanced Notes** (`EnhancedNotesSettings.enableEnhancedNotes`) — **required**; Pipeline Management uses ContentNote as a primary data source.
- **Opportunity Team** (`OpportunitySettings.enableOpportunityTeam`) — **required**; the suggestion flow uses OpportunityTeamMember and will fail deployment without it.
- **Pipeline Inspection** (`OpportunitySettings.enablePipelineInspection`) — **required**; provides the UI where reps view and accept/dismiss suggestions. Suggestions still generate without it, but users have nowhere to see them.
- **Enhanced Email** (`EmailAdministrationSettings.enableEnhancedEmailEnabled`) — **optional but recommended**; only needed for email-body indexing when Einstein Activity Capture is in use.
- **Pipeline Management** (`SalesDealAgentSettings.enableDealAgent`) — **required**; the feature itself.

---

## Clarifying Questions

> **Run the license preflight FIRST — before asking any of these questions.** As
> your very first action (right after resolving the org alias), run
> `bash scripts/setup-all.sh <org-alias> --check-license`. It runs only auth + the
> capability gate, asks nothing, and changes nothing. **If it exits non-zero**,
> relay the printed license/edition blocker to the user and **STOP** — do not ask
> any clarifying question and make no changes. Only when it exits 0 (org is
> capable — greenfield or already provisioned) proceed to the questions below.

Once the preflight passes, determine:

1. **Greenfield or repair?** Is this a new org that has never had Pipeline Management, or one with partial configuration?
2. **Data sources**: Which data sources should inform the agent?
   - Notes (enabled by default)
   - Emails (requires Einstein Activity Capture)
   - Voice/Video calls (requires Einstein Conversation Insights)
   - Enhanced Email (for email body indexing — requires `EmailAdministrationSettings.enableEnhancedEmailEnabled`)
3. **Autonomous updates**: Should the agent update opportunity fields autonomously, or only suggest updates for user review?
4. **Which fields should the agent manage? (ask this FIRST, up front — setup is field-selection-driven).** `setup-all.sh` builds the flow with **only the fields you select**, from the start — there is no deploy-both-then-strip step. Ask: *"Which Opportunity fields should the agent suggest values for? The OOTB options are Next Step (`NextStep`) and Opportunity Stage (`StageName`); you can also add custom text fields (e.g. a Competitor Analysis field)."*
   - **At least 1 field is REQUIRED** — setup aborts (exit 1) if zero fields are selected. There is **no** default to `NextStep`.
   - **Hard cap: 5 fields total**; OOTB fields count toward it. Selecting more aborts before any change.
   - Pass the set with `--fields "NextStep,StageName,Risk__c"` in non-interactive runs, or type it at the interactive prompt.
5. **Per-field prompt customization (all fields EXCEPT `StageName`).** For each selected non-`StageName` field, setup collects an optional **goal** ("You must think about…") and **instruction** (extraction guidance):
   - **`NextStep`** ships with a curated OOTB managed prompt. Setup only overrides it when you supply a goal/instruction (interactive: it asks whether to customize; non-interactive: pass `--field-goal "NextStep:…"` / `--field-instruction "NextStep:…"`). Skip customization to keep the OOTB prompt.
   - **Custom fields** always get a goal/instruction (your text, or the script's sensible defaults).
   - **`StageName` is NOT customizable** — it is a managed picklist template with no override support; setup never prompts for it.
6. **Custom field eligibility**: Only standard or custom **text** fields on Opportunity are supported — plain Text (`type=string`) or Text Area ≤ 255 (`type=textarea`, `htmlFormatted=false`); length ≤ 255; not Long Text Area (length > 255), Rich Text Area (`htmlFormatted=true`), picklist, or formula. The suggestion is capped at the field's own length. Fields selected in question 4 are wired during `setup-all.sh`; **additional** fields added *after* setup use `scripts/add-field-suggestion.sh <org-alias> <FieldApiName>` (one per field; see Phase 4.3). Both paths enforce the 5-total cap — `add-field-suggestion.sh` refuses to wire a 6th field.
7. **Opportunity stages**: Opportunity stages are picklist values, and different Opportunity record types may expose different stage subsets. Are standard or custom opportunity stages in use? Do their descriptions need to be defined/updated? Note: `OpptStageDescription` is **global-per-stage** — keyed only by `OpportunityStageApiName`, with no per-record-type column — so a description is written **once per active stage** and applies across every record type that exposes that stage. Setup works the same whether or not the org has Opportunity record types.

---

## Admin Communication Guidelines

**CRITICAL**: This skill serves admin users, not developers. Follow these rules:

1. **Run all bash commands in background** (`run_in_background: true`) - this includes the main setup commands AND any log-tailing for progress monitoring
2. **Monitor progress without showing commands** - You can tail logs to provide progress updates, but run tail commands in background too. Parse the output and show only friendly updates like "✓ Opportunity Team: enabled". Never show the tail command itself or raw log lines.
3. **Investigate errors silently** - When something fails, do your diagnosis (check data, run queries, fix environment issues) in background without narrating each step. Only surface the conclusion and action: "I need to create a test opportunity first. Let me do that..." NOT "The --json output is corrupted... let me check... ANSI color codes... let me fix..."
4. **Narrate in plain language**: Say "Setting up the platform..." NOT "Running setup-all.sh Phase 1.5"
5. **Hide technical details**: No SOAP responses, curl commands, jq parsing, phase numbers, or script paths unless user asks to debug
6. **Check exit codes**: Always parse success/failure and translate technical errors to admin-friendly messages
7. **Set time expectations**: "This takes ~3 minutes..." prevents "is it frozen?" questions
8. **Handle errors gracefully**: Auto-retry transient failures; explain and offer choices for real blockers

See `references/admin-communication.md` for detailed error translation patterns, examples, and recovery strategies.

## Workflow

**IMPORTANT — Primary Entry Point**: For end-to-end setup, drive `scripts/setup-all.sh`. It handles all prerequisites, enablement, flow deployment, permissions, and verification in the correct dependency order. Only use individual scripts when diagnosing or repairing specific components after `setup-all.sh` has run.

`setup-all.sh` is a **3-phase, field-selection-driven** setup: (1) platform enablement + agent user + PSG assignment; (2) field selection → prompt template creation/activation → stage descriptions (only if `StageName` selected) → prompt verification; (3) flow build (selected fields only), flow activation, agent activation, PSG recalc. It is **safe by default**: suggestions-only mode, no stage-description creation unless asked, and the flow does not go live until the prompts are in place.

#### Canonical agent path — two calls with an interactive tune-loop between them

See `references/canonical-agent-path.md` for the full two-call pattern with code examples, agent rules, narration templates, and internal step map.

**Summary**: Split setup into Call 1 (`--through-phase prompts`) and Call 2 (`--from-phase flow`) with a tune-loop between them where you drive prompt approval per field. Call 2 is MANDATORY — without it no flow exists and no suggestions generate.

#### Unattended / CI path (single call, no tune-loop)

For fully unattended runs (cron/CI, or when the user explicitly declines prompt review):

```bash
bash setup-all.sh <org-alias> --fields "NextStep,StageName,Risk__c" \
  [--field-goal "NextStep:<text>"] [--field-instruction "NextStep:<text>"] \
  [--autonomous] [--create-stage-descriptions] [--skip-prompt-verification] \
  --non-interactive [--users "a@x.com,b@x.com"]
```

In single-pass mode the verification step still prints each field's suggestion (informational). Relay them to the user.

#### Flags

See `references/flags.md` for complete flag documentation. Key flags:

- `--check-license` — preflight only (exit 0 = capable, 1 = blocker). Run FIRST.
- `--through-phase prompts` / `--from-phase flow` — split-run endpoints (mutually exclusive)
- `--fields "NextStep,StageName"` — required field set (at least 1, max 5)
- `--autonomous` — enable auto-apply mode (off by default)
- `--non-interactive` / `--yes` — unattended mode (requires `--fields`)
- `--users "a@x.com,b@x.com"` — explicit user list for PSG assignment (email-validated)

The phases below explain the decision logic for manual/repair scenarios. See `references/setup-order.md` for step-by-step details.

### Automation Summary

Every configuration step and whether it's CLI-automatable (and how) or UI-only lives in `references/automation-matrix.md`. In short: prerequisites, enablement, flow clone/activation, agent publish/activation, permissions, field suggestions, and stage descriptions are all CLI-automatable (`setup-all.sh` does them in dependency order); only Agent Analytics is UI-only.

---

### Phase 0 — Authentication and Org Assessment

1. **Authenticate** — See `references/auth-and-cli.md`. Always use `2>/dev/null` on `sf --json | jq`.

2. **Assess org state** — Branching signals (NOT PSG existence — PSGs ship with the license even in unconfigured orgs):
   - **Enablement**: `SalesDealAgentSettings.enableDealAgent` via SOAP readMetadata
   - **Setup-has-run** (any of): (a) agent user holds `SalesManagementAgentUserPsg`, (b) flow `Process_Field_Update_Suggestions` exists (by ApiName, not label), (c) `BotDefinition` with `AgentTemplate IN ('SalesMgmt__NGASalesAgent','SalesMgmt__SalesAgent')`

3. **Run `scripts/setup-all.sh <org-alias>`** — handles branching automatically:
   - No enablement + no signals → greenfield (Phase 1)
   - Partial signals → repair (Phase 3)
   - All present → verification only

### Phase 1 — Enable Prerequisites and Pipeline Management

**See `references/setup-order.md` for complete scripts.** Enable in dependency order: Einstein GenAI → Agentforce Agent → Agent Platform → Enhanced Notes → Opportunity Team → Pipeline Management → Pipeline Inspection. Then deploy the flow (`scripts/create-flow.sh`) and verify agent architecture (`references/agent-creation.md`).

**What auto-creates on enablement**: agent user + PSGs (auto-assigned). **What you must create**: `BotDefinition:SalesAgent` (via authoring-bundle publish) and the schedule-triggered flow (via template deploy).

### Phase 2 — Assign Permissions

1. **Define Agent Access**: `bash scripts/define-agent-access.sh <org-alias>` — creates custom permset, links into both PSGs. See `references/agent-creation.md` → "Agent Access".

2. **Assign PSG to target users**: **HARD RULE — never bulk-assign.** Grant `SalesManagementUserPsg` only to: (1) the running user, and (2) explicit `--users` list. No enumerate-and-grant.

### Phase 3 — Repair Mode (Partially Configured Org)

See `references/repair-diagnostics.md` for the full checklist. Common issues: flow deactivated → Tooling API `PATCH`; agent not active → `sf agent activate`; prompt template inactive → version round-trip redeploy; agent missing → SOAP toggle off/on.

### Phase 4 — Customize (Admin Decisions Required)

1. **Define Opportunity Stage Descriptions** — Use the "propose and correct" pattern from `references/opportunity-stages.md`. Query active stages, present defaults from reference file, apply user corrections, bulk-create via Tooling API.
   
   **IMPORTANT**: Stage descriptions MAY be auto-provisioned when Pipeline Management is enabled (test orgs showed MEDDIC descriptions pre-populated). **Always CHECK for existing descriptions BEFORE attempting to create them**. If descriptions already exist, UPDATE rather than CREATE to avoid duplicates.

2. **Configure additional data sources** — See `references/data-sources.md` for decision table (Einstein Conversation Insights, Einstein Activity Capture, Inbox).

3. **Add custom opportunity field suggestions (AFTER setup)** — Fields chosen at setup time are wired by `setup-all.sh --fields`. To add a **new** field to an already-configured org, run `scripts/add-field-suggestion.sh <org-alias> <FieldApiName>` (e.g. a `Risk__c` field). The script validates the field, fills the canonical template (`assets/field-completion-template.genAiPromptTemplate-meta.xml`), deploys and activates it via the version round-trip, and idempotently wires the field into the live `Process_Field_Update_Suggestions` flow (respecting the 5-field cap). Optional flags: `--label`, `--goal`, `--instruction` (the two field-specific prompt lines), `--verify-with-note` (seed a Note + run a synchronous generation), `--opp <Id>`, `--skip-flow`, `--force`. See `references/field-completion-prompts.md` for mechanics and `references/field-completion-prompt-template.md` for writing the goal/instruction lines.

   > **Naming note**: the prompt-template `<type>` is `einstein_gpt__fieldCompletion` (used in all metadata — never change it). The **Setup UI** (Prompt Builder) labels this category **"Field Generation"** — same thing. Admins should look for "Field Generation", not "Field Completion".

4. **Configure autonomous updates** — Autonomous mode is a single **org-wide** toggle (`SalesDealAgentSettings.enableDealAgentAutoApproveAllTasks`), not a per-field setting: when ON, the agent auto-applies all field suggestions without review; when OFF (the default), every suggestion waits for human approval. It is opt-in via `setup-all.sh --autonomous`. See `references/autonomous-updates.md` for the toggle and safety considerations.

5. **Enable Agent Analytics** — Setup → Einstein Feedback and Monitoring → Agent Analytics (UI-only).

---

## Understanding the Flows

See `references/flow-clone-from-template.md` for complete flow architecture, clone approach, and technical constraints.

**Key facts**: Pipeline Management uses a schedule-triggered flow (`Process_Field_Update_Suggestions`) cloned from the managed template. Detection is by ApiName (not label). The flow calls `getOrExecFieldUpdtSuggestion` with the selected fields — adding a field requires both activating its template AND wiring it into the flow's collection (handled atomically by `add-field-suggestion.sh`). **No suggestions generate until this flow is active.**

---

## Key Considerations

- **Pipeline Management REQUIRES a standalone `BotDefinition:SalesAgent`** — a missing BotDefinition blocks setup. Auto-provisioning creates it in most editions, but where it doesn't, `publish_and_activate_agent()` (in `shared/agent-bundle-publish.sh`, called by `setup-all.sh` and `create-agent.sh`) publishes the bundle from `assets/sales_management_agent.agent` and activates it. Do NOT rely on the `EmployeeCopilotPlanner` fallback — users need the interactive chat surface.
- Flow runs only when agent is **active** with **Read/Write** on opportunities; agent joins as opportunity team member (watch for Apex triggers on OpportunityTeamMember)
- Daily limit: 8,000 LLM requests / ~4,000 opportunities. Suggestions expire after 30 days
- Stage template reads `OpptStageDescription` via `GetOpportunityStageDetailsInvocableAction` — **stage suggestions fail** if any active stage lacks a description
- **Do NOT use CLI Metadata deploy** for DealAgent enablement — SOAP API v64.0 only (CLI has silent failure mode)
- **Do NOT enable `BotSettings`/`enableBots`** — legacy messaging bots, unrelated, fails with "Legal Terms" error
- Pipeline Management does NOT use a managed package — components provisioned directly on enablement
- Toggle not visible in Setup → verify Sales Cloud EE+ license and Agentforce SKU
- Always use `2>/dev/null` on `sf ... --json` piped to jq (strips CLI warnings that corrupt JSON)

---

## References

- `references/setup-order.md` — Complete copy-paste setup sequence with all scripts
- `references/soap-api-enablement.md` — SOAP API patterns for all prerequisites
- `references/flow-clone-from-template.md` — Flow clone approach with ApiName-based detection
- `references/agent-creation.md` — Agent creation (auto-provisioning + authoring-bundle publish; the SOAP toggle only re-provisions the agent user and PSGs, not the BotDefinition)
- `references/field-completion-prompts.md` — Adding custom field suggestions end-to-end (verified v67 pattern, the three requirements, `add-field-suggestion.sh` mechanics, verification)
- `references/field-completion-prompt-template.md` — Writing the field-specific goal/instruction lines the script consumes
- `references/opportunity-stages.md` — Stage descriptions + methodologies
- `references/repair-diagnostics.md` — Partially configured org handling
- `references/auth-and-cli.md` — Auth methods, CLI compatibility
- `references/data-sources.md` — Decision table for EAC/ECI/Notes/Enhanced Email
- `references/autonomous-updates.md` — Auto-apply mode toggle and safety considerations
- `references/metadata-inventory.md` — Complete inventory of provisioned metadata components
- `references/automation-matrix.md` — Which setup steps are CLI-automatable (and how) vs UI-only
- `references/admin-communication.md` — Admin-friendly narration patterns: error-translation table, silent-investigation examples, and per-step narration templates for driving setup conversationally

## Examples

- `examples/custom-prompt-instructions.md` — Custom prompt instruction patterns for methodology alignment and update aggressiveness control

## Standalone Scripts

Executable scripts for each setup phase (run from `scripts/` directory with `sfdx-project.json` in CWD):

- `scripts/setup-all.sh` — **Master orchestration**: 3-phase, field-selection-driven end-to-end setup (auth + enablement + agent user/PSG → field selection + prompt templates + stage descriptions + prompt-verification gate → flow build/activate + agent activate + PSG recalc). Requires `--fields` (aborts if none); interactive by default; safe defaults (suggestions-only, no stage-description creation) with `--field-goal`/`--field-instruction`, `--autonomous`, `--create-stage-descriptions`, `--skip-prompt-verification` opt-in flags and `--non-interactive`/`--yes` for unattended runs
- `scripts/shared/flow-builder.sh` — flow field-collection helpers sourced by `setup-all.sh`: `build_field_collection` (greenfield — writes a flow wiring only the selected fields), plus `strip_flow_field` / `add_flow_field` / `flow_wired_fields` (repair — reconcile an already-deployed flow's fields in place)
- `scripts/shared/stage-descriptions.sh` — Phase 4c.5 stage-description creation sourced by `setup-all.sh`; exports `run_stage_descriptions()` (self-gates on `STAGENAME_SELECTED`; sets `STAGE_DESCRIPTIONS_BLOCKED` for the Phase 8.5 summary)
- `scripts/shared/test-opp.sh` — shared test-opportunity + grounding-note resolution sourced by both verify scripts (`flow-debug-and-verify.sh`, `verify-prompt-generation.sh`); exports `resolve_test_opportunity` (reuse/create/fallback the `[PM-TEST]` test opp, roll CloseDate, seed/refresh the grounding note) and `seed_grounding_note`
- `scripts/retrieve-settings.sh` — Audit current org settings state
- `scripts/enable-prerequisites.sh` — Enable prerequisite **settings only** (Einstein GenAI, Agentforce, Enhanced Notes, Opportunity Team) via SOAP — no fields/flow/agent. `setup-all.sh` runs this same enablement inline; use the standalone script only for surgical, non-destructive prerequisite toggling
- `scripts/enable-deal-agent.sh` — Enable Pipeline Management via SOAP API (standalone helper; `setup-all.sh` enables PM inline — use this only for isolated manual toggling)
- `scripts/create-flow.sh` — Detect, deploy from template, or activate suggestion flow (falls back to UI guidance)
- `scripts/create-agent.sh` — Verify/create/activate agent (auto-provisioning + authoring-bundle publish; SOAP toggle only re-provisions agent user/PSGs, not the BotDefinition); also defines Agent Access on completion
- `scripts/define-agent-access.sh` — Define Agent Access so both users holding `SalesManagementUserPsg` and the autonomous agent user holding `SalesManagementAgentUserPsg` can launch/run the agent (custom permset + `SetupEntityAccess` + `PermissionSetGroupComponent` into both PSGs + recalc)
- `scripts/deploy-settings.sh` — Deploy non-SOAP settings (Notes, Email, Opportunity)
- `scripts/add-field-suggestion.sh` — Add an AI field-completion suggestion for any eligible Opportunity text field (validate → fill canonical template → deploy + activate via version round-trip → wire flow; `--verify-with-note` for synchronous generation)
- `scripts/verify-all.sh` — Comprehensive configuration status check (read-only)

## Admin Verification Tools

The following scripts help admins verify that Pipeline Management is working correctly after setup. Use these to confirm field suggestions are generating as expected.

**Before running either verify script, compose a realistic grounding note and pass it via the `PM_GROUNDING_NOTE` env var.** The AI only generates a suggestion when the opportunity's Note carries real sales context — a generic placeholder grounds on nothing and returns empty, making a working setup look broken. Write a few sentences of a plausible sales call/meeting reflecting the configured `--fields` and any `--field-goal`/`--field-instruction` (e.g. concrete next steps and deadlines for `NextStep`; buyer, budget, pain, and timeline signals for `StageName`). Do not use a rigid template — tailor it to what was configured. Example: `PM_GROUNDING_NOTE="Discovery call with the VP of Sales: confirmed a $250K budget and a Q3 go-live; agreed next steps are a technical deep-dive with IT and an ROI analysis." bash scripts/flow-debug-and-verify.sh <org>`. Absent the env var, the scripts fall back to a generic note.

**Both scripts are invoked separately by the skill but converge on the SAME test opportunity and the SAME grounding note.** They both find-or-create a user-owned opp named `[PM-TEST] Test Pipeline Verification Opp` (the `[PM-TEST]` prefix makes every opp this tooling creates findable via `Opportunity WHERE Name LIKE '[PM-TEST]%'`). On reuse they roll the opp's CloseDate +30 days so it stays flow-eligible, and refresh the grounding note only when the `PM_GROUNDING_NOTE` you pass differs from the stored one (otherwise the existing note is left untouched). Pass the same `PM_GROUNDING_NOTE` value to both invocations so the note is consistent regardless of run order.

- `scripts/flow-debug-and-verify.sh` — Guided two-phase verification of the scheduled suggestion flow.
  - **flow-debug-start** (`bash scripts/flow-debug-and-verify.sh <org> [opp-id]`) reuses a stable user-owned test opportunity named `[PM-TEST] Test Pipeline Verification Opp` if one is still eligible (so repeated runs don't pile up duplicate opps), otherwise creates it, falls back to any user-owned open opp if creation fails, seeds/refreshes a grounding Note on whichever opp resolves, and prints the flow's **Debug** URL, the opportunity to select, and the exact `verify` command to run afterward — including a trailing baseline count (the pre-run suggestion count). It uses a user-owned opp so the resulting suggestion is visible in the admin's owner-scoped Pipeline Inspection. If no opportunity is available it prints an actionable message and exits 0 without verifying. Relay the URL + opportunity to the user and wait for them to run Debug in Flow Builder against that opportunity — this is the only on-demand path that binds a real `$Record` on a scheduled record-triggered flow (leave rollback mode UNCHECKED so the DML persists).
  - **verify** (`bash scripts/flow-debug-and-verify.sh <org> <opp-id> verify [baseline]`) runs after the user confirms the debug run finished: it confirms the flow reached its action (agent user added to the Opportunity Team) and polls (~4 min) for the generated `AiGenActionItem` suggestions. **Pass the baseline that flow-debug-start printed** — it is captured *before* the debug run, so the delta is exact; omitting it falls back to weaker absolute detection. The wait between phases happens in the conversation, not inside the script.
- `scripts/verify-prompt-generation.sh` — Test the prompt template behind a field by calling the Einstein `/generations` API directly. Pass the **field** API name (`bash scripts/verify-prompt-generation.sh <org> <field> [opp-id]` — e.g. `NextStep`, `Risk__c`); it resolves the field to its managed/derived template (a bare, un-namespaced managed name returns `ENTITY_IS_DELETED`) and uses the same user-owned opp selection strategy as `flow-debug-and-verify.sh` (both share one sourced lib: reuse the shared `[PM-TEST] Test Pipeline Verification Opp` → create it → owner-scoped fallback → graceful skip) — the only difference on skip is that no Einstein endpoint call is made. Shows the actual suggestion text generated, helping admins validate custom prompt instructions.

## Agent Assets

- `assets/sales_management_agent.agent` — Agent Script definition for the Sales Management Agent (used when auto-provisioning fails)
- `assets/sales_management_agent.bundle-meta.xml` — AiAuthoringBundle metadata (deploy with `sf agent publish authoring-bundle --api-name SalesAgent`)
- `assets/field-completion-template.genAiPromptTemplate-meta.xml` — Canonical `einstein_gpt__fieldCompletion` prompt template with `@@PLACEHOLDERS@@`, filled in by `scripts/add-field-suggestion.sh` (do not deploy directly)
