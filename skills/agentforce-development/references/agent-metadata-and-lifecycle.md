# Agent Metadata and Lifecycle Reference

## Table of Contents

1. Agent Metadata Structure
2. Agent Metadata Lifecycle Overview
3. Creating an Agent
4. Working With Authoring Bundles
5. Publishing Authoring Bundles
6. Activating Published Agents
7. Lifecycle Operations

---

## 1. Agent Metadata Structure

Agent Script agents are defined across two independent metadata domains. Understanding this distinction is critical for every lifecycle operation.

### Two-Domain Entity Graph

```
AUTHORING DOMAIN (developer-owned, exists before any publish)
  AiAuthoringBundle
    ├── .agent (Agent Script source — editable text file)
    └── .bundle-meta.xml (metadata; optional <target> links to published version)

RUNTIME DOMAIN (created by publish)
  Bot (top-level container, one per agent)
    └── BotVersion (one per published version)
          └── GenAiPlannerBundle (versioned bundle, contains compiled agent definition)
                └── local topics and actions (scoped to this version only)
```

The authoring domain is where you work. The runtime domain is what the org creates when you publish. These two domains are separate until you publish, which is when they connect.
### The Authoring Domain: AiAuthoringBundle

An `AiAuthoringBundle` is a Salesforce metadata source component represented as a directory in your local project containing two files:

**1. `.agent` file** —  Agent Script source code. This is the editable text file where you define topics, actions, variables, and flow control. It is human-readable and supports multiple versions.

**2. `.bundle-meta.xml` file** — Metadata about the bundle. Contains a `bundleType` element set to `AGENT` and optionally a `<target>` element that controls whether the bundle is DRAFT (editable) or locked to a published version:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<AiAuthoringBundle xmlns="http://soap.sforce.com/2006/04/metadata">
    <bundleType>AGENT</bundleType>
    <target>Local_Info_Agent.v2</target>
</AiAuthoringBundle>
```

When `<target>` is present, the bundle is locked to that published version and cannot be modified. Draft-state bundles omit `<target>` entirely.
Authoring bundles are stored in `<packageDirectory>/main/default/aiAuthoringBundles/` where `<packageDirectory>` comes from `sfdx-project.json`.
### Two Forms of AiAuthoringBundle Locally

**Naked AiAuthoringBundle** (e.g., `Local_Info_Agent`) — No version suffix in the directory name. In the org, this always points to the highest DRAFT version. This is the only writable surface for pro-code developers.
**Version-suffixed AiAuthoringBundle** (e.g., `Local_Info_Agent_1`, `Local_Info_Agent_2`) — Published snapshots retrieved from the org after publication. Locked by a `<target>` element in their `bundle-meta.xml`. Read-only — modified deploys fail; unmodified deploys succeed as misleading no-ops. Use these for version history inspection, diffing, and auditing. NEVER edit a version-suffixed authoring bundle expecting your changes to persist.
### The Runtime Domain: Bot → BotVersion → GenAiPlannerBundle

Publishing creates the runtime entities that make an agent usable in the org.

**Bot** — Top-level container (one per agent). Links to all published versions.

**BotVersion** — One per published version (e.g., `v1`, `v2`, `v3`). Only one version can be active at a time.

**GenAiPlannerBundle** — Compiled agent definition for a specific version. Contains topics, actions, and all runtime metadata, scoped to that version only.

Runtime entities are org-generated and never edited directly.
### Agent Pseudo Metadata Type

When using the Salesforce CLI, `Agent:X` is a pseudo-metadata type that covers the runtime domain components: `Bot`, `BotVersion`, `GenAiPlannerBundle`, and related GenAiPlugin/GenAiFunction metadata. This saves you from specifying each type individually during retrieve/deploy.

**CRITICAL GOTCHA:** `Agent:X` retrieve does NOT include `AiAuthoringBundle`. If you need the authoring bundle (to see the `<target>` element or to work with the source), use `AiAuthoringBundle:X` explicitly.
---

## 2. Agent Metadata Lifecycle Overview

### Recommended Pipeline

The end-to-end pipeline for creating and activating an agent:

1. `sf agent generate authoring-bundle --json --no-spec --name "<Label>" --api-name <Developer_Name>`
2. Edit the `.agent` file locally
3. `sf project deploy start --json --metadata AiAuthoringBundle:<Developer_Name>`
4. `sf agent validate authoring-bundle --json --api-name <Developer_Name>`
5. `sf agent publish authoring-bundle --json --api-name <Developer_Name>`
6. `sf agent activate --json --api-name <Bot_API_Name>`

Each phase is detailed in the sections that follow.
### Lifecycle Phases

**Phase 1: Generate** — Create a boilerplate `AiAuthoringBundle` in your local project with `sf agent generate authoring-bundle`. The authoring bundle exists locally only; the org is unaffected. See Section 3.

**Phase 2: Deploy** — Push the `AiAuthoringBundle` to the org using `sf project deploy start`. This populates the authoring domain only — the authoring bundle becomes visible in Agent Builder (part of Agentforce Studio) for low-code authoring and preview. The `Bot` and `GenAiPlannerBundle` metadata entities are NOT created yet. 

**Phase 3: Publish** — Compile the `AiAuthoringBundle` and create the full runtime entity graph with `sf agent publish authoring-bundle`. This populates the runtime domain: `Bot`, `BotVersion`, and `GenAiPlannerBundle` are created. See Section 5.

**Phase 4: Activate** — Make a published version live with `sf agent activate`. Only one version can be active at a time. Published agents must be activated before they can be previewed with `--api-name` or used in production. See Section 6.
**Phase 5: Test** — Create test specs (`sf agent test create`), run tests against the activated agent (`sf agent test run`), and check results (`sf agent test resume`). Tests run against activated published agents only — DRAFT authoring bundles cannot be tested. The `sf agent test create` command compiles an Agent Test Spec (YAML) into `AiEvaluationDefinition` metadata in the org. See Section 7 (Test Lifecycle).
### Deploy vs. Publish: The Critical Distinction

These are two different operations that populate different domains.

**Deploy** (`sf project deploy start`): Metadata operation only. Puts the `AiAuthoringBundle` source file into the org's authoring domain. Does NOT create Bot, BotVersion, or GenAiPlannerBundle. The authoring bundle IS visible in Agentforce Studio for low-code users to edit and preview as a DRAFT. Deploy is a staging step — useful for pro-code/low-code collaboration where pro-code developers author locally and deploy to get the authoring bundle into Builder for low-code refinement.
**Publish** (`sf agent publish authoring-bundle`): Full entity creation. Deploys the `AiAuthoringBundle`, compiles Agent Script to Agent DSL, and creates the entire runtime entity graph (Bot + BotVersion + GenAiPlannerBundle + GenAiPlugins). Publish is self-contained — a brand-new `AiAuthoringBundle` can be published directly with no prior deploy or org state.

Mental model: the `AiAuthoringBundle` is the recipe; the runtime domain entities are the cooked dish; publish is the act of cooking. Deploy stages the recipe in the org's kitchen — publish actually cooks it.
---

## 3. Creating an Agent

Use the `sf agent generate authoring-bundle` command to create a new agent. This command requires three flags.

### Command Syntax

```bash
sf agent generate authoring-bundle --json --no-spec --name "<Label>" --api-name <Developer_Name>
```

**Required flags:**

- `--json` — Always set first. Produces machine-readable output.

- `--no-spec` — This flag must be present, or the command hangs waiting for input.

- `--name "<Label>"` — The human-readable display name. This becomes `agent_label` in the Agent Script `config` block. Example: `"Local Info Agent"`. Wrap in quotes if the label contains spaces.

- `--api-name <Developer_Name>` — The unique API identifier (no spaces, letters/numbers/underscores only). This becomes `developer_name` in the `config` block. Example: `Local_Info_Agent`.
### What the Command Creates

The command creates two files in a directory named after your `--api-name`:

```
aiAuthoringBundles/
  └── Local_Info_Agent/
        ├── Local_Info_Agent.agent (editable source)
        └── Local_Info_Agent.bundle-meta.xml (metadata)
```

The `.agent` file contains boilerplate with `system`, `config`, `start_agent`, and placeholder topics. You edit this file to define your agent.

The `.bundle-meta.xml` file is initially minimal (bundleType only, no `<target>`), indicating DRAFT state.
### Common Failure Modes with WRONG/RIGHT Pairs

**1. Omitting `--no-spec`**

```bash
# WRONG — CLI waits for spec file (hangs)
sf agent generate authoring-bundle --json --name "Local Info Agent" --api-name Local_Info_Agent

# CORRECT — explicit --no-spec
sf agent generate authoring-bundle --json --no-spec --name "Local Info Agent" --api-name Local_Info_Agent
```

Without `--no-spec`, the CLI expects interactive input. Always include `--no-spec`.
**2. Confusing `--name` and `--api-name`**

```bash
# WRONG — swapped; produces invalid developer_name
sf agent generate authoring-bundle --json --no-spec \
    --name Local_Info_Agent \
    --api-name "Local Info Agent"

# CORRECT — name is human-readable (spaces OK), api-name is identifier
sf agent generate authoring-bundle --json --no-spec \
    --name "Local Info Agent" \
    --api-name Local_Info_Agent
```

`--name` is the label (human-readable, can include spaces, goes in `agent_label`). `--api-name` is the developer name (identifier, no spaces, goes in `developer_name`).
---

## 4. Working With Authoring Bundles

This section covers the non-obvious behaviors and constraints of authoring bundles.

### First Deploy Creates DRAFT V1

When you deploy an `AiAuthoringBundle` to an org for the first time (if it has never been published), the org creates DRAFT V1. This is your starting state. Subsequent deploys update this DRAFT. When you publish, V1 becomes locked and a new DRAFT is created for future edits.
### The "Naked" AiAuthoringBundle Always Points to the Highest DRAFT

Your local agent directory (without a version suffix) represents the editable working copy in the org. In the org, this "naked" `AiAuthoringBundle` is always linked to the highest DRAFT version. When you deploy, you update this DRAFT. When you publish, a new DRAFT version is created for the next round of edits.
### Version-Suffixed AiAuthoringBundles Are Frozen Snapshots

After you publish, version-suffixed authoring bundles appear in your local project (e.g., `Local_Info_Agent_1`, `Local_Info_Agent_2`). These are org-generated snapshots locked by a `<target>` element in their `bundle-meta.xml`:

```xml
<AiAuthoringBundle xmlns="http://soap.sforce.com/2006/04/metadata">
    <bundleType>AGENT</bundleType>
    <target>Local_Info_Agent.v1</target>
</AiAuthoringBundle>
```

The presence of `<target>` locks this authoring bundle to that specific published version. It is read-only. Modified deploys fail with an error like "content cannot be changed on a locked version." Unmodified deploys succeed as meaningless no-ops.

Use version-suffixed authoring bundles for auditing and diffing version history, NOT for editing. All edits must go through the naked `AiAuthoringBundle`.
### No Pro-Code Way to Create New DRAFT Versions

Once a DRAFT version exists in the org, there is no CLI command to create additional DRAFT versions. The only way to create multiple DRAFTs is via Agentforce Studio's "create new DRAFT version" button on a published version. These additional DRAFTs can then be retrieved with their version number.

In pro-code workflows, you have one DRAFT per agent at any given time. The DRAFT evolves: you deploy, the DRAFT updates. You publish, the DRAFT becomes locked. You deploy again, a new DRAFT is created.
### Deploy-Before-Publish Is Legitimate (For Pro-Code/Low-Code Collaboration)

Deploy-before-publish is the foundation for pro-code/low-code collaboration:

1. Pro-code developer authors Agent Script locally
2. Pro-code developer deploys the authoring bundle (no publish step)
3. Low-code user opens the authoring bundle in Agentforce Studio and refines it
4. Low-code user saves changes
5. Pro-code developer retrieves the updated authoring bundle and continues

Deploy/retrieve are one-way overwrites with no sync warnings. This is by design for cross-tool collaboration.
### NEVER Deploy `AiAuthoringBundle` in Routine Backing-Code Operations

When deploying backing code (Apex, Flows, Prompt Templates), NEVER include agent metadata (`.agent` files or `AiAuthoringBundle` metadata) unless you explicitly intend to update the agent.

Accidental deployment of an outdated authoring bundle will overwrite in-progress work in the org.
### `default_agent_user` Configuration: Immutable and Restricted

The `default_agent_user` field in your Agent Script `config` block must reference a Salesforce user with the "Einstein Agent" license type. Standard Salesforce-licensed users, even System Administrators, will fail at publish time with a misleading error message: "Internal Error, try again later."

This error message does NOT indicate a license issue — it masks the true problem.

To find a valid user, query the org for active users with the Einstein Agent license:

```bash
sf data query --json -q "SELECT Username FROM User WHERE Profile.UserLicense.Name = 'Einstein Agent' AND IsActive = true LIMIT 5"
```

`default_agent_user` can be changed after publish, but only while no published version is activated. Deactivate the agent before changing `default_agent_user`, then republish and reactivate.
### Two Validation Layers: Compile vs. API Validation

The CLI `sf agent validate authoring-bundle` checks syntax and Agent Script compilation only. It does NOT validate `default_agent_user` or backing logic references.

API validation runs during `sf agent publish` and in Agentforce Studio. This is where `default_agent_user` license requirements are checked and backing logic references are fully validated.

The result: A developer can validate successfully and still fail at publish due to invalid `default_agent_user` or missing backing logic.
### Deploy Validates Backing Logic via Invocable Action Registry Lookup

When you deploy an `AiAuthoringBundle`, the deployment process validates that every backing logic reference (Apex class, Flow, Prompt Template) resolves to a registered Invocable Action in the org. The referenced class or flow or prompt must exist.

For Apex classes, the class must have an `@InvocableMethod`-annotated method.

**Critical gap:** Deploy validation does NOT check parameter names, types, return types, or whether the method has the correct number of parameters. Stub classes with `@InvocableMethod` are sufficient to unblock deployment.

This means you can deploy an authoring bundle with completely wrong I/O definitions and not discover the problem until conversation or preview. Parameter mismatches are caught only at runtime.

A minimal stub class with `@InvocableMethod` unblocks pro-code/low-code collaboration, but defers type validation to runtime.
### Server-Side `AiAuthoringBundle` Filename Versioning

When deploying a local authoring bundle (`Local_Info_Agent.agent`), the server uses a version-suffixed filename (`Local_Info_Agent_4.agent`), triggering a CLI warning:

```
"AiAuthoringBundle, Local_Info_Agent_4.agent, returned from org, but not found in the local project"
```

This is not an error — it's normal behavior. It reflects the "naked `AiAuthoringBundle` = highest DRAFT" behavior. The warning is misleading but harmless.
### Post-Publish Workflow Is Seamless

After publishing, your local source remains unchanged. The `bundle-meta.xml` does NOT get `<target>` set automatically. You can immediately continue editing the `.agent` file and deploy again. The platform auto-creates a new DRAFT version on the server.

The intended workflow is: publish → keep editing → deploy (auto-creates new DRAFT).
### Edge Case: Retrieve After Publish Locks the Authoring Bundle

If you explicitly retrieve the authoring bundle after publishing (e.g., `sf project retrieve start --json --metadata AiAuthoringBundle:Local_Info_Agent`), the retrieved `bundle-meta.xml` WILL have `<target>` set, locking the authoring bundle to that published version. Subsequent deploys with content changes fail.

Recovery: Remove `<target>` from `bundle-meta.xml` and deploy. This unlocks the authoring bundle and allows new edits.

This edge case only happens if you retrieve after publish. Normal post-publish workflows (just keep editing and deploying) never trigger this behavior.
---

## 5. Publishing Authoring Bundles

Publishing converts an agent's design (Agent Script in an `AiAuthoringBundle`) into its runtime existence (Bot, BotVersion, GenAiPlannerBundle). It is self-contained and can be done with no prior deploy.

### Why Publishing Is Needed

Deploy alone puts the authoring bundle source into the org but does NOT create the runtime entity graph. A published agent cannot be previewed with `--api-name` until it is activated.

Publishing compiles the `AiAuthoringBundle` to Agent DSL and creates Bot, BotVersion, and GenAiPlannerBundle. After activation, the agent becomes usable for preview and runtime.
### Publish Is Self-Contained

You do NOT need to deploy first. A brand-new authoring bundle can be published directly:

```bash
sf agent generate authoring-bundle --json --no-spec --name "Local Info Agent" --api-name Local_Info_Agent
# Edit Local_Info_Agent.agent ...
sf agent publish authoring-bundle --json --api-name Local_Info_Agent
```

Publish handles the initial deploy, compilation, and entity creation in one step. The simplest pipeline is: generate → edit → validate → publish → activate.
### Command Syntax

```bash
sf agent publish authoring-bundle --json --api-name <Developer_Name>
```

The `--api-name` is the directory name under `aiAuthoringBundles/` (the `developer_name` from your config block).
### What Metadata Gets Created

When you publish, the org creates:

- **Bot** — Top-level container (one per agent)
- **BotVersion** — Versioned instance (e.g., `v1`, `v2`, `v3`)
- **GenAiPlannerBundle** — Compiled agent definition for this version of the agent, with a `localActions/` directory containing topic-scoped action definitions.

Example directory structure after publishing:

```
bots/
  └── Local_Info_Agent/
      ├── Local_Info_Agent.bot-meta.xml
      ├── v1.botVersion-meta.xml
      ├── v2.botVersion-meta.xml
      └── v3.botVersion-meta.xml
genAiPlannerBundles/
  ├── Local_Info_Agent_v1/
  │   ├── localActions/
  │   └── Local_Info_Agent_v1.genAiPlannerBundle
  ├── Local_Info_Agent_v2/
  │   ├── localActions/
  │   └── Local_Info_Agent_v2.genAiPlannerBundle
  └── Local_Info_Agent_v3/
      ├── localActions/
      └── Local_Info_Agent_v3.genAiPlannerBundle
```

These are separate top-level directories. Each publish adds a BotVersion and a version-named GenAiPlannerBundle subdirectory. All are org-generated and read-only.
### Multiple Published Versions Accumulate

Each publish creates a new version. Older versions remain in the org but become inactive. You can have v1, v2, v3, etc. coexisting.

After first publish: `v1.botVersion-meta.xml` and `Local_Info_Agent_v1.genAiPlannerBundle` exist.
After second publish: `v2.botVersion-meta.xml` and `Local_Info_Agent_v2.genAiPlannerBundle` exist. (v1 still exists but is inactive.)

This is version inflation — versions accumulate whether content changed or not (when no existing DRAFT exists on server).
### Gotcha: Publish Response Lacks Version Number

The `sf agent publish authoring-bundle` response does NOT tell you which version number was created. You must retrieve with `AiAuthoringBundle:` (NOT `Agent:`) to see what version was published:

```bash
sf project retrieve start --json --metadata AiAuthoringBundle:Local_Info_Agent
```

Examine the returned `bundle-meta.xml` to see the `<target>` version (e.g., `Local_Info_Agent.v2`).
### The `Agent` Pseudo-Type Retrieves Runtime Metadata Only

Retrieving with `Agent:Local_Info_Agent` returns the runtime entity graph: `Bot`, `BotVersion`, and `GenAiPlannerBundle` metadata. It does not include `AiAuthoringBundle` metadata.

To retrieve the authoring bundle (e.g., to inspect `<target>` after publish), use the `AiAuthoringBundle` metadata type directly:

```bash
sf project retrieve start --json --metadata AiAuthoringBundle:Local_Info_Agent
```
### Troubleshooting Publish Failures

When `sf agent publish authoring-bundle` fails, run these checks in order. Stop at the first failure and fix it before continuing.

#### 1. Validate `default_agent_user`

Read `agent_type` and `default_agent_user` from the `.agent` config block, then validate based on agent type:

**If `agent_type` is `AgentforceEmployeeAgent`:** `default_agent_user` must NOT be present. If it is set, remove the entire line.

**If `agent_type` is `AgentforceServiceAgent`:** `default_agent_user` must be present. Query the org for the specified username:

```bash
sf data query --json -q "SELECT Username, IsActive, Profile.UserLicense.Name FROM User WHERE Username = '<default_agent_user_value>'"
```

- No results → user does not exist. Set a valid username.
- `IsActive` is false → reactivate the user or set a different username.
- `Profile.UserLicense.Name` is not `"Einstein Agent"` → wrong license. Set a user with the Einstein Agent license.

#### 2. Verify all backing logic is deployed

Every `target` in the `.agent` file must resolve to a registered backing logic component in the org. Redeploy all backing logic:

```bash
sf project deploy start --json --metadata ApexClass Flow PromptTemplate
```

If deploy reports unresolved references, identify and deploy the missing components before retrying publish. For Apex-backed actions, the class must have an `@InvocableMethod`-annotated method — a class without the annotation produces the same error as a missing class.

#### 3. Inspect `bundle-meta.xml` for a stale `<target>` lock

Open the authoring bundle's `bundle-meta.xml` and check for a `<target>` element:

```xml
<!-- If this element is present, the bundle is locked -->
<target>Developer_Name.v2</target>
```

Remove the entire `<target>` line, save, and redeploy before publishing again.

#### 4. Deactivate any active version, then republish

```bash
sf agent deactivate --json --api-name <Bot_API_Name>
sf agent publish authoring-bundle --json --api-name <Developer_Name>
```

#### 5. If all checks pass and publish still fails, escalate to the human

State which checks you ran and what each returned.

---

## 6. Activating Published Agents

After publishing, the agent exists but is inactive. Activation makes a published version live for preview, runtime access, and testing.

### Activation Commands

```bash
# Activate a specific published version
sf agent activate --json --api-name <Bot_API_Name>

# Deactivate (take a version offline without deleting it)
sf agent deactivate --json --api-name <Bot_API_Name>
```

The `--api-name` is the Bot's API name (from your Agent Script `config` block's `developer_name`).
### Activation Requirements

Only one published version can be active at a time. Activating a new version automatically deactivates the previous one. Running `sf agent preview start --api-name <Bot_API_Name>` requires the Bot to have an activated version. If no version is activated, attempting to start a preview with `--api-name` fails.
### Agent Test Execution Requires an Activated Agent

Tests run against activated published agents only. If you try to run a test against an unpublished or inactive agent, it fails.
---

## 7. Lifecycle Operations

This section consolidates CLI commands for deploy, retrieve, delete, rename, test execution, and opening in Builder.

### Deploy

Deploy puts the `AiAuthoringBundle` into the org as metadata. It does NOT create runtime entities.

**Deploy action-backing code only:**

```bash
sf project deploy start --json --metadata ApexClass Flow
```

Use `--metadata` to scope routine deploys to backing code. A bare `sf project deploy start` deploys all changed local metadata, including agent metadata.

**Deploy agent metadata (pro-code/low-code collaboration):**

```bash
sf project deploy start --json --metadata AiAuthoringBundle:Local_Info_Agent
```

Explicitly including agent metadata is useful when collaborating with low-code users in Agentforce Studio.
### Retrieve

Retrieve pulls metadata from the org to your local project.

**Retrieve authoring bundle (highest version):**

```bash
sf project retrieve start --json --metadata AiAuthoringBundle:Local_Info_Agent
```

This retrieves the authoring bundle source files (`.agent` and `.bundle-meta.xml`). Use this to see the `<target>` element or to get the latest source from the org.

**Retrieve authoring bundles (all versions):**

```bash
sf project retrieve start --json --metadata "AiAuthoringBundle:Local_Info_Agent_*"
```

The wildcard `*` retrieves every version of an authoring bundle (e.g., `Local_Info_Agent_1`, `Local_Info_Agent_2`). Without the wildcard, only the naked `AiAuthoringBundle` is returned.

Use this pattern to inspect/compare different versions of an authoring bundle.
**Retrieve runtime metadata with the `Agent` pseudo-type:**

```bash
sf project retrieve start --json --metadata Agent:Local_Info_Agent
```

The `Agent` pseudo-type retrieves Bot, BotVersion, GenAiPlannerBundle, and GenAiPlugin — the full runtime entity graph. It does not include `AiAuthoringBundle`. Use the `AiAuthoringBundle` metadata type directly when you need source files.
### Delete

Deletion behavior differs based on whether the agent has been published.

**Delete unpublished authoring bundle:**

```bash
sf project delete source --json --metadata AiAuthoringBundle:Local_Info_Agent
```

This works for DRAFT-only agents that have never been published.

**Published agents cannot be deleted via CLI:**

Published agents cannot be deleted via the Metadata API due to circular dependencies between metadata types. There is no CLI path to delete a published NGA agent. Cleanup requires the Salesforce Setup UI or scratch org expiration.

Use unique names for test agents to avoid collisions.
**Backing Code Deletion Enforcement:**

The org tracks dependencies between `AiAuthoringBundle` versions and their backing Apex classes. Attempting to delete a backing class while any version references it fails with a dependency error.

To delete a backing class:

1. Update the authoring bundle to remove the reference
2. Deploy the updated authoring bundle
3. Delete the backing class
### Rename

Renaming is hazardous due to the metadata hierarchy. The platform creates dependencies between `AiAuthoringBundle` names and published versions.

Do not attempt an in-place rename. Create a new agent with the desired name and migrate content. Document the old agent as deprecated and schedule deletion after a grace period.

### Test Lifecycle

Agent testing requires a test spec (YAML), which gets compiled into `AiEvaluationDefinition` metadata in the org. Test specs are NOT Salesforce metadata — they are local YAML files that the CLI uses as input.

**Test spec location:** `specs/` directory at the SFDX project root (not inside a package directory).

**Create a test spec from the skill template:**

Copy the test spec template from the **agentforce-testing** skill to `specs/<Agent_API_Name>-testSpec.yaml` in the user's SFDX project. Update `name`, `description`, `subjectName`, and `testCases` to match the agent being tested.

Do NOT use `sf agent generate test-spec` to create a new test spec. This command requires interactive input and cannot be used programmatically. It can reverse-engineer a test spec from an existing `AiEvaluationDefinition` when supplied with the `--from-definition` flag:

```bash
sf agent generate test-spec --from-definition force-app/main/default/aiEvaluationDefinitions/Local_Info_Agent_Test.aiEvaluationDefinition-meta.xml --output-file specs/Local_Info_Agent-testSpec.yaml
```

**Create the test in the org:**

```bash
sf agent test create --json --spec specs/Local_Info_Agent-testSpec.yaml --api-name Local_Info_Agent_Test --force-overwrite
```

This compiles the test spec YAML into `AiEvaluationDefinition` metadata and automatically deploys it to the target org. The `--force-overwrite` flag ensures the CLI does not enter interactive mode if an `AiEvaluationDefinition` with the same `--api-name` already exists. Use `--preview` to generate the `AiEvaluationDefinition` locally without deploying to the org.

Iterating on a test spec is a common workflow: edit the YAML, re-run `sf agent test create` with the same `--api-name` and `--force-overwrite`, then run the test again.

A local test spec YAML does NOT mean the test exists in the org. You must run `sf agent test create` before you can run the test.

**Run tests:**

```bash
sf agent test run --json --api-name Local_Info_Agent_Test --wait 5
```

The `--api-name` is the `AiEvaluationDefinition` name (set by `--api-name` during `sf agent test create`). The `--wait 5` flag forces synchronous execution with a 5-minute timeout — the command blocks until the test completes or times out. Without `--wait`, the command returns a job ID immediately and the agent must poll `sf agent test results` for completion. Tests run against activated published agents only.

**Check test results (async fallback):**

```bash
sf agent test results --json --job-id <JOB_ID>
```

Only needed if `--wait` was not used or the wait timed out. Use the job ID from the `sf agent test run` response.
### Open in Builder

These commands launch the user's local browser to Agentforce Studio. Do NOT use `--json` with these commands — JSON mode outputs the target URL but does not open the browser.

**View all authoring bundles:**

```bash
sf org open authoring-bundle
```

Opens Agentforce Studio showing all authoring bundles in the org.

**View a specific published agent:**

```bash
sf org open agent --api-name <Bot_API_Name>
```

Opens the published agent in Agentforce Studio. Only works for published agents. Unpublished (DRAFT-only) authoring bundles must be opened via `sf org open authoring-bundle`.
