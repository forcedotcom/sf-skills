# DevOps Center Project CLI Commands Reference

Complete reference for `sf devops project` CLI commands with JSON output schemas and common patterns.

## Command Summary

| Command | Purpose | Required Flags | Optional Flags |
|---------|---------|---------------|----------------|
| `sf devops project list` | List all DevOps Center projects | `--target-org` (`-o`) | `--api-version` |
| `sf devops project create` | Create a new project | `--target-org` (`-o`), `--name` (`-n`) | `--description` (`-d`), `--api-version` |
| `sf devops project update` | Update project name, description, or active status | `--target-org` (`-o`), `--project-id` (`-i`), plus at least one of: `--name` (`-n`), `--description` (`-d`), `--is-active` | `--api-version` |

All commands require `--target-org <alias>` (`-o`) unless the `target-org` config var is set, and support `--json` for structured output. `--flags-dir <value>` imports flag values from a directory.

**Org Authentication:**
Before running any DevOps Center commands, verify org authentication:
```bash
sf org display --json
```

If no default org is set or the user wants to target a specific org, add `--target-org <alias>` to all commands.

---

## List Projects

### Basic Usage

```bash
sf devops project list --target-org my-devops-org --json
```

Queries the `DevopsProject` standard object and returns the Id, Name, and Description for each project.

### Example

```bash
# List projects using an org's username
sf devops project list --target-org devops-center@example.com --json
```

### JSON Output Schema

```json
{
  "status": 0,
  "result": {
    "projects": [
      {
        "Id": "1Qg000000000001",
        "Name": "Project Alpha",
        "Description": "Core platform release pipeline"
      },
      {
        "Id": "1Qg000000000002",
        "Name": "Project Beta",
        "Description": null
      }
    ]
  }
}
```

The project records live under `.result.projects[]` (not a bare `.result[]` array) — every `jq` filter in this skill and its scripts reads that path.

### Key Fields

- `Id`: Salesforce record ID for the project (use with `--project-id` in update and downstream skills)
- `Name`: Human-readable project name
- `Description`: Detailed description (may be null/blank)

---

## Create Project

### Required Fields

```bash
sf devops project create \
  --target-org my-devops-org \
  --name "MyApp Release" \
  --json
```

### With Optional Description

```bash
sf devops project create \
  --target-org my-devops-org \
  --name "Platform Update" \
  --description "Platform services update" \
  --json
```

### JSON Output Schema

```json
{
  "status": 0,
  "result": {
    "Id": "1Qg000000000003",
    "Name": "Platform Update",
    "Description": "Platform services update"
  }
}
```

> **Note:** The `create`/`update` single-record `result` shape is representative. The authoritative, verified envelope is `list` (`.result.projects[]` with capitalized `Id`/`Name`/`Description`). To obtain a created/updated project's ID reliably, re-read the list and filter by name rather than depending on the mutation command's own output shape — this is what `scripts/create-project.sh` does.

---

## Update Project

At least one of `--name`, `--description`, or `--is-active` must be provided.

### Update Name

```bash
sf devops project update \
  --target-org my-devops-org \
  --project-id 1Qg000000000001 \
  --name "MyApp Release v2" \
  --json
```

### Update Description

```bash
sf devops project update \
  --target-org my-devops-org \
  --project-id 1Qg000000000001 \
  --description "Updated release description" \
  --json
```

### Activate / Deactivate

```bash
# Deactivate a project
sf devops project update \
  --target-org my-devops-org \
  --project-id 1Qg000000000001 \
  --no-is-active \
  --json

# Activate a project
sf devops project update \
  --target-org my-devops-org \
  --project-id 1Qg000000000001 \
  --is-active \
  --json
```

> **Note:** `--is-active` is a boolean flag. Use `--is-active` to activate or `--no-is-active` to deactivate — never pass a value like `--is-active true`.

### Update Multiple Fields at Once

```bash
sf devops project update \
  --target-org my-devops-org \
  --project-id 1Qg000000000001 \
  --name "Archived App" \
  --description "Archived" \
  --no-is-active \
  --json
```

### JSON Output Schema

```json
{
  "status": 0,
  "result": {
    "Id": "1Qg000000000001",
    "Name": "MyApp Release v2",
    "Description": "Updated release description",
    "IsActive": true
  }
}
```

---

## Error Handling

### Common Error Scenarios

**Project not found (update):**
```json
{
  "status": 1,
  "name": "NOT_FOUND",
  "message": "Project with ID 1Qg000000000999 does not exist or is not accessible",
  "exitCode": 1
}
```

**Missing required field (create):**
```json
{
  "status": 1,
  "name": "RequiredFlagsError",
  "message": "Missing required flag --name",
  "exitCode": 1
}
```

**Missing update field:**
```json
{
  "status": 1,
  "name": "RequiredFlagsError",
  "message": "At least one of --name, --description, or --is-active must be provided",
  "exitCode": 1
}
```

**DevOps Center not enabled / no projects accessible:**
```json
{
  "status": 1,
  "name": "DEVOPS_NOT_ENABLED",
  "message": "DevOps Center is not enabled for this org",
  "exitCode": 1
}
```

**Authentication failure:**
```json
{
  "status": 1,
  "name": "NoOrgFound",
  "message": "No org configuration found for target-org. Run 'sf org login web' to authenticate.",
  "exitCode": 1
}
```

---

## Parsing JSON Output

Every filter reads the authoritative `.result.projects[]` envelope. To resolve a name to an ID or read back a created project's ID, filter the list by name (see the Idempotent Create Pattern below and `scripts/list-projects.sh --resolve`).

### Check for Empty List

```bash
COUNT=$(sf devops project list --target-org my-devops-org --json | jq '.result.projects | length')

if [ "$COUNT" -eq 0 ]; then
  echo "No projects found — create one before setting up work items"
else
  echo "Found $COUNT projects"
fi
```

### List Project IDs and Names

```bash
sf devops project list --target-org my-devops-org --json | \
  jq -r '.result.projects[] | "\(.Id): \(.Name)"'

# Output:
# 1Qg000000000001: Project Alpha
# 1Qg000000000002: Project Beta
```

---

## Idempotent Create Pattern

To avoid duplicate projects, check for an existing project with the same name before creating:

```bash
NAME="MyApp Release"

# Check if a project with this name exists
EXISTING_ID=$(sf devops project list --target-org my-devops-org --json | \
  jq -r ".result.projects[] | select(.Name == \"$NAME\") | .Id" | head -n1)

if [ -n "$EXISTING_ID" ]; then
  echo "Project already exists: $EXISTING_ID"
else
  # Create new project, then read the ID back from the list
  sf devops project create --target-org my-devops-org --name "$NAME" --json >/dev/null
  NEW_ID=$(sf devops project list --target-org my-devops-org --json | \
    jq -r ".result.projects[] | select(.Name == \"$NAME\") | .Id" | head -n1)
  echo "Created new project: $NEW_ID"
fi
```

---

## Authentication Requirements

All `sf devops project` commands require an authenticated org (`sf org login web` or JWT), DevOps Center enabled (DOCe provisioned), and permission to manage projects. Verify with `sf org display --target-org <alias> --json`; if auth fails, run `sf org login web --set-default --alias <alias>`.
