# CLI Flags Reference

Complete reference for the scratch org snapshot commands: `sf org create snapshot`, `sf org get snapshot`, `sf org list snapshot`, and `sf org delete snapshot`.

> **Global flags (all four commands):** `--json` (format output as JSON — ALWAYS use this) and `--flags-dir <value>` (import flag values from a directory).
>
> **Dev Hub flag (all four commands):** `--target-dev-hub` / `-v` — username or alias of the Dev Hub org. Required unless the `target-dev-hub` config variable is already set. There is **no** `--target-org` flag; snapshots are a Dev Hub feature.
>
> **API version (all four commands):** `--api-version <value>` — override the API version used for API requests.

---

## `sf org create snapshot`

Create a point-in-time copy (metadata and data) of a scratch org.

### Required Flags

| Flag | Alias | Description | Example |
|------|-------|-------------|---------|
| `--source-org` | `-o` | ID or locally authenticated username/alias of the scratch org to snapshot. Aliases/usernames auto-resolve to the org ID (IDs start with `00D`). | `--source-org my-scratch` |
| `--name` | `-n` | Unique name of the snapshot. **Max 15 characters** — longer values fail with `STRING_TOO_LONG` (verified live). | `--name Dependencies` |
| `--target-dev-hub` | `-v` | Dev Hub username or alias. Not required if the `target-dev-hub` config is set. | `--target-dev-hub DevHub` |

### Optional Flags

| Flag | Alias | Description | Example |
|------|-------|-------------|---------|
| `--description` | `-d` | Description of the snapshot. Document the contents; include a VCS tag or commit ID. | `--description "Contains PackageA v1.1.0"` |
| `--api-version` | | Override the API version. | `--api-version 66.0` |

### Usage Patterns

```bash
# Basic snapshot creation (by alias)
sf org create snapshot --source-org my-scratch --name MySnapshot --json

# With a description
sf org create snapshot --source-org my-scratch --name MySnapshot \
  --description "Baseline with Package v1.2.0" --json

# Using the source org ID instead of an alias
sf org create snapshot --source-org 00D5g00000001XyEAI --name MySnapshot --json

# Specify the Dev Hub explicitly
sf org create snapshot --source-org my-scratch --name NightlyBranch \
  --target-dev-hub NightlyDevHub --json
```

**Legacy alias:** `sf force org snapshot create`

> **Asynchronous:** creation returns a record whose `Status` is `InProgress` (verified live — not `New` or `Pending`). Poll `sf org get snapshot` until `Status` is `Active` before using the snapshot.

---

## `sf org get snapshot`

Get details about a snapshot — including its creation status.

### Required Flags

| Flag | Alias | Description | Example |
|------|-------|-------------|---------|
| `--snapshot` | `-s` | Name or ID of the snapshot to retrieve. IDs start with `0Oo`. | `--snapshot Dependencies` |
| `--target-dev-hub` | `-v` | Dev Hub username or alias (or default config). | `--target-dev-hub DevHub` |

### Usage Patterns

```bash
# Get details by name
sf org get snapshot --snapshot Dependencies --json

# Get details by ID
sf org get snapshot --snapshot 0Oo5g00000001ABCAA --json

# Against a specific Dev Hub
sf org get snapshot --snapshot Dependencies --target-dev-hub SnapshotDevHub --json
```

**Legacy alias:** `sf force org snapshot get`

---

## `sf org list snapshot`

List the scratch org snapshots in a Dev Hub.

### Flags

Takes only the Dev Hub flag (`--target-dev-hub` / `-v`) plus the global flags. As an admin you see all snapshots in the Dev Hub; as a user you see only your own unless granted View All.

> **No server-side filters** (verified live). `sf org list snapshot` returns every snapshot (subject to your visibility) with no flags to filter by status, date, or expiry. Filter client-side from the `--json` output.

### Usage Patterns

```bash
# List snapshots in the default Dev Hub
sf org list snapshot --json

# List snapshots in a specific Dev Hub
sf org list snapshot --target-dev-hub SnapshotDevHub --json

# Save the list to a file
sf org list snapshot --json > tmp/MySnapshotList.json
```

**Legacy alias:** `sf force org snapshot list`

### Filtering for snapshots expiring soon

Each snapshot record carries an `ExpirationDate` (`YYYY-MM-DD`, populated once the snapshot is `Active`; `null` while `InProgress` — verified live). To list snapshots expiring within N days, pipe the JSON through `jq`:

```bash
# Snapshots expiring within DAYS days, soonest first (negative = already expired).
DAYS=30
sf org list snapshot --target-dev-hub SnapshotDevHub --json \
  | jq --argjson days "$DAYS" -r '
      (now | floor) as $now
      | [ .result[]
          | select(.ExpirationDate != null)
          | . + { daysUntilExpiry: ((((.ExpirationDate + "T00:00:00Z") | fromdateiso8601) - $now) / 86400 | floor) }
          | select(.daysUntilExpiry <= $days) ]
      | sort_by(.daysUntilExpiry)
      | if length == 0 then "No snapshots expiring within \($days) day(s)."
        else (.[] | "\(.SnapshotName)\t[\(.Status)]\texpires \(.ExpirationDate)\tin \(.daysUntilExpiry)d") end'
```

Requires `jq` (>= 1.6) on the PATH alongside `sf`.

---

## `sf org delete snapshot`

Delete a scratch org snapshot.

### Required Flags

| Flag | Alias | Description | Example |
|------|-------|-------------|---------|
| `--snapshot` | `-s` | Name or ID of the snapshot to delete. IDs start with `0Oo`. | `--snapshot BaseSnapshot` |
| `--target-dev-hub` | `-v` | Dev Hub username or alias (or default config). | `--target-dev-hub DevHub` |

### Optional Flags

| Flag | Alias | Description | Example |
|------|-------|-------------|---------|
| `--no-prompt` | `-p` | Don't prompt to confirm the deletion (use in scripts/CI). | `--no-prompt` |
| `--api-version` | | Override the API version. | `--api-version 66.0` |

### Usage Patterns

```bash
# Delete by ID (prompts for confirmation)
sf org delete snapshot --snapshot 0Oo5g00000001ABCAA --json

# Delete by name without prompting (scripts/CI)
sf org delete snapshot --snapshot BaseSnapshot --no-prompt --json

# Against a specific Dev Hub
sf org delete snapshot --snapshot BaseSnapshot --target-dev-hub SnapshotDevHub --json
```

**Legacy alias:** `sf force org snapshot delete`

> Without `--no-prompt`, the command asks for confirmation. Declining returns with no result and performs no deletion. Dev Hub admins can delete any snapshot; users can delete only their own unless granted Modify All.
>
> **Bulk-delete guardrail:** there is no single command to delete multiple snapshots — each `sf org delete snapshot` call removes one snapshot. Before deleting multiple/all snapshots, or any delete with `--no-prompt`, first run `sf org list snapshot --json`, echo the resolved target names back to the user, and obtain explicit confirmation.

---

## Important Notes

- **No update command exists anywhere in the CLI** (verified — `sf org --help` under the `org` topic lists only `create/get/list/delete` for `snapshot`). To rename, redescribe, or change expiration, delete and recreate.
- **Dev Hub must have Scratch Org Snapshots enabled** — otherwise commands fail with a feature-not-enabled error.
- **Snapshot name limit (create)** — `--name` is capped at **15 characters** (verified live); a longer value fails with `STRING_TOO_LONG`. Names must also be unique within the Dev Hub.
- **Source-org auto-resolution (create)** — `--source-org` accepts an org ID (`00D...`), username, or alias; aliases/usernames resolve to the org ID locally.
- **Snapshot identifier (get/delete)** — `--snapshot` accepts the snapshot name or its ID (`0Oo...`).
- **Asynchronous creation** — `create` does not wait for the snapshot to finish; use `sf org get snapshot` to poll `Status` until it is `Active`.
- **Returned fields** — snapshot records expose `Id`, `SnapshotName`, `Description`, `Status`, `SourceOrg`, `CreatedDate`, `LastModifiedDate`, `ExpirationDate`, and `Error` (populated only when `Status` is `Error`), plus the standard sobject `attributes` wrapper on `get`/`list`.
