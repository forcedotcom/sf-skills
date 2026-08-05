# CLI Flags Reference

Complete reference for `sf org create snapshot` command flags.

## Required Flags

| Flag | Alias | Description | Example |
|------|-------|-------------|---------|
| `--source-org` | `-o` | ID or authenticated username/alias of scratch org to snapshot | `--source-org my-scratch` |
| `--name` | `-n` | Unique name for the snapshot | `--name MySnapshot` |
| `--target-dev-hub` | `-v` | Dev Hub org username or alias (required unless default is set) | `--target-dev-hub DevHub` |

## Optional Flags

| Flag | Alias | Description | Example |
|------|-------|-------------|---------|
| `--description` | `-d` | Description of snapshot contents | `--description "Package v1.2.0"` |
| `--api-version` | | Override the API version used for API requests | `--api-version 66.0` |

## Global Flags

| Flag | Description |
|------|-------------|
| `--json` | Format output as JSON (ALWAYS use this) |

## Usage Patterns

### Basic Snapshot Creation

```bash
sf org create snapshot --source-org my-scratch --name MySnapshot --json
```

### With Description

```bash
sf org create snapshot \
  --source-org my-scratch \
  --name MySnapshot \
  --description "Baseline with Package v1.2.0" \
  --json
```

### Using Org ID Instead of Alias

```bash
sf org create snapshot \
  --source-org 00D5g00000001XyEAI \
  --name MySnapshot \
  --json
```

### Specify Dev Hub Explicitly

```bash
sf org create snapshot \
  --source-org my-scratch \
  --name MySnapshot \
  --target-dev-hub MyDevHub \
  --json
```

## Important Notes

- **Source org auto-resolution**: Accepts org ID (starts with 00D) or username/alias — aliases are automatically resolved to org IDs
- **Description best practice**: Include version control reference (git tag, commit SHA) to track snapshot contents
- **Asynchronous creation**: Snapshot creation happens asynchronously — use `sf org get snapshot` to check status
