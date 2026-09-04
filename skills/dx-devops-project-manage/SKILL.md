---
name: dx-devops-project-manage
description: "Use this skill to list, view, or manage DevOps Center projects in a Salesforce org — show all projects, create a new project, or update an existing project's name, description, or active status. Invoke it to run sf devops project list whenever the user wants to show, see, view, display, or list available projects, check which or how many DevOps Center projects exist, or look up a project ID — even a plain listing request should use this skill rather than a raw tool or a direct answer. Also invoke to create a project, set up a new deployment pipeline foundation, initialize DevOps Center for a new feature, update project settings like name and description, or activate/deactivate (archive) a project. Consolidates sf devops project list/create/update operations. DO NOT TRIGGER for work item, pipeline, promotion, or conflict operations — those are separate skills."
metadata:
  version: "1.0"
  domains: ["Developer Experience"]
  minApiVersion: "58.0"
  relatedSkills:
    - "dx-devops-pipeline-manage"
    - "dx-devops-promote"
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

# DevOps Center Project Management

Manages the complete DevOps Center project lifecycle — from listing existing projects through creation to updating project settings. Provides headless CLI-driven operations for autonomous release workflows.

## Scope

- **In scope**: List DevOps Center projects, create a new project, update project fields (name, description), resolve a project name to its ID for downstream skills
- **Out of scope**: Work item lifecycle, pipeline creation/configuration, promotion/deployment, conflict detection (separate skills)

---

## Required Inputs

Gather or infer before proceeding:

- **Operation type**: list, create, or update
- **Target org**: `--target-org <alias>` is required on every command unless the `target-org` config var is already set (`sf config get target-org`)
- **For list**: no other required input (lists all projects in the org); optional name filter
- **For create**: project name (required), description (optional)
- **For update**: project ID (required), fields to update — at least one of name, description, or active status

Defaults unless specified:
- Output format: `--json` for headless consumption
- Project identifier: when the user gives a project name for update, resolve it to a project ID first via `sf devops project list --target-org <alias> --json`

If the user provides a clear request ("list all projects", "create a project called Release Alpha", "rename project X to Y"), proceed immediately without unnecessary questions.

---

## Workflow

All operations use `sf devops project` CLI commands with `--json` output for structured consumption.

### Phase 1 — Identify Operation

1. **Determine the operation type** from user intent:
   - Keywords like "list", "show", "find", "what projects", "get project ID" → list operation
   - Keywords like "create", "new", "set up", "initialize" → create operation
   - Keywords like "update", "change", "rename", "modify", "edit" → update operation

### Phase 2 — Execute Operation

2. **Verify org authentication** before any operation, checking the same org the operation will target:
   ```bash
   # When a specific org is requested, check that alias (do NOT rely on the default org):
   sf org display --target-org <alias> --json
   # Only when no alias is supplied and a default org is expected:
   sf org display --json
   ```
   - If the requested org is not authenticated or authentication has expired, instruct the user to run:
     ```bash
     sf org login web --alias <alias>
     ```
   - Verify the authenticated org has DevOps Center enabled by attempting to list projects
   - `--target-org <alias>` is **required** on every `sf devops project` command unless the `target-org` config var is set (check with `sf config get target-org`). Add `--target-org <alias>` to all commands when targeting a specific org — a targeted operation must never require or reset the default org

   > Deterministic project-list parsing, empty-list handling, name→ID resolution, idempotent create, and update are handled by the scripts in `scripts/` — each script exits non-zero with an actionable message on failure. Pass the org alias as the trailing/`--target-org` argument when the `target-org` config var is not set; omit it to use the default org. The scripts read the authoritative `.result.projects[]` list envelope.

3. **List projects** — when the user wants to see existing projects or resolve a project name to an ID:
   - **Use the `sf devops project list` CLI (via `scripts/list-projects.sh`) — do NOT substitute an MCP/metadata tool** (e.g. a `list_devops_center_projects` tool). The `sf devops project` CLI is the only supported, verifiable path; other tools bypass this skill and will not satisfy the operation.
   - To list all projects: run `scripts/list-projects.sh [target-org]` and report any errors it returns. Output is tab-separated `Id  Name  Description`, one project per line; a single line `NO_PROJECTS` means none exist.
   - To resolve a single project name to its ID: run `scripts/list-projects.sh --resolve "<project-name>" [target-org]` and report any errors it returns (exit 3 = no such project).

4. **Create a project** — when the user wants to create a new project:
   - Run `scripts/create-project.sh "<name>" "<description>" [target-org]` and report any errors it returns. The description argument is optional.
   - The script is idempotent: it prints `EXISTING <id>` if a project with that name already exists, or `CREATED <id>` after creating and verifying a new one. Capture the returned ID for downstream operations (work items, pipelines).

5. **Update a project** — when the user wants to change name, description, or active status:
   - Run `scripts/update-project.sh --project (<id>|name:<name>) [--name "<new-name>"] [--description "<new-desc>"] [--is-active|--no-is-active] [--target-org <alias>]` and report any errors it returns.
   - Pass `--project name:<name>` to update by name (the script resolves it to an ID) or `--project <id>` for a known ID.
   - At least one of `--name`, `--description`, or `--is-active`/`--no-is-active` must be provided (the script enforces this). Use `--is-active` to activate or `--no-is-active` to deactivate.
   - The script prints `UPDATED <id>` on success.

### Phase 3 — Report

6. **Report results** (the scripts already verified success deterministically; report their output to the user):
   - **List**: present projects in a readable format showing project ID, name, and description. If `NO_PROJECTS` was returned, state that no DevOps Center projects were found. If resolving a name to an ID, return the ID.
   - **Create**: return the project ID and confirm — "Project created successfully. Use this project ID for work items and pipelines: <id>." If the script returned `EXISTING <id>`, tell the user the project already existed and return that ID.
   - **Update**: confirm which fields were changed (e.g., "Project name updated to 'Platform Core'", or "Project deactivated").

---

## Rules / Constraints

| Constraint | Rationale |
|-----------|-----------|
| Always use the `sf devops project` CLI | List/create/update MUST go through `sf devops project` (via the `scripts/`), never a `salesforce_dx` MCP tool or metadata query — those bypass this skill and fail the operation |
| All sf devops commands must use `--json` flag | Structured output is required for headless consumption; human-readable output is unreliable for parsing |
| `--target-org` required unless config var set | Every `sf devops project` command requires `--target-org <alias>` unless the `target-org` config var is already set |
| Project ID required for update | Use `--project-id` (`-i`); resolve from a name via `sf devops project list --target-org <alias> --json` when the user gives a name |
| `--name` required for create | A project cannot be created without a name |
| At least one update field required | Update command fails if none of `--name`, `--description`, or `--is-active` is provided |
| Use `--is-active` / `--no-is-active` for activation | Activate with `--is-active`, deactivate with `--no-is-active`; do not pass a value |
| Idempotent create operations | Check for an existing project with the same name before creating a duplicate |
| Never use interactive prompts | Skills run in headless environments; all inputs must be via CLI flags |
| A project is a prerequisite for work items and pipelines | Downstream skills (work-item-manage, pipeline-manage) need the project ID this skill returns |

---

## Gotchas

| Issue | Resolution |
|-------|------------|
| **No default org set** | Run `sf org display --json` first; if it fails, instruct the user to run `sf org login web --set-default` |
| **User provides project by name, not ID (update)** | Resolve via `scripts/list-projects.sh --resolve "<name>" [target-org]`, or pass `--project name:<name>` to `scripts/update-project.sh` (it resolves internally) |
| **Tempted to use an MCP listing tool** | A `salesforce_dx` MCP tool (e.g. `list_devops_center_projects`) may be available, but using it bypasses this skill and the `sf devops project list` CLI — always list via `scripts/list-projects.sh` |
| **DevOps Center not enabled** | If `sf devops project list` errors, the org lacks DevOps Center; instruct the user to provision it in Setup → DevOps Center |
| **Project not found (update)** | User provided an invalid project ID; run `scripts/list-projects.sh [target-org]` to show available projects |
| **Wrong list envelope** | `project list` returns records under `.result.projects[]` (capitalized `Id`/`Name`/`Description`), NOT `.result[]`; the scripts already use the correct path |
| **Duplicate project name** | Idempotent create check should catch this; return the existing project ID instead of creating a duplicate |
| **Empty project list** | No projects exist yet; guide the user to create one before setting up work items or pipelines |
| **Missing update field** | Update fails if none of `--name`, `--description`, or `--is-active` is provided; ensure at least one is passed |
| **No default org and no `--target-org`** | Commands fail with a NoOrgFound / missing target-org error; set `--target-org <alias>` or `sf config set target-org <alias>` |
| **Activate/deactivate passes a value** | `--is-active` is a boolean flag — use `--is-active` or `--no-is-active`, never `--is-active true` |

---

## Output Expectations

Deliverables vary by operation:

- **List**: tab-separated `Id  Name  Description` lines (or `NO_PROJECTS`) from `scripts/list-projects.sh`
- **Create**: `EXISTING <id>` or `CREATED <id>` from `scripts/create-project.sh`
- **Update**: `UPDATED <id>` from `scripts/update-project.sh`

Outputs are derived from the `sf devops project` CLI via the `scripts/` helpers, which read the authoritative `.result.projects[]` list envelope.

---

## Verification Checklist

Before reporting results to the user:

### Universal Checks
- [ ] Was org authentication verified with `sf org display --json`?
- [ ] Was `--target-org <alias>` supplied to the script (or the `target-org` config var confirmed set)?
- [ ] Did the invoked script exit 0? (Non-zero exit means the operation failed — report the script's error message.)

### List Operation Checks
- [ ] Are projects displayed with project ID, name, and description?
- [ ] If the script returned `NO_PROJECTS`, was this communicated to the user?
- [ ] If resolving a name to an ID, was the ID returned (or "not found" surfaced on exit 3)?

### Create Operation Checks
- [ ] Did the script return `CREATED <id>` or `EXISTING <id>`, and was the ID reported?

### Update Operation Checks
- [ ] Was the project identified by `--project <id>` or `--project name:<name>`?
- [ ] Was at least one update field provided (name, description, or `--is-active`/`--no-is-active`)?
- [ ] Did the script return `UPDATED <id>`?

---

## Cross-Skill Integration

| When | Delegate to |
|------|-------------|
| User wants to create, list, or update work items in a project | `dx-devops-work-item-manage` (pass the project ID from this skill) |
| User wants to create or configure a pipeline for a project | `dx-devops-pipeline-manage` |
| User wants to promote or deploy changes | `dx-devops-promote` |

This skill typically runs **first** in a DevOps Center workflow — the project ID it returns is the entry point for work item and pipeline skills.

---

## Reference File Index

| File | When to read / run |
|------|-------------|
| `scripts/list-projects.sh` | Workflow step 3 — list all projects or resolve a project name to an ID (`--resolve`); handles the empty-list case |
| `scripts/create-project.sh` | Workflow step 4 — idempotently create a project and verify it via re-read |
| `scripts/update-project.sh` | Workflow step 5 — update name/description/active status by ID or name |
| `references/cli-commands.md` | When you need detailed CLI flag documentation, JSON output schemas, or error handling patterns |
| `examples/common-workflows.md` | When the user's request matches a common pattern (name resolution, idempotent creation, project setup as a workflow entry point) |
