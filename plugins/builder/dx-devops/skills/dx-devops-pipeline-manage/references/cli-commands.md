# DevOps Center Pipeline CLI Commands Reference

Command reference for `sf devops pipeline` and `sf devops stage` — flags and JSON output schemas. For jq parsing snippets, error handling, the idempotent check-before-create pattern, and auth setup, see `references/parsing-patterns.md`.

## Command Summary

| Command | Purpose | Required Flags |
|---------|---------|---------------|
| `sf devops pipeline list` | List all pipelines in the org | `--target-org` |
| `sf devops pipeline get` | Get one pipeline's stages, repos, and connected projects | `--target-org`, `--pipeline-id` |
| `sf devops pipeline create` | Create a pipeline linked to a Git repo | `--target-org`, `--name`, `--repo` |
| `sf devops pipeline update` | Activate / deactivate / rename a pipeline | `--target-org`, `--pipeline-id` |
| `sf devops pipeline stage add` | Insert an empty stage before another stage | `--target-org`, `--pipeline-id`, `--name`, `--next-stage-id` |
| `sf devops pipeline stage update` | Rename a stage | `--target-org`, `--pipeline-id`, `--stage-id`, `--name` |
| `sf devops pipeline stage delete` | Delete a stage (auto-relinks neighbors) | `--target-org`, `--pipeline-id`, `--stage-id` |
| `sf devops pipeline project add` | Attach a project to a pipeline | `--target-org`, `--pipeline-id`, `--project-id` |
| `sf devops pipeline project delete` | Detach a project from a pipeline | `--target-org`, `--pipeline-id`, `--project-id` |
| `sf devops stage environment add` | Add a Salesforce environment to a stage | `--target-org`, `--pipeline-id`, `--stage-id`, `--environment-name`, `--org-type` |
| `sf devops stage environment delete` | Remove an environment (inactive pipeline only) | `--target-org`, `--pipeline-id`, `--environment-id` |

All commands support `--json` for structured output and `--api-version <value>` to override the API version. `--target-org` is not required if the `target-org` config variable is already set.

---

## List Pipelines

```bash
sf devops pipeline list --target-org my-devops-org --json
```

Returns all pipelines in the org as **SObject records** under `.result.pipelines[]`, with capitalized fields (`Id`, `Name`, `Description`, `IsActive`). This summary view does **not** include stages or connected projects — use `pipeline get` for those.

### JSON Output Schema

```json
{
  "status": 0,
  "result": {
    "pipelines": [
      {
        "attributes": { "type": "DevopsPipeline", "url": "/services/data/v67.0/sobjects/DevopsPipeline/1PJWt0000007NsjOAE" },
        "Id": "1PJWt0000007NsjOAE",
        "Name": "Release Pipeline",
        "Description": null,
        "IsActive": false
      }
    ]
  }
}
```

Use `.Id` with `--pipeline-id` in follow-on commands.

---

## Get Pipeline Details

```bash
sf devops pipeline get --target-org my-devops-org --pipeline-id 0XB000000000001 --json
```

Returns a single pipeline's full detail — its stages, the repo/branch per stage, and connected projects. **This is how you discover stage IDs** needed by `stage add` (`--next-stage-id`), `stage update`/`stage delete` (`--stage-id`), and `stage environment add` (`--stage-id`). Unlike `pipeline list`, `get` uses lowercase camelCase fields (`id`, `name`, `stages`, `connectedProjects`).

### JSON Output Schema

```json
{
  "status": 0,
  "result": {
    "id": "1PJWt000000HLUfOAO",
    "name": "Release Pipeline",
    "description": null,
    "isActive": true,
    "stages": [
      {
        "id": "1QVWt000000G3huOAC",
        "name": "Staging",
        "nextStageId": "1QVWt000000G3htOAC",
        "branchName": "staging",
        "repositoryName": "my-new-rep",
        "repositoryOwner": "ad-shreya",
        "environment": { "id": "1QeWt0000000i13KAA", "name": "cli-stage" }
      },
      {
        "id": "1QVWt000000G3htOAC",
        "name": "Production",
        "nextStageId": null,
        "branchName": "main",
        "repositoryName": "my-new-rep",
        "repositoryOwner": "ad-shreya",
        "environment": { "id": "1QeWt0000000jDFKAY", "name": "Prod 2" }
      }
    ],
    "connectedProjects": [ { "id": "1QgWt0000000rabKAA", "name": "Release Project 1" } ],
    "warnings": []
  }
}
```

### Stage Ordering — Linked List, Not an Array Index

Stages form a **linked list** via `nextStageId`, not a numeric `order` field:
- Each stage's `nextStageId` points to the stage that follows it in the promotion chain.
- The **terminal stage** (last, typically Production) has `nextStageId: null`.
- To insert before a given stage with `stage add`, pass that stage's `id` as `--next-stage-id`.

See `references/parsing-patterns.md` for jq snippets that list stage names/IDs, find the terminal stage, and resolve a stage ID by name.

---

## Create Pipeline

A pipeline must be linked to a Git repository at creation.

```bash
# Existing repo — pass the full URL, nothing else
sf devops pipeline create --target-org my-devops-org --name "Release Pipeline" \
  --repo https://github.com/myorg/myrepo --json

# New GitHub repo — requires --repo-owner
sf devops pipeline create --target-org my-devops-org --name "Release Pipeline" \
  --repo my-new-repo --create-repo --repo-type github --repo-owner myorg --json
```

For a **new Bitbucket repo**, swap the provider flags: `--repo-type bitbucket --bitbucket-workspace myworkspace` (plus optional `--bitbucket-project-key PROJ`) in place of `--repo-type github --repo-owner`. Add `--description "<text>"` to any scenario for a pipeline description.

### Required Flags by Scenario

The correct flag set depends on whether the repo already exists and, for new repos, on the provider. Always required: `--name` and `--repo`. `--description` is optional in every scenario.

| Scenario | Required flags | Must NOT include |
|----------|---------------|------------------|
| **Existing repo** (GitHub or Bitbucket) | `--name`, `--repo <url>` | `--create-repo`, `--repo-type`, `--repo-owner`, `--bitbucket-*` |
| **New GitHub repo** | `--name`, `--repo <name>`, `--create-repo`, `--repo-type github`, `--repo-owner <org-or-user>` | `--bitbucket-workspace`, `--bitbucket-project-key` |
| **New Bitbucket repo** | `--name`, `--repo <name>`, `--create-repo`, `--repo-type bitbucket`, `--bitbucket-workspace <workspace>` | `--repo-owner` |

Per-flag detail:

| Flag | Applies to | Notes |
|------|-----------|-------|
| `--name` / `-n` | all | Pipeline name (required) |
| `--repo` / `-r` | all | Existing repo URL, or a repo name when used with `--create-repo` (required) |
| `--description` / `-d` | all | Pipeline description (optional) |
| `--create-repo` | new repo only | Create the repo if it doesn't exist |
| `--repo-type` | new repo only | `github` or `bitbucket` (required when creating a repo) |
| `--repo-owner` | **GitHub** new repo | Organization or user that owns the repo (required for GitHub create) |
| `--bitbucket-workspace` | **Bitbucket** new repo | Workspace that owns the repo (required for Bitbucket create) |
| `--bitbucket-project-key` | Bitbucket new repo | Optional Bitbucket project key |
| `--stage` / `-s` | all | Name of a pipeline stage, in promotion order. Repeat once per stage. Defaults to Integration, UAT, Staging, Production |

> **Provider mismatch fails:** pairing `--repo-owner` with `--repo-type bitbucket`, or `--bitbucket-workspace` with `--repo-type github`, is rejected. Match the provider flag to `--repo-type`.

### Custom Stage Names at Create Time

By default a new pipeline seeds the stage chain **Integration → UAT → Staging → Production**. To seed a different chain, repeat `--stage` once per stage in promotion order:

```bash
sf devops pipeline create \
  --target-org my-devops-org \
  --name "Release Pipeline" \
  --repo https://github.com/myorg/myrepo \
  --stage Dev --stage QA --stage Prod \
  --json
```

Seeding stages at create time avoids a separate round of `stage add` / `stage update` calls afterward.

After creating, resolve the new pipeline's ID by name from `sf devops pipeline list --json` (see `references/parsing-patterns.md`) — this avoids depending on the exact shape of the create response. A new pipeline always starts with at least one stage (the default chain, or your `--stage` list) — run `sf devops pipeline get` to see the seeded stages, then add or rename stages if you need to adjust the chain.

---

## Update Pipeline (Activate / Deactivate / Rename)

```bash
# Activate — requires at least one stage
sf devops pipeline update --pipeline-id 0XB000000000001 --activate --json

# Deactivate
sf devops pipeline update --pipeline-id 0XB000000000001 --deactivate --json

# Rename
sf devops pipeline update --pipeline-id 0XB000000000001 --name "My Pipeline" --json

# Deactivate and rename in one step
sf devops pipeline update --pipeline-id 0XB000000000001 --deactivate --name "My Pipeline" --json
```

| Flag | Notes |
|------|-------|
| `--pipeline-id` | Required — ID of the pipeline to update |
| `--activate` | Activate the pipeline. Mutually exclusive with `--deactivate` |
| `--deactivate` | Deactivate the pipeline. Mutually exclusive with `--activate` |
| `--name` / `-n` | New name for the pipeline. Can be combined with `--deactivate` |

- A pipeline must have **at least one stage** before it can be activated.
- `--activate` and `--deactivate` cannot be used together; `--deactivate` and `--name` may be combined in one command.
- **You can't modify pipeline stages after you activate and promote changes through it.** Finish all stage/environment configuration before activating.

---

## Add a Stage

Inserts an **empty** stage (no branch or environment) immediately before `--next-stage-id`. Configure its environment separately afterward.

```bash
# Add a Development stage before Integration
sf devops pipeline stage add \
  --target-org my-devops-org \
  --pipeline-id 0XB000000000001 \
  --name "Development" \
  --next-stage-id 0Xc000000000001 \
  --json
```

Get the `--next-stage-id` from `sf devops pipeline get`. The new stage is always inserted **immediately before** the anchor stage you pass as `--next-stage-id` — there is no append-to-end flag. To place a stage at a given point in the chain, choose the anchor that should follow it (e.g. anchor to the terminal stage to insert the new stage just before it).

---

## Rename / Delete a Stage

```bash
# Rename a stage
sf devops pipeline stage update \
  --pipeline-id 0XB000000000001 \
  --stage-id 0Xc000000000002 \
  --name "QA" \
  --json

# Delete a stage — the predecessor auto-relinks to the successor so the chain stays intact
sf devops pipeline stage delete \
  --pipeline-id 0XB000000000001 \
  --stage-id 0Xc000000000002 \
  --json
```

---

## Add an Environment to a Stage

```bash
sf devops stage environment add \
  --target-org my-devops-org \
  --pipeline-id 0XB000000000001 \
  --stage-id 0Xp000000000001 \
  --environment-name Production_Org \
  --org-type Production \
  --json
```

| Flag | Required | Notes |
|------|----------|-------|
| `--pipeline-id` | Required | Pipeline containing the stage |
| `--stage-id` | Required | Target stage (from `pipeline get`) |
| `--environment-name` / `-e` | Required | Environment name |
| `--org-type` | Required | Exactly `Production` or `Sandbox` |
| `--no-browser` | Optional | Don't auto-open a browser for OAuth; prints the redirect URL instead |

> **Headless caveat:** This command triggers an OAuth flow and opens a browser by default. In CI or headless runs, pass `--no-browser` and complete authentication via the printed redirect URL.

---

## Delete an Environment from a Stage

The pipeline must be **inactive** before you can delete an environment.

```bash
sf devops stage environment delete \
  --target-org my-devops-org \
  --pipeline-id 0XB000000000001 \
  --environment-id 0Xe000000000001 \
  --json
```

`--pipeline-id` is used to verify the pipeline is inactive before deleting.

---

## Attach / Detach a Project

A project can be attached to **only one pipeline**.

```bash
# Attach
sf devops pipeline project add \
  --target-org my-devops-org \
  --pipeline-id 0XB000000000001 \
  --project-id 0Hn000000000001 \
  --json

# Detach — deletes only the junction record; the project itself is not deleted
sf devops pipeline project delete \
  --target-org my-devops-org \
  --pipeline-id 0XB000000000001 \
  --project-id 0Hn000000000001 \
  --json
```

Resolve a project ID from its name via `sf devops project list --json` — see `references/parsing-patterns.md` for the jq snippet.
