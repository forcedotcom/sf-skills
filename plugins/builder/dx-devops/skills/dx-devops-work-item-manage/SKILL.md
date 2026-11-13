---
name: dx-devops-work-item-manage
description: "Use this skill to manage the full lifecycle of DevOps Center work items — list, create, update, commit changes, perform status transitions, and create pull requests. Update fields like subject, description, and status. Commit changes to work item branches, through the DevOps Center commit API or git. Create pull requests for work item branches via DevOps Center API. Invoke when the user wants to track, find, create, or update a work item, commit changes to a work item branch, advance a work item's status through the pipeline, or create a pull request for code review. Consolidates sf devops work-item and review operations. DO NOT TRIGGER for promotion or deployment operations, or conflict detection."
metadata:
  relatedSkills:
    - "dx-devops-promote"
  version: "1.2"
  domains: ["Developer Experience"]
  minApiVersion: "58.0"
  cliTools:
    - tool: ["sf"]
      semver: ">=2.0.0"
    - tool: ["git"]
      semver: ">=2.0.0"
    - tool: ["jq"]
      semver: ">=1.6"
---

# DevOps Center Work Item Management

Manages the complete work item lifecycle in DevOps Center — from creation through status transitions to promotion readiness. Provides headless CLI-driven operations for autonomous release workflows.

## Scope

- **In scope**: List work items, create new work items, commit changes to work item branches, update work item fields (subject, description, status), transition work item status (New → In Progress → Ready to Promote), create pull requests for work item branches
- **Out of scope**: Promotion/deployment, conflict detection, pipeline or project management (separate skills)

---

## Required Inputs

Gather or infer before proceeding:

- **Operation type**: list, create, update, commit, or create-review
- **For list**: project ID (required) — obtain via `sf devops project list --json` if not provided
- **For create**: project ID (required), subject (required), description (optional)
- **For commit**: work item name or ID (required), commit message, and either the files to commit (git path) or the components to commit (API path). Optional: **dev org alias** — the org that holds the changes. When provided, try the DevOps Center commit API first (see step 5); otherwise use git
- **For update**: work item name (e.g., WI-000001) or work item ID (required), fields to update (subject, description, status)
- **For create-review**: work item name (e.g., WI-000001) or work item ID (required). Optional: **dev org alias**. When provided, try the DevOps Center review API first (see step 7); otherwise use `sf devops review create`

Defaults unless specified:
- Output format: `--json` for headless consumption
- Work item identifier: prefer `--work-item-name` (WI-000001) over `--work-item-id` when both are available (names are human-readable)

If the user provides a clear request ("list work items for Project Alpha", "create work item to fix login bug", "move WI-12345 to In Progress", "create PR for WI-12345"), proceed immediately without unnecessary questions.

---

## Workflow

Operations use `sf devops work-item` CLI commands with `--json` output; the API commit path also uses `sf api request rest` and `sf data query`.

### Phase 1 — Identify Operation

1. **Determine the operation type** from user intent:
   - Keywords like "list", "show", "find" → list operation
   - Keywords like "create", "new", "add" → create operation
   - Keywords like "commit", "push", "save changes", "git commit" → commit operation
   - Keywords like "update", "change", "modify", "edit", "move", "transition", "advance", "mark as" → update operation
   - Keywords like "create PR", "pull request", "code review", "review", "open PR" → create-review operation

### Phase 2 — Execute Operation

2. **Verify org authentication** before any operation:
   ```bash
   sf org display --json
   ```
   - If no default org is set or authentication has expired, instruct the user to run:
     ```bash
     sf org login web --set-default --alias <alias>
     ```
   - Verify the authenticated org has DevOps Center enabled by attempting to list projects
   - If the user wants to target a specific org, use `--target-org <alias>` on all subsequent commands
   - For the API commit path, run `sf org display --target-org <alias> --json` for **both** the dev org and the hub org

3. **List work items** — when the user wants to see existing work items:
   ```bash
   sf devops work-item list --project-id <project-id> --json
   ```
   - `--project-id` is required — if the user provides a project name instead of ID, first run `sf devops project list --json` to resolve the name to an ID
   - Verify the command returns status 0 (success)
   - Parse the JSON output: the work items are in the `.result[]` array
   - Each work item has: `name` (e.g., WI-000001), `subject`, `branch`, `environment`, `status`, `description`
   - Present in a readable format showing work item name, subject, status, branch, and environment
   - If `.result[]` is an empty array, confirm "No work items found in project <project-name>."
   - If the user requested filtering by status (e.g., "show work items in Ready to Promote status"), run:
     ```bash
     sf devops work-item list --project-id <id> --json | jq '.result[] | select(.status == "<requested-status>")'
     ```
     Then present the matching work items

4. **Create a work item** — when the user wants to create a new work item:
   ```bash
   sf devops work-item create \
     --project-id <project-id> \
     --subject "<subject>" \
     --description "<description>" \
     --json
   ```
   - `--project-id` is required (obtain from user or via `sf devops project list --json`)
   - `--subject` is required (user-facing title)
   - `--description` is optional (defaults to blank if omitted)
   - Capture the returned work item name (e.g., WI-000001), branch name, and environment from JSON output for future operations
   - Idempotent: if the user attempts to create a duplicate (same subject + project), check via list first and return the existing work item

5. **Execute commit operation** — when operation type is commit. Choose the path first:
   - **API path** — only when the user gave a dev org alias AND the changes are already deployed in that dev org (if unsure, ask: deploy with `sf project deploy start`, or use git). Dev org alias: `commitChanges`, `DevopsRequestInfo`. Hub alias: `sf devops` and `WorkItemComponentList`. DevOps Center retrieves the named components from the dev org and commits them as `DevOps Center <noreply@salesforce.com>`.
   - **Git path** — everything else. If the changes exist only in the dev org, run `sf project retrieve start --target-org <dev-org>` first.

   **API path** (commands, body, error codes and polling in `references/commit-api.md`):
   1. Preflight `GET /connect/devops/doceConnectionType` on the dev org; a failed call (non-zero exit or error body) or `isCore` not `true` means use the git path.
   2. `sf devops project list` → project id, then `sf devops work-item list --project-id <id> --target-org <hub>` → work item id and name. Status must be New, In Progress, In Review or Ready to Promote.
   3. `POST /connect/devops/commitChanges` on the **dev org**; the body is the inner object (no `commitChanges` wrapper).
   4. A failed call, or `status: "ERROR"` with `reqId` = `CODE:message`: surface it and stop.
   5. If the POST `status` is `SUCCESS` (accepted only), poll `DevopsRequestInfo WHERE RequestToken = '<reqId>'` on the dev org every 10 seconds until `Status` is `SUCCESS` or `ERROR` (report `Message`/`ErrorDetails`), 12-minute deadline. Past it the request is stuck; report it and do not retry automatically.
   6. Confirm a new `WorkItemComponentList` exists on the hub before creating a review.

   **Git path:**
   - If the work item is New, first set it to In Progress (step 6); the hub ignores pushes made while it is New
   - Use the work item's `branch` field as the branch
   - Standard git workflow:
     ```bash
     git checkout <branch-name>
     git add <files>
     git commit -m "<commit-message>"
     git push origin <branch-name>
     ```
   - The hub registers the push asynchronously; re-check it before creating a PR

6. **Update work item** — when the user wants to change subject, description, or status:
   ```bash
   sf devops work-item update \
     --work-item-name <WI-name> \
     --subject "<new-subject>" \
     --description "<new-description>" \
     --status "<In Progress|Ready to Promote>" \
     --json
   ```
   - Work item identifier is required: use `--work-item-name <WI-000001>` (preferred) or `--work-item-id <id>`
   - If the user provides a work item by subject instead of name, resolve it to a name first:
     ```bash
     sf devops work-item list --project-id <id> --json | jq -r '.result[] | select(.subject == "<user-provided-subject>") | .name'
     ```
     Then pass the returned name (e.g., WI-000001) to the update command
   - At least one of `--subject`, `--description`, or `--status` must be provided
   - Valid status values: "In Progress" or "Ready to Promote" (exact strings with spaces)
   - Only include flags for fields being updated (omit unchanged fields)
   - Verify the command returns status 0 (success)
   - Parse the JSON response: `.result.name`, `.result.subject`, `.result.status` contain the updated values
   - **For status transitions specifically**: after the command completes, explicitly confirm the new status by checking `.result.status` in the response. If the status field is absent from the update response, re-query the work item via list to verify the status persisted

7. **Create pull request** — when the user wants to create a PR for code review. Choose the path first:
   - **API path** — when the user gave a dev org alias and the `doceConnectionType` preflight (step 5, API path, item 1) succeeds. The call runs on the dev org and DevOps Center creates the PR with its stored VCS credentials.
   - **CLI path** — everything else.

   **API path** (body, errors and idempotency in `references/review-api.md`):
   1. Resolve the work item id and name on the hub (`sf devops work-item list --project-id <id> --target-org <hub>`). The work item must have a committed component list and must not be Nevered.
   2. `POST /connect/devops/createReview` on the **dev org** with `{workItemId, workItemName, workItemLink}`; the body is the inner object (no `createReview` wrapper).
   3. The call is synchronous. Errors return HTTP 200 with `status: "Error"` and `errorMessage` = `CODE:detail`. Surface it using the error table in the reference and stop.
   4. On `Success`, `reviewUrl` is the PR URL. Calling again for the same work item returns the same URL, so a repeat call is safe.
   5. Confirm on the hub that the work item is `IN_REVIEW` and `ReviewRemoteReference` holds the PR number.

   **CLI path:**
   ```bash
   sf devops review create \
     --work-item-name <WI-name> \
     --json
   ```
   - Work item identifier is required: use `--work-item-name <WI-000001>` (preferred) or `--work-item-id <id>`
   - If the user provides a work item by subject instead of name, resolve it to a name first:
     ```bash
     sf devops work-item list --project-id <id> --json | jq -r '.result[] | select(.subject == "<user-provided-subject>") | .name'
     ```
     Then pass the returned name (e.g., WI-000001) to the review create command
   - Creates PR via DevOps Center API using VCS credentials stored in the org
   - No local VCS authentication required — DevOps Center handles GitHub/Bitbucket auth
   - Works with GitHub and Bitbucket
   - Verify the command returns status 0 (success)
   - Parse the JSON response: `.result.pullRequestUrl` contains the PR URL, `.result.status` contains the PR status (typically "open" for newly created PRs), `.result.number` contains the PR number
   - If the command fails with a VCS credentials error, instruct the user to configure VCS credentials in the DevOps Center org (Setup → DevOps Center → VCS Credentials)
   - If the command fails with "PR already exists" error, report that a PR already exists for this work item (idempotent operation)

### Phase 3 — Verify and Report

8. **Verify operation success**:
   - **For list**: confirm the CLI returned status 0, parse the JSON `.result[]` array, and verify it contains work items (or is empty if no matches). If the user specified a project by name, confirm the resolved project ID matches.
   - **For create**: verify the CLI returned status 0 and the JSON output contains `.result.name` (work item ID like WI-000001), `.result.branch` (branch name), and `.result.environment` fields.
   - **For commit (git path)**: verify each git command returned exit code 0. If `git push` succeeds, the commit is saved to the work item branch; the hub registers it asynchronously.
   - **For commit (API path)**: verify the POST `status`, then `DevopsRequestInfo.Status`, are `SUCCESS`, and that a new `WorkItemComponentList` with a `CommitReference` exists on the hub. A new list with an empty `CommitReference` means nothing new was committed; report that, not a clean success.
   - **For update (general fields)**: verify the CLI returned status 0 and compare the returned JSON fields against the user's requested changes. If updating subject, confirm `.result.subject` matches the new value.
   - **For update (status transition)**: verify the CLI returned status 0, then **explicitly confirm the status transition** by checking `.result.status` in the JSON response matches the target status (e.g., "Ready to Promote"). If the response doesn't include the status field, re-run `sf devops work-item list` filtered to this work item and verify the status persisted.
   - **For create-review (CLI path)**: verify the CLI returned status 0 and the JSON output contains `.result.pullRequestUrl` (the PR URL) and `.result.status` (should be "open" or equivalent). If VCS credentials are missing, the CLI returns an error — surface this to the user.
   - **For create-review (API path)**: verify the response `status` is `Success` with a non-empty `reviewUrl`, then that the hub work item is `IN_REVIEW` with `ReviewRemoteReference` set.

9. **Report results**:
   - **List**: present work items in a readable format showing work item name, subject, status, branch, and environment. If filtering by status was requested, show only matching work items.
   - **Create**: return the work item name (e.g., WI-000001), branch name, environment, and confirm "Work item created successfully."
   - **Commit**: git path — confirm which files were staged, the commit SHA (from git output), and "Changes committed and pushed to branch <branch-name>." API path — confirm the `reqId`, components committed and hub `CommitReference` (author is DevOps Center)
   - **Update (general)**: confirm which fields changed with before/after values (e.g., "Subject updated from 'X' to 'Y'").
   - **Status transition**: explicitly state the transition with old → new status (e.g., "Status updated: In Progress → Ready to Promote").
   - **Create-review**: return the PR URL and confirm "Pull request created successfully. Status: open. URL: <url>". API path — report `reviewUrl`, and note when the call returned an existing PR rather than creating one

---

## Rules / Constraints

| Constraint | Rationale |
|-----------|-----------|
| All sf devops commands must use `--json` flag | Structured output is required for headless consumption; human-readable output is unreliable for parsing |
| Work item identifier required for commit, update, and create-review | Use `--work-item-name` (preferred) or `--work-item-id`; obtain from list or prior create |
| Project ID required for list and create | All work items belong to a project; use `sf devops project list --json` if not provided |
| At least one update field required | Update command fails if no `--subject`, `--description`, or `--status` flag is provided |
| Status values must be exact strings | "In Progress" and "Ready to Promote" (with spaces, proper capitalization); other values fail |
| Idempotent create operations | Check for existing work item with same subject + project before creating duplicates |
| Commit before creating a PR | Commit first and confirm a component list exists on the hub before `review create` |
| API commit only sends components already in the dev org | The API retrieves from the dev org, not from local disk; deploy local-only edits first (`sf project deploy start`) or use the git path |
| Check `status` in the commit API response | Errors are returned as HTTP 200 with `status: "ERROR"` |
| Check `status` in the review API response | Errors are returned as HTTP 200 with `status: "Error"` and `errorMessage` as `CODE:detail` |
| PR creation requires VCS credentials in org | DevOps Center API uses stored VCS credentials; no local git auth needed |
| Never use interactive prompts | Skills run in headless environments; all inputs must be via CLI flags |

---

## Gotchas

| Issue | Resolution |
|-------|------------|
| **No default org set** | Run `sf org display --json` first; if it fails, instruct user to run `sf org login web --set-default` |
| **User provides work item by subject, not name** | Resolve via: `sf devops work-item list --project-id <id> --json \| jq -r '.result[] \| select(.subject == "<subject>") \| .name'`; then pass the returned name to the update/create-review command |
| **User provides project by name, not ID** | First run `sf devops project list --json` and filter `.result[]` by `.name` field to find the project ID, then use that ID in the list/create command |
| **Status update response missing status field** | The CLI doesn't always return the status field in the update response; re-run `sf devops work-item list` filtered to this work item and check `.result[0].status` to verify the transition persisted |
| **Work item not found** | User provided invalid work item name/ID; run list command to show available work items |
| **Invalid status value** | Only "In Progress" and "Ready to Promote" are valid (exact strings with spaces); check spelling and capitalization |
| **Project not found** | User provided invalid project ID; run `sf devops project list --json` to show available projects |
| **Duplicate work item subject** | Idempotent create check should catch this; return existing work item name instead of creating duplicate |
| **Commit pushed while work item is New** | The hub ignores external pushes for New work items; set In Progress first and, if already pushed, re-check after the status change |
| **API commit still in progress past the deadline** | Report it as stuck; do not retry automatically (a new request could race it) |
| **Git push fails - no commits or branch not found** | Verify files are staged with `git status` and branch name retrieved from work item via list command |
| **Review API returns `REVIEW_VCS_AUTHENTICATION_FAILED`** | Core maps any "not found" to this code, so a missing branch looks like an auth failure; check the work item and target branches exist as well as the credential |
| **PR creation fails - VCS credentials** | VCS credentials not configured in DevOps Center UI; instruct user to configure in Setup → DevOps Center → VCS Credentials |

---

## Output Expectations

Deliverables vary by operation:

- **List**: JSON array of work items with work item name (WI-######), subject, branch, environment, repository details
- **Create**: Work item name (e.g., WI-000001), ID, branch name, and environment of the newly created work item
- **Commit**: Confirmation of git commit and push success with commit SHA, or for the API path the `reqId`, final request status and `CommitReference`
- **Update**: Confirmation of updated fields (old value → new value for subject/description, or status change)
- **Create-review**: Pull request URL, PR number, and status (API path: `reviewUrl` and hub `IN_REVIEW` confirmation)

Outputs are derived from `sf devops work-item` CLI, `sf devops review create` CLI, the DevOps Center commit and review APIs, and standard git commands.

---

## Verification Checklist

Before reporting results to the user:

### Universal Checks
- [ ] Was org authentication verified with `sf org display --json`?
- [ ] Was the CLI command executed with `--json` flag?
- [ ] Did the CLI return a successful exit code (0)?
- [ ] Is the JSON output parseable and non-empty?
- [ ] If multi-org scenario, was `--target-org` specified on all commands?

### List Operation Checks
- [ ] Was `--project-id` provided?
- [ ] Are work items displayed with work item name, subject, branch, environment?
- [ ] If the list is empty, was this communicated to the user?

### Create Operation Checks
- [ ] Was a work item name (WI-######) and ID returned in the JSON output?
- [ ] Was the branch name returned in the JSON output?
- [ ] Was `--subject` provided and included in the command?
- [ ] Was `--project-id` provided (or obtained via project list)?

### Commit Operation Checks
- [ ] API path: preflight passed, POST `status` checked, `DevopsRequestInfo` polled to `SUCCESS`, new `WorkItemComponentList` with `CommitReference` seen on the hub?
- [ ] Git path: was the work item In Progress, and the branch name retrieved?
- [ ] Git path: did `git add`, `git commit` and `git push` all exit 0?

### Update Operation Checks
- [ ] Was work item identifier provided (name or ID)?
- [ ] Was at least one update field provided (subject, description, or status)?
- [ ] If status was updated, was it a valid value ("In Progress" or "Ready to Promote")?
- [ ] Was the updated work item returned in JSON?

### Create-Review Operation Checks
- [ ] Was work item identifier provided (name or ID)?
- [ ] Was a PR URL returned (`.result.pullRequestUrl` for the CLI, `reviewUrl` for the API)?
- [ ] API path: was the response `status` checked, and was the hub work item confirmed `IN_REVIEW`?
- [ ] Was the PR creation confirmed?

---

## Reference File Index

| File | When to read |
|------|-------------|
| `references/commit-api.md` | When committing through the DevOps Center API: request body, response and error codes, polling, preflight |
| `references/review-api.md` | When creating a review through the DevOps Center API: request body, response and error codes, idempotency, hub confirmation |
| `references/cli-commands.md` | When you need detailed CLI flag documentation, JSON output schemas, or error handling patterns |
| `examples/common-workflows.md` | When the user's request matches a common pattern (bulk updates, reassignment, idempotent creation, sequential transitions) |
