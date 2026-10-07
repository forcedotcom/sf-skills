# Using Snapshots in Scratch Org Definition Files

Snapshot lifecycle (create/get/list/delete) is owned by this skill. Once a snapshot's `Status` is `Active` (checked via `sf org get snapshot` — see `SKILL.md`), reference it by name to create new scratch orgs — that part is owned by the **`dx-org-manage`** skill.

## Scratch Org Definition File Format

Use the `snapshot` field instead of `edition` in `project-scratch-def.json`:

```json
{
  "orgName": "My Company",
  "snapshot": "MySnapshot",
  "features": ["EnableSetPasswordInApi"]
}
```

## Key Differences from Edition-Based Definitions

| Field | Edition-based | Snapshot-based |
|-------|--------------|----------------|
| Primary field | `"edition": "Developer"` | `"snapshot": "MySnapshot"` |
| Contents | Empty org with edition defaults | Pre-configured org state (metadata + data) from the snapshot |

## Or via Command Flag

```bash
sf org create scratch --snapshot MySnapshot --target-dev-hub <alias> --alias <name> --json
```

## Common Use Cases

### 1. Package Development

```json
{ "orgName": "Package Dev Org", "snapshot": "Dependencies_v1.2.0" }
```

### 2. Testing Baseline

```json
{ "orgName": "Test Baseline", "snapshot": "TestData_Populated" }
```

### 3. CI/CD Pipeline

```json
{ "orgName": "CI Scratch Org", "snapshot": "Nightly_Build_Baseline" }
```

## Workflow Summary

1. **Create the snapshot** (`dx-org-snapshot-manage`): `sf org create snapshot --source-org <scratch> --name MySnapshot`
2. **Poll status** (`dx-org-snapshot-manage`): `sf org get snapshot --snapshot MySnapshot` until `Status` is `Active`
3. **Reference in a definition file**: `"snapshot": "MySnapshot"`
4. **Create the new scratch org** (`dx-org-manage`): `sf org create scratch --definition-file config/project-scratch-def.json`
