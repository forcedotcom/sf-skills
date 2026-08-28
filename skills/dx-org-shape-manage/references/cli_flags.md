# CLI Flags Reference

Complete reference for the org shape commands: `sf org create shape`, `sf org list shape`, and `sf org delete shape`.

> **Global flags (all three commands):** `--json` (format output as JSON — ALWAYS use this) and `--flags-dir <value>` (import flag values from a directory).

---

## `sf org create shape`

Capture an org shape (baseline configuration) from the specified source org.

### Required Flags

| Flag | Alias | Description | Example |
|------|-------|-------------|---------|
| `--target-org` | `-o` | Username or alias of the **source org** to capture the shape from. Not required if the `target-org` configuration variable is already set. | `--target-org SourceOrg` |

> **Note:** `--target-org` here is the org being *shaped* (the source org), NOT a Dev Hub. There is no `--target-dev-hub` flag on this command.

> **API version:** This skill does not set `--api-version`. If the user needs a shape created against a specific API version, tell them to run `sf org create shape` manually via the CLI with that flag.

### Flags That Do NOT Exist (common mistakes)

Unlike `sf org create snapshot`, the shape command has **no** way to name or describe the shape:

| Not a flag | Why |
|------------|-----|
| `--name` / `-n` | A shape is identified by the source org's ID, not a custom name |
| `--description` / `-d` | Shapes have no description; use `sf org list shape` to identify them |
| `--target-dev-hub` / `-v` | The command runs against the source org, not a Dev Hub |

### Usage Patterns

```bash
# Basic shape creation (by alias)
sf org create shape --target-org SourceOrg --json

# Using the default target org
sf org create shape --json

# By username
sf org create shape --target-org test-org@example.com --json
```

**Legacy alias:** `sf force org shape create`

---

## `sf org list shape`

List all org shapes you've created. Output includes the alias, username, and ID of the source org, plus the shape's status.

### Flags

This command takes only the global flags (`--json`, `--flags-dir`). It does **not** take `--target-org` — it lists shapes across all your authenticated orgs.

### Usage Patterns

```bash
# List all org shapes you've created
sf org list shape --json

# List all org shapes and write the output to a file
sf org list shape --json > tmp/MyOrgShapeList.json
```

**Legacy alias:** `sf force org shape list`

---

## Listing Inactive Shapes (`sf data query`)

`sf org list shape` only surfaces `Active`/`InProgress` shapes and takes no `--target-org` — there is no flag to see `Inactive` shapes or to scope to one source org. To see a source org's full shape history, including shapes superseded by a later `sf org create shape` run, query `ShapeRepresentation` directly:

```bash
# All shapes (any status) for a specific source org
sf data query --target-org SourceOrg --query "SELECT Id, Name, Status, CreatedDate, LastModifiedDate FROM ShapeRepresentation" --json

# Only Inactive shapes for a specific source org
sf data query --target-org SourceOrg --query "SELECT Id, Name, Status, CreatedDate, LastModifiedDate FROM ShapeRepresentation WHERE Status = 'Inactive'" --json
```

`ShapeRepresentation` has no `SourceOrgId`, `username`, or `alias` field — the query result contains only `Id`, `Name`, `Status`, `CreatedDate`, `LastModifiedDate` (plus whatever other fields you select, e.g. `Description`, `CreatedById`, `LastModifiedById`). Requires the same `ShapeRepresentation` CRUD access as `sf org create/delete shape`.

---

## `sf org delete shape`

Delete **all** org shapes for a target (source) org.

### Required Flags

| Flag | Alias | Description | Example |
|------|-------|-------------|---------|
| `--target-org` | `-o` | Username or alias of the source org whose shapes to delete. Not required if the `target-org` configuration variable is already set. | `--target-org SourceOrg` |

### Optional Flags

| Flag | Alias | Description | Example |
|------|-------|-------------|---------|
| `--no-prompt` | `-p` | Don't prompt for confirmation (use in scripts/CI) | `--no-prompt` |

> **API version:** This skill does not set `--api-version`. If the user needs a specific API version, tell them to run `sf org delete shape` manually via the CLI with that flag.

### Usage Patterns

```bash
# Delete all org shapes for the source org (prompts for confirmation)
sf org delete shape --target-org SourceOrg --json

# Delete without prompting (scripts/CI)
sf org delete shape --target-org SourceOrg --no-prompt --json
```

**Legacy alias:** `sf force org shape delete`

### Exit Codes

| Code | Meaning |
|------|---------|
| `0` | All deletions succeeded |
| `1` | All deletions failed |
| `68` | Partial failure — some shapes deleted, others failed (see the `failures` array in the JSON) |

> Without `--no-prompt`, the command prompts "Delete shape for `<username>`?". Declining returns with no result and performs no deletion.

---

## Important Notes

- **Source org must be enabled for org shape** — enable it via **Setup → Scratch Orgs → Enable Org Shape for Scratch Orgs** in the source org. Otherwise create/delete fail with a no-access error (`ShapeRepresentationNoAccess`), or a generic `UNKNOWN_EXCEPTION` (with a support ErrorId) if the org is only partially enabled.
- **ShapeRepresentation access** — the running user must have CRUD access to the `ShapeRepresentation` object, or create fails with `NoCrudAccessCreateShape`.
- **Find the shape's org ID** — run `sf org list shape` to view created shapes, their status (`Active`, `InProgress`), and the source org IDs.
- **One active shape per source org** — creating a new shape marks any previous shape for that org inactive; `sf org delete shape` removes all shapes for the org.
