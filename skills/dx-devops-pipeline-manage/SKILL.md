---
name: dx-devops-pipeline-manage
description: "Use this skill to manage the full lifecycle of a DevOps Center pipeline — list all pipelines, get a single pipeline's details, create a new pipeline linked to a Git repository, add or remove stages, rename a stage, add or remove Salesforce environments on stages, attach or detach projects, and activate or deactivate the pipeline. Invoke when the user wants to set up a release pipeline, wire promotion stages across integration, UAT, staging, and production orgs, connect environments to stages, attach a project, or activate a continuous delivery pipeline. Uses sf devops pipeline and sf devops stage commands with --json output. DO NOT TRIGGER for work-item lifecycle, promotion or deployment execution, conflict detection, or standalone project creation (separate skills)."
metadata:
  version: "1.0"
  minApiVersion: "58.0"
  relatedSkills:
    - "dx-devops-work-item-manage"
  accessCheck:
    - type: "orgPref"
      value: "ALMDevopsCorePref"
    - type: "userPerm"
      value: "UserHasDevOpsCore"
  cliTools:
    - tool: ["jq"]
      semver: ">=1.6"
    - tool: ["sf"]
      semver: ">=2.0.0"
---

# DevOps Center Pipeline Management

Manages the complete pipeline lifecycle in DevOps Center — from creation against a repository, through stage and environment configuration and project attachment, to activation of a ready-to-promote release pipeline. Provides headless CLI-driven operations for autonomous release workflows.

## Scope

- **In scope**: List pipelines, get pipeline details, create a pipeline (linked to an existing or new Git repo), add/delete/rename stages, add/delete Salesforce environments on stages, attach/detach projects, and activate/deactivate/rename the pipeline
- **Out of scope**: Work-item lifecycle, promotion/deployment execution, conflict detection, standalone project creation (separate skills)

---

## Required Inputs

Gather or infer before proceeding:

- **Operation type**: list, get, create, add-stage, delete-stage, rename-stage, add-environment, delete-environment, attach-project, detach-project, activate, or deactivate
- **For get / any stage or environment op**: pipeline ID (required) — obtain via `sf devops pipeline list --json`
- **For create**: pipeline name (required) and a Git repo (`--repo`, required). Repo flags differ by scenario:
  - **Existing repo (GitHub or Bitbucket)**: only `--repo <url>` — do **not** pass `--repo-type`/`--create-repo`
  - **New GitHub repo**: `--repo <name> --create-repo --repo-type github --repo-owner <org-or-user>`
  - **New Bitbucket repo**: `--repo <name> --create-repo --repo-type bitbucket --bitbucket-workspace <workspace>` (`--bitbucket-project-key <key>` optional)
  - Description (`--description`) optional in all cases
- **For add-stage**: pipeline ID, new stage name, and `--next-stage-id` (the stage the new one precedes) — get stage IDs via `sf devops pipeline get`
- **For add-environment**: pipeline ID, stage ID, environment name, and `--org-type` (Production or Sandbox)
- **For attach/detach-project**: pipeline ID and project ID
- **For activate/deactivate/rename**: pipeline ID

Defaults unless specified:
- Output format: `--json` for headless consumption
- Target org: use `--target-org <alias>` if not relying on the default org

If the user gives a clear request ("create a pipeline on repo myorg/myrepo", "add a UAT stage before Production", "activate pipeline 0XB..."), proceed immediately without unnecessary questions.

---

## Workflow

All operations use `sf devops pipeline` and `sf devops stage` CLI commands with `--json` output for structured consumption. Pipeline IDs and stage IDs are the primary identifiers — resolve them via `list` and `get` before mutating.

### Phase 1 — Identify Operation

1. **Determine the operation type** from user intent:
   - "list", "show all pipelines" → list; "details of pipeline", "show stages" → get
   - "create", "set up", "new pipeline" → create
   - "add stage", "insert stage" → add-stage; "rename stage" → rename-stage; "remove/delete stage" → delete-stage
   - "connect environment", "add org to stage" → add-environment; "remove environment" → delete-environment
   - "attach project", "connect project" → attach-project; "detach project" → detach-project
   - "activate", "turn on"; "deactivate", "turn off"; "rename pipeline" → lifecycle update

### Phase 2 — Execute Operation

2. **Verify org authentication** before any operation:
   ```bash
   sf org display --json
   ```
   - If no default org is set or auth has expired, instruct the user to run `sf org login web --set-default --alias <alias>`
   - Confirm the org has DevOps Center enabled by running `sf devops pipeline list --json`
   - Add `--target-org <alias>` to every command when targeting a specific org

3. **Inspect pipelines**:
   ```bash
   sf devops pipeline list --json                              # all pipelines in the org
   sf devops pipeline get --pipeline-id <pipeline-id> --json   # one pipeline, with stages/repos/projects
   ```
   - `list` returns SObject records under `.result.pipelines[]` with capitalized fields (`.Id`, `.Name`, `.IsActive`) — it does **not** include stages or connected projects
   - `get` returns a single pipeline under `.result` with camelCase fields (`.id`, `.name`, `.stages[]`, `.connectedProjects[]`); each stage has `.id`, `.name`, `.nextStageId`, `.branchName`, and `.environment.{id,name}`. **Stages are a linked list** — order is defined by `nextStageId`, and the terminal stage has `nextStageId: null`. Use `get` to discover **stage IDs** before any stage or environment operation

4. **Create a pipeline** — the pipeline must be linked to a Git repository. `--name` and `--repo` are always required; the remaining flags depend on the repo scenario:
   ```bash
   # Existing repo (GitHub or Bitbucket) — pass the full repo URL, nothing else
   sf devops pipeline create --name "<pipeline-name>" --repo <repo-url> --json

   # New GitHub repo — requires --repo-owner
   sf devops pipeline create --name "<pipeline-name>" --repo <repo-name> \
     --create-repo --repo-type github --repo-owner <org-or-user> --json

   # New Bitbucket repo — requires --bitbucket-workspace (--bitbucket-project-key optional)
   sf devops pipeline create --name "<pipeline-name>" --repo <repo-name> \
     --create-repo --repo-type bitbucket --bitbucket-workspace <workspace> \
     --bitbucket-project-key <key> --json

   # Custom stage chain (any scenario) — repeat --stage in promotion order
   sf devops pipeline create --name "<pipeline-name>" --repo <repo-url> \
     --stage Dev --stage QA --stage Prod --json
   ```
   - Provider-specific required flags: **GitHub new repo** → `--repo-owner`; **Bitbucket new repo** → `--bitbucket-workspace`. Omitting the provider's required flag fails the create
   - Do **not** pass `--repo-type`/`--create-repo` for an existing repo — supply only the repo URL via `--repo`
   - **Custom stages at create time**: a new pipeline seeds the default stage chain **Integration → UAT → Staging → Production**. To seed different stages, repeat `-s/--stage` once per stage **in promotion order** — e.g. `--stage Dev --stage QA --stage Prod`. This avoids adding/renaming stages afterward
   - Add `--description "<text>"` optionally in any scenario
   - Capture the returned pipeline ID for subsequent stage/environment/project/activation steps
   - **Idempotency**: the CLI does not dedupe. Before creating, run `sf devops pipeline list --json` and check for a pipeline with the same name/repo; return the existing one if found. See `references/parsing-patterns.md` for the check-before-create snippet

5. **Configure stages** — a stage is added relative to an existing stage, then bound to an environment. **Read `references/cli-commands.md`** for full flag details before multi-stage work:
   ```bash
   # Insert an empty stage BEFORE an existing stage (get the next-stage-id from `pipeline get`)
   sf devops pipeline stage add --pipeline-id <id> --name "<stage-name>" --next-stage-id <stage-id> --json
   # Rename a stage
   sf devops pipeline stage update --pipeline-id <id> --stage-id <stage-id> --name "<new-name>" --json
   # Delete a stage (predecessor auto-relinks to successor)
   sf devops pipeline stage delete --pipeline-id <id> --stage-id <stage-id> --json
   ```
   - `stage add` inserts an **empty** stage (no branch/environment) before `--next-stage-id`; configure its environment separately
   - Build the promotion chain by inserting each new stage before the stage that should follow it

6. **Bind environments to stages** — attach a Salesforce org to a stage:
   ```bash
   # Validate the org-type against the fixed enum BEFORE calling the CLI
   bash scripts/validate-org-type.sh "<Production|Sandbox>"   # exits non-zero on an invalid value
   sf devops stage environment add --pipeline-id <id> --stage-id <stage-id> \
     --environment-name "<env-name>" --org-type <Production|Sandbox> --json
   # Remove an environment (pipeline must be inactive)
   sf devops stage environment delete --pipeline-id <id> --environment-id <env-id> --json
   ```
   - `--org-type` must be exactly `Production` or `Sandbox` — run `scripts/validate-org-type.sh <value>` first and only proceed on exit 0
   - **Headless caveat**: `stage environment add` triggers an OAuth browser flow. In headless/CI runs pass `--no-browser` — the CLI prints a redirect URL for manual authentication

7. **Attach / detach a project** — a project can be attached to only one pipeline:
   ```bash
   sf devops pipeline project add --pipeline-id <id> --project-id <project-id> --json
   sf devops pipeline project delete --pipeline-id <id> --project-id <project-id> --json
   ```
   - If the user names a project instead of providing its ID, resolve it via `sf devops project list --json` (see `references/parsing-patterns.md`)

8. **Activate / deactivate / rename the pipeline**:
   ```bash
   # Before activating, confirm the deterministic ≥1-stage prerequisite
   bash scripts/check-activation-ready.sh <id> [target-org]   # exits non-zero if stage-less
   sf devops pipeline update --pipeline-id <id> --activate --json             # activate
   sf devops pipeline update --pipeline-id <id> --deactivate --json           # deactivate
   sf devops pipeline update --pipeline-id <id> --name "<new-name>" --json    # rename
   ```
   - Before `--activate`, run `scripts/check-activation-ready.sh <id>` and only proceed on exit 0 — it fails with an actionable message when the pipeline has no stages
   - **Stages cannot be modified after the pipeline is activated and changes are promoted through it** — finish stage/environment configuration before activating
   - `--activate` and `--deactivate` are mutually exclusive; `--deactivate` and `--name` may be combined in one command

### Phase 3 — Verify and Report

9. **Verify operation success** — use `scripts/verify-operation.sh`, which performs the deterministic JSON-status and post-state field checks and exits non-zero with an actionable message on mismatch:
   ```bash
   # Assert a captured command's JSON status is 0 (pipe the CLI output in)
   sf devops pipeline update --pipeline-id <id> --activate --json | bash scripts/verify-operation.sh status -
   # Assert post-state after activate / stage / project ops
   bash scripts/verify-operation.sh active      <id> true         [target-org]   # isActive == true
   bash scripts/verify-operation.sh has-stage   <id> "<stage>"    [target-org]   # stage present in chain
   bash scripts/verify-operation.sh has-project <id> "<project>"  [target-org]   # project connected
   ```
   - **Create**: confirm the pipeline appears in `sf devops pipeline list --json` by `.Name` and capture its `.Id`
   - **Stage / environment / project changes**: verify with the `has-stage` / `has-project` modes above (they read `sf devops pipeline get` and check `.result.stages[]` / `.result.connectedProjects[]`)
   - **Activate**: verify with the `active <id> true` mode

10. **Report results**:
    - **List**: pipeline name, ID, and active state per pipeline (no stages — that's what `get` is for)
    - **Get**: pipeline name, ID, active state, stage chain (each stage's name → environment → branch, ordered via `nextStageId`), connected projects
    - **Create**: pipeline ID, name, and linked repo (or "existing pipeline returned" on idempotent match)
    - **Stage / environment / project op**: the resulting stage chain with each stage's environment, in promotion order
    - **Lifecycle**: the new active state and/or name

### Verification Checklist (gate before reporting success)

Confirm the items for the operation you performed. Do **not** report success until every applicable box holds:

- [ ] Every `sf devops` command was run with `--json` and returned `status: 0` (`scripts/verify-operation.sh status -`)
- [ ] **Create**: the new pipeline appears in `sf devops pipeline list --json` by name, and (for a new repo) the provider-specific flags were supplied (`--repo-owner` for GitHub, `--bitbucket-workspace` for Bitbucket)
- [ ] **Add-stage / add-environment**: the stage exists in the chain and `--org-type` passed `scripts/validate-org-type.sh` (`scripts/verify-operation.sh has-stage ...`)
- [ ] **Attach-project**: the project shows in `.result.connectedProjects[]` (`scripts/verify-operation.sh has-project ...`)
- [ ] **Activate**: `scripts/check-activation-ready.sh` passed beforehand and `.result.isActive` is now `true` (`scripts/verify-operation.sh active <id> true`)
- [ ] **Delete-environment**: the pipeline was inactive before the delete

---

## Rules / Constraints

| Constraint | Rationale |
|-----------|-----------|
| All sf devops commands must use `--json` flag | Structured output is required for headless consumption; human-readable output is unreliable for parsing |
| A pipeline requires a Git repo at create time | `sf devops pipeline create` requires `--name` and `--repo`; for an existing repo pass only the URL, for a new repo add `--create-repo` and `--repo-type` |
| New-repo create needs provider-specific flags | GitHub requires `--repo-owner`; Bitbucket requires `--bitbucket-workspace` (`--bitbucket-project-key` optional). The wrong provider's flags fail the command |
| Pipeline ID required for get, update, and all stage/environment/project ops | These commands identify the pipeline only by `--pipeline-id`; obtain it via `sf devops pipeline list` |
| Stage IDs come from `pipeline get` | `stage add` (`--next-stage-id`), `stage update`/`delete` (`--stage-id`), and `stage environment add` (`--stage-id`) all need stage IDs |
| `stage add` inserts an empty stage before `--next-stage-id` | Stages carry no environment until one is added; build the chain by anchoring to the following stage |
| `--org-type` must be exactly `Production` or `Sandbox` | The flag is a fixed enum; other values fail |
| Pipeline must have ≥1 stage before activation | `sf devops pipeline update --activate` rejects a stage-less pipeline |
| Do not modify stages after activate + promote | DevOps Center locks stage structure once changes have been promoted through an active pipeline |
| Environment delete requires an inactive pipeline | `stage environment delete` only succeeds while the pipeline is inactive |
| A project attaches to only one pipeline | `pipeline project add` fails if the project is already attached elsewhere; detach first |
| Idempotent create via check-before-create | The CLI does not dedupe; list existing pipelines and return the match instead of erroring |
| Prefer `--no-browser` in headless runs | `stage environment add` opens an OAuth browser flow; `--no-browser` prints a redirect URL for CI |

---

## Gotchas

| Issue | Resolution |
|-------|------------|
| **No default org set** | Run `sf org display --json` first; if it fails, instruct user to run `sf org login web --set-default` |
| **Create fails — missing repo** | `--repo` is required; pass an existing repo URL, or `--create-repo` + `--repo-type` for a new repo |
| **New-repo create fails — missing provider flag** | GitHub new repo needs `--repo-owner`; Bitbucket new repo needs `--bitbucket-workspace`. Don't mix providers' flags (`--repo-owner` with `bitbucket`, or `--bitbucket-workspace` with `github`) |
| **`stage add` fails — no next-stage-id** | `--next-stage-id` is required; run `sf devops pipeline get --pipeline-id <id> --json` to find the stage IDs and pick the one the new stage should precede |
| **Environment add hangs in CI** | The OAuth browser flow blocks headless runs; add `--no-browser` and complete auth via the printed redirect URL |
| **Activation rejected** | The pipeline needs at least one stage; add a stage (and its environment) before `--activate` |
| **Cannot modify stages** | The pipeline is active and has promoted changes; stage structure is locked — configuration must complete before activation |
| **Environment delete fails** | The pipeline is active; deactivate with `pipeline update --deactivate` before deleting the environment |
| **Project already attached** | A project attaches to only one pipeline; detach from the other pipeline first via `pipeline project delete` |
| **Pipeline / stage / project not found** | The ID is invalid; run `sf devops pipeline list --json`, `sf devops pipeline get --json`, or `sf devops project list --json` to find valid IDs |

---

## Output Expectations

Deliverables vary by operation:

- **List**: pipelines with ID, name, and active state (no stages/projects in the list view)
- **Get**: a pipeline with ID, name, active state, its stage chain (each with environment and branch, ordered via `nextStageId`), and connected projects
- **Create**: pipeline ID, name, and linked repository (or the pre-existing pipeline on idempotent match)
- **Stage op**: the updated ordered stage chain
- **Environment op**: the stage with its bound environment (name, org-type)
- **Project op**: confirmation of attach/detach
- **Lifecycle**: the new active state and/or pipeline name

Outputs are derived from `sf devops pipeline` and `sf devops stage` CLI commands.

---

## Cross-Skill Integration

| Delegate to | When |
|-------------|------|
| `dx-devops-work-item-manage` | The user wants to create or advance work items once the pipeline is active |

If a project the user wants to attach can't be found, resolve or list existing projects with `sf devops project list --json` (see `references/parsing-patterns.md`) rather than delegating — project creation is out of scope for this skill.

---

## Reference File Index

| File | When to read |
|------|-------------|
| `references/cli-commands.md` | When you need detailed CLI flag documentation and JSON output schemas for each `sf devops pipeline` / `sf devops stage` command |
| `references/parsing-patterns.md` | When you need jq snippets to parse the JSON (stage chains, pipeline/project ID resolution), error-handling reference, the check-before-create idempotent pattern, or auth requirements |
| `examples/common-workflows.md` | When the user's request matches a common pattern (end-to-end pipeline setup, inserting a stage, binding an environment, attaching a project, activation) |
| `scripts/validate-org-type.sh` | Run before `stage environment add` to validate `--org-type` against the `Production`/`Sandbox` enum |
| `scripts/check-activation-ready.sh` | Run before `pipeline update --activate` to confirm the pipeline has ≥1 stage |
| `scripts/verify-operation.sh` | Run in Phase 3 to assert a command's JSON status and post-state fields (`status` / `active` / `has-stage` / `has-project`) |
