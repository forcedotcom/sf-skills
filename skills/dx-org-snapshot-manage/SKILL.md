---
name: dx-org-snapshot-manage
description: "ALWAYS USE THIS SKILL to create, check the status of, list, or delete scratch org snapshots. A snapshot is a point-in-time copy of a scratch org's metadata AND data, referenced by name in the `snapshot` field of a scratch org definition file. Use when the user asks to create/take a snapshot, check a snapshot's status or creation progress, list/show/view existing snapshots (including filtering for snapshots expiring soon), or delete/remove a snapshot. Requires a Dev Hub with Scratch Org Snapshots enabled. DO NOT TRIGGER for creating org shapes (use dx-org-shape-manage) or for creating scratch orgs, including from an existing snapshot via `--snapshot` (use dx-org-manage)."
metadata:
  version: "1.0"
  domains: ["Developer Experience"]
  minApiVersion: "60.0"
  relatedSkills:
    - "dx-org-manage"
    - "dx-org-shape-manage"
  cliTools:
    - tool: ["sf"]
      semver: ">=2.0.0"
    - tool: ["jq"]
      semver: ">=1.6"
  accessCheck:
    - type: "orgPref"
      value: "ScratchOrgSnapshotPref"
---

# dx-org-snapshot-manage

Coordinates the full lifecycle of Salesforce scratch org snapshots — **create**, **get** (status), **list**, and **delete** — via `sf org create snapshot`, `sf org get snapshot`, `sf org list snapshot`, and `sf org delete snapshot`. A snapshot is a point-in-time copy of a scratch org (its metadata **and** data) that you reference by name in a scratch org definition file to spin up new orgs from saved state.

---

## Tool Restrictions

**Use ONLY the Bash tool** to execute the `sf org ... snapshot` commands. Do NOT use MCP tools — ignore them completely.

**Output artifacts for eval/testing:** ALWAYS write the command's complete JSON response to a file when an output directory is available. Do NOT ask the user what file to write — this skill defines the filenames. After executing each command: (1) if the user specified an output path, write there immediately; (2) otherwise run `[ -d force-app/main/adk-eval-output/ ] && echo 'force-app/main/adk-eval-output'` to detect the eval directory; (3) write the command's full, unmodified JSON response to `<output-dir>/<filename>` using these filenames: `create-snapshot-result.json`, `get-snapshot-result.json`, `list-snapshots-result.json`, or `delete-snapshot-result.json`. This is the generated output — write it without asking. (4) If no output directory can be found by either check, include the command's complete, unmodified JSON response verbatim (e.g. in a fenced code block) in your final reply instead of skipping the artifact.

---

## Relationship to Other Skills

This skill owns the **full snapshot lifecycle** — create, get status, list, and delete. It does not create scratch orgs.

- **Any snapshot operation** (create, status, list, delete, expiry check) → this skill.
- **Create a scratch org, including from an existing snapshot** (`--snapshot <name>`) → `dx-org-manage`.
- **Org shapes** (baseline config without data, `sf org create/list/delete shape`) → `dx-org-shape-manage`. Shapes and snapshots are different artifacts with different commands — see the comparison below.

| | Snapshot (this skill) | Org Shape (`dx-org-shape-manage`) |
|--|----------|-----------|
| Captures | Full point-in-time copy: metadata **and** data | Baseline config only: features, limits, edition, Metadata API settings |
| Commands | `sf org create/get/list/delete snapshot` | `sf org create/list/delete shape` |
| Referenced via | `snapshot` (name) in the scratch def file | `sourceOrg` (org ID) in the scratch def file |
| Prerequisite | **Dev Hub** has Scratch Org Snapshots enabled | **Source org** has Org Shape for Scratch Orgs enabled |
| Operates against | A **Dev Hub** (`--target-dev-hub`) | The **source org** (`--target-org`) |

---

## Scope

- **In scope**: Creating (`sf org create snapshot`), getting status (`sf org get snapshot`), listing (`sf org list snapshot`), and deleting (`sf org delete snapshot`) scratch org snapshots
- **Out of scope**: Creating org shapes (`dx-org-shape-manage`), creating scratch orgs — including from a snapshot (`dx-org-manage`)

---

## Required Inputs

Infer from the user's request:

- **Operation**: create, get, list, or delete (see Workflow step 1)
- **Dev Hub**: Username or alias of the Dev Hub that owns the snapshots. Passed via `--target-dev-hub` (`-v`); optional if the `target-dev-hub` config variable is set. **All four commands** operate against a Dev Hub, never `--target-org`.
- **Source org** (create only): Scratch org ID (starts with `00D`), username, or alias to snapshot. Passed via `--source-org` (`-o`).
- **Snapshot name** (create only): A unique name for the snapshot, **max 15 characters**. Passed via `--name` (`-n`).
- **Snapshot name or ID** (get & delete only): Name, or ID (starts with `0Oo`), of the snapshot. Passed via `--snapshot` (`-s`).
- **Description** (create, optional): Documents snapshot contents.
- **Expiry threshold in days** (expiring-soon listing only): There is no CLI flag for this — it's a client-side filter on `ExpirationDate` (see Command Patterns).

---

## Workflow

1. **Identify the operation** and match it to the command pattern below.
2. **Resolve the Dev Hub** — if `--target-dev-hub` isn't provided, check the default with `sf config get target-dev-hub`. Never fabricate a placeholder Dev Hub name (e.g. `my-dev-hub`) — an unresolved hub is a hard stop; advise `sf org login web --set-default-dev-hub` instead.
3. **For create, confirm the source org and snapshot name** — the source must be a scratch org; the name must be unique in the Dev Hub and ≤15 characters.
4. **Execute via Bash tool** with the `--json` flag.
5. **Report the result** (see Output Expectations and the example files).

### Command Patterns

| Operation | User intent | Execute via Bash tool |
|-----------|-------------|------------------------|
| **Create** | Create snapshot with name only | `sf org create snapshot --source-org <orgId\|alias> --name <SnapshotName> --json` |
| **Create** | Create snapshot with description | `sf org create snapshot --source-org <orgId\|alias> --name <SnapshotName> --description "<desc>" --json` |
| **Create** | Specify Dev Hub explicitly | `sf org create snapshot --source-org <orgId\|alias> --name <SnapshotName> --target-dev-hub <devHub> --json` |
| **Get** | Check a snapshot's status/details | `sf org get snapshot --snapshot <name\|0Oo...> --json` |
| **List** | List all snapshots in the Dev Hub | `sf org list snapshot --json` |
| **List** | List snapshots expiring within N days | `sf org list snapshot --json` → filter on `ExpirationDate` with `jq` (see `references/cli_flags.md`) |
| **Delete** | Delete a snapshot (with confirm prompt) | `sf org delete snapshot --snapshot <name\|0Oo...> --json` |
| **Delete** | Delete without prompting (scripts/CI) | `sf org delete snapshot --snapshot <name\|0Oo...> --no-prompt --json` |
| **Delete** | Delete multiple/all snapshots | **First** `sf org list snapshot --json`, confirm the target names with the user, **then** run `sf org delete snapshot --snapshot <name>` once per snapshot — there is no bulk-delete command |

**Snapshot creation is asynchronous.** `create` returns a record whose `Status` is typically `InProgress` initially, with `ExpirationDate` still `null`. Poll with `sf org get snapshot` until `Status` is `Active` (verified live against a real Dev Hub — see `examples/create_success_output.json` vs `examples/get_output.json`) before using the snapshot to create scratch orgs.

---

## Rules / Constraints

| Constraint | Rationale |
|-----------|-----------|
| Always use `--json` flag | Provides structured output for reliable parsing and error handling |
| All commands operate against a **Dev Hub** | `--target-dev-hub` (not `--target-org`) — optional only if the `target-dev-hub` config is set |
| Dev Hub must have **Scratch Org Snapshots** enabled | Otherwise commands fail — contact Salesforce to enable it |
| Source org (create) must be a **scratch org** | Snapshots only work with scratch orgs |
| Snapshot names must be **unique** in the Dev Hub, **≤15 characters** | Longer names fail with `STRING_TOO_LONG` (verified live) |
| Creation is **asynchronous** | `create` may return before the snapshot is `Active` — poll with `sf org get snapshot` |
| **There is no update/rename/extend-expiration command.** | Verified — the CLI (and the underlying platform object) exposes only create/get/list/delete. To change a snapshot's name, description, or expiration, delete it and create a new one. |
| **There is no bulk-delete command.** | Each `sf org delete snapshot` call removes exactly one snapshot |
| **`sf org list snapshot` has no server-side filters** | Returns every visible snapshot; filter status/expiry client-side (e.g. with `jq`) |
| `delete` prompts for confirmation by default | Use `--no-prompt` (`-p`) for non-interactive/CI use |
| **Bulk/`--no-prompt` deletes require an explicit confirmation step** | Before deleting multiple or all snapshots — or any delete with `--no-prompt` — first run `sf org list snapshot --json`, echo the resolved target names back to the user, and get explicit confirmation. Deletion is irreversible. |
| Permissions affect visibility/deletion | Users see/delete only their own snapshots unless a Dev Hub admin grants View All / Modify All |

---

## Troubleshooting

| Issue | Resolution |
|-------|------------|
| `@salesforce/plugin-signups does not exist in the registry` | Snapshot commands live in the `signups` plugin, bundled with a normal `sf` install. This means the CLI environment is incomplete (slim/offline image) — do NOT attempt `sf plugins install` in an offline environment, it will fail and loop. Advise repairing the environment (`sf update`, or a fresh install) from a connected machine. |
| `Scratch Org Snapshots isn't enabled for your Dev Hub.` | The Dev Hub lacks the snapshot feature — contact Salesforce to enable it |
| `No snapshot found with the given name or id: <value>` (`SingleRecordQuery_NoRecords`) | Verified live on `get`/`delete` — the name/ID doesn't exist in this Dev Hub. Run `sf org list snapshot --json` to see available snapshots |
| `STRING_TOO_LONG` — "Org Snapshot Name: data value too large... (max length=15)" | Verified live — the `--name` value exceeds 15 characters. Shorten it and retry |
| Snapshot name already exists (`DuplicateValue`) | Names must be unique per Dev Hub — choose a different name |
| `Status` is `InProgress` for a while | Creation is asynchronous — keep polling `sf org get snapshot` until `Status` becomes `Active` |
| `Status` is `Error` (see the `Error` field) | Read the `Error` field, delete the failed snapshot, and recreate |
| `NotADevHubError` | The targeted org isn't a Dev Hub — point `--target-dev-hub` at an actual Dev Hub |
| No default Dev Hub org found | Provide `--target-dev-hub <alias>` or set a default with `sf config set target-dev-hub=<alias>` |

---

## Output Expectations

All commands return JSON when `--json` is used. `get`/`list` return the raw `OrgSnapshot` sobject record(s) — verified live, these include the sobject `attributes` wrapper plus `Id`, `SnapshotName`, `Description`, `Status` (`New`, `InProgress`, `Active`, `Error`, `Expired`, or `Deleted`), `SourceOrg`, `CreatedDate`, `LastModifiedDate`, `ExpirationDate` (`null` until `Active`), and `Error`.

- **Create** → a single snapshot record (`Status` is `InProgress` immediately after creation; `ExpirationDate` is `null`).
- **Get** → a single snapshot record — use it to poll `Status`.
- **List** → an array of snapshot records, ordered by `CreatedDate`. Empty array if none exist.
- **Delete** → `{ "id": "0Oo...", "success": true, "errors": [] }`. No result if the user declines the confirmation prompt.

See the example files below for exact response structures (captured live against a real Dev Hub, not assumed).

---

## Cross-Skill Integration

| Need | Delegate to |
|------|-------------|
| Create a scratch org from a snapshot | `dx-org-manage` skill (set `snapshot` to the snapshot name in the definition file, or `--snapshot <name>`) |
| Create/list/delete an org **shape** instead of a snapshot | `dx-org-shape-manage` skill |

---

## Reference File Index

| File | When to read |
|------|-------------|
| `references/cli_flags.md` | Detailed flag reference across create/get/list/delete, including the `jq` pipeline for filtering snapshots expiring soon |
| `references/snapshot_usage.md` | Using a snapshot name in a scratch org definition file, once it's `Active` |

## Example Files

| File | Purpose |
|------|---------|
| `examples/create_success_output.json` | Successful snapshot creation (`Status: InProgress`) |
| `examples/create_error_output.json` | `STRING_TOO_LONG` — name over 15 characters |
| `examples/get_output.json` | Get response for an `Active` snapshot (`ExpirationDate` populated) |
| `examples/list_output.json` | List response — array of snapshot records |
| `examples/delete_output.json` | Successful delete response |
