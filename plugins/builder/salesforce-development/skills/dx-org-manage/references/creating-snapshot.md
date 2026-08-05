# Creating Snapshots

Creates a point-in-time snapshot of a scratch org using `sf org create snapshot`. Snapshots preserve scratch org state and configuration for reuse in scratch org definition files.

---

## Required Inputs

Infer from the user's request:

- **Source org**: Scratch org ID (starts with 00D) or username/alias to snapshot
- **Snapshot name**: Unique name for the snapshot (required)
- **Dev Hub**: Dev Hub org alias/username (uses default if not specified)
- **Description** (optional): Document snapshot contents, version control reference

---

## Workflow

1. **Gather inputs** — get source org, snapshot name, and optional description
2. **Build command** — construct `sf org create snapshot` with appropriate flags
3. **Execute via Bash tool** — run command with `--json` flag
4. **Return result** — report snapshot ID and status

### Command Patterns

| User intent | Execute via Bash tool |
|-------------|---------|
| Create snapshot with name only | `sf org create snapshot --source-org <orgId or alias> --name <SnapshotName> --json` |
| Create snapshot with description | `sf org create snapshot --source-org <orgId or alias> --name <SnapshotName> --description "<desc>" --json` |
| Specify Dev Hub explicitly | `sf org create snapshot --source-org <orgId or alias> --name <SnapshotName> --target-dev-hub <devHubAlias> --json` |

---

## Rules / Constraints

| Constraint | Rationale |
|-----------|-----------|
| Always use `--json` flag | Provides structured output for reliable parsing and error handling |
| Snapshot names must be unique in the Dev Hub | Duplicate names cause creation to fail |
| Source org must be a scratch org | Snapshots only work with scratch orgs, not sandboxes or production orgs |
| Dev Hub must have snapshot feature enabled | "NOT_FOUND" error means Dev Hub doesn't support snapshots |
| Source org accepts ID or username/alias | Command auto-resolves aliases to org IDs; org IDs start with 00D |
| Include description for tracking | Best practice: reference version control tag or commit ID in description |

---

## Troubleshooting

| Issue | Resolution |
|-------|------------|
| "NOT_FOUND" error when creating snapshot | Dev Hub doesn't have snapshot feature enabled — contact admin to enable in Dev Hub settings |
| "No org found for <alias>" error | Source org alias doesn't exist or isn't authenticated — verify with `sf org list` |
| Snapshot name already exists | Use a different unique name — snapshot names must be unique per Dev Hub |
| "An error while created the org snapshot" | Generic error — check that source org is a scratch org and still active |
| Long-running snapshot creation | Use `sf org get snapshot --snapshot <name>` to check status — snapshot creation is asynchronous |

---

## Output Expectations

The command returns JSON output with the created snapshot details.

See `examples/snapshots/success_output.json` and `examples/snapshots/error_output.json` for complete response structures.

Example success response:
```json
{
  "result": {
    "SnapshotId": "0Ym...",
    "SnapshotName": "MySnapshot",
    "Status": "Active",
    "SourceOrg": "00D..."
  }
}
```

---

## Using Snapshots

After creating a snapshot, use it to create scratch orgs by:

1. **In scratch org definition file:**
   ```json
   {
     "snapshot": "MySnapshot"
   }
   ```

2. **Or via command flag:**
   ```bash
   sf org create scratch --snapshot MySnapshot --target-dev-hub <alias> --alias <name> --json
   ```

See `snapshot_usage.md` for detailed examples.

---

## Additional Resources

- See `cli_flags.md` for detailed explanation of all available flags
- See `snapshot_usage.md` for how to use snapshots in scratch org creation
