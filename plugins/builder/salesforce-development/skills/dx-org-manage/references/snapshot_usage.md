# Using Snapshots in Scratch Org Definition Files

After creating a snapshot, reference it in scratch org definition files to create new scratch orgs from the saved state.

## Scratch Org Definition File Format

Use the `snapshot` field instead of `edition` in your `project-scratch-def.json`:

```json
{
  "orgName": "My Company",
  "snapshot": "MySnapshot",
  "features": ["EnableSetPasswordInApi"],
  "settings": {
    "lightningExperienceSettings": {
      "enableS1DesktopEnabled": true
    }
  }
}
```

## Key Differences from Edition-Based Definitions

| Field | Edition-based | Snapshot-based |
|-------|--------------|----------------|
| Primary field | `"edition": "Developer"` | `"snapshot": "MySnapshot"` |
| Contents | Empty org with edition defaults | Pre-configured org state from snapshot |

## Creating a Scratch Org from Snapshot

```bash
sf org create scratch --definition-file config/project-scratch-def.json --alias from-snapshot
```

The scratch org will be created with all the metadata, data, and configuration from the snapshot.

## Common Use Cases

### 1. Package Development

```json
{
  "orgName": "Package Dev Org",
  "snapshot": "Dependencies_v1.2.0",
  "description": "Org with all dependencies installed"
}
```

### 2. Testing Baseline

```json
{
  "orgName": "Test Baseline",
  "snapshot": "TestData_Populated",
  "description": "Org with sample data for testing"
}
```

### 3. CI/CD Pipeline

```json
{
  "orgName": "CI Scratch Org",
  "snapshot": "Nightly_Build_Baseline",
  "description": "Latest nightly build dependencies"
}
```

## Workflow Summary

1. **Create snapshot**: `sf org create snapshot --source-org <scratch> --name MySnapshot`
2. **Check status**: `sf org get snapshot --snapshot MySnapshot`
3. **Reference in definition file**: `"snapshot": "MySnapshot"`
4. **Create new scratch org**: `sf org create scratch --definition-file config/project-scratch-def.json`
