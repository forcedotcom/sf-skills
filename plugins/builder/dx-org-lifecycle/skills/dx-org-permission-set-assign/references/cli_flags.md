# CLI Flags Reference

Complete reference for `sf org assign permset` command flags.

## Required Flags

| Flag | Alias | Description | Example |
|------|-------|-------------|---------|
| `--name` | `-n` | Permission set to assign (can be repeated) | `--name MyPermSet` |
| `--target-org` | `-o` | Username or alias of the target org (required unless default is set) | `--target-org my-scratch` |

## Optional Flags

| Flag | Alias | Description | Example |
|------|-------|-------------|---------|
| `--on-behalf-of` | `-b` | Username or alias to assign the permission set to (can be repeated) | `--on-behalf-of user1@my.org` |
| `--api-version` | | Override the API version used for API requests | `--api-version 66.0` |

## Global Flags

| Flag | Description |
|------|-------------|
| `--json` | Format output as JSON (ALWAYS use this) |

## Usage Patterns

### Single Permission Set to Default Admin

```bash
sf org assign permset --name MyPermSet --json
```

### Multiple Permission Sets to Default Admin

```bash
sf org assign permset --name PermSet1 --name PermSet2 --json
```

### Assign to Specific Org

```bash
sf org assign permset --name MyPermSet --target-org my-scratch --json
```

### Assign to Specific Users

```bash
sf org assign permset --name MyPermSet --on-behalf-of user1@my.org --on-behalf-of user2@my.org --json
```

### Combined: Multiple Sets, Multiple Users, Specific Org

```bash
sf org assign permset \
  --name PermSet1 \
  --name PermSet2 \
  --on-behalf-of user1@my.org \
  --on-behalf-of user2@my.org \
  --target-org my-scratch \
  --json
```

## Important Notes

- **Multiple Values**: Use multiple `--name` or `--on-behalf-of` flags rather than comma-separated values
- **Spaces in Names**: Enclose permission set names with spaces in double quotes: `--name "Permission Set Name"`
- **Default Behavior**: Without `--on-behalf-of`, assigns to the org's default admin user
- **Processing**: Multiple users are processed sequentially to avoid auth file collisions
