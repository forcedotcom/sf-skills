# Scratch Org Definition File Options

Complete reference for scratch org definition file configuration. Use this when users need to configure org features, settings, or advanced options beyond basic org creation.

## File Structure

```json
{
  "orgName": "My Company",
  "edition": "Developer",
  "features": ["<feature>", "<feature>"],
  "settings": {
    "<SettingType>": {
      "<settingName>": <value>
    }
  },
  "adminEmail": "admin@example.com",
  "description": "Scratch org for feature X development",
  "hasSampleData": false,
  "snapshot": "SnapshotName",
  "sourceOrg": "00D1234567890ABC",
  "username": "custom.username@example.com"
}
```

## Authoring a definition file (seed-then-modify)

When a user wants features/settings and no suitable definition file exists, do NOT synthesize JSON
from scratch — **start from a seed and modify it**:

1. **Seed source (priority):** (1) an existing definition file in the project's `config/` (copy as
   base), else (2) the file `sf template generate project` scaffolds
   (`config/project-scratch-def.json`), else (3) the minimal seed shipped with this skill:
   `assets/scratch-def.seed.json` — `{"orgName": "...", "edition": "Developer", "features": [],
   "settings": {}}`.
2. **Modify** per the requested features/settings using the schema on this page. The
   features/settings space is open-ended — compose whatever the user asks for; nested `settings`
   **cannot** be CLI flags, so any such request means authoring a file.
3. **Write a new purpose-named file** (`config/<purpose>-scratch-def.json`, or a user-chosen path
   outside a project) — **no-clobber**: never overwrite an existing file (especially
   `config/project-scratch-def.json`) without explicit confirmation.
4. **Interactive:** show the result and let the user accept / edit. **Non-interactive (eval/CI):**
   author the file AND proceed to create without waiting.

Author only documented fields; never write internal-only fields. See
`references/scratch-org-create.md` for how authoring fits the full create flow.

## Core Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `orgName` | string | Yes | Name of the company (user-visible) |
| `edition` | string | Yes* | Developer, Enterprise, Group, Professional, or Partner variants |
| `adminEmail` | string | No | Email for the admin user |
| `description` | string | No | Description shown in Dev Hub |
| `hasSampleData` | boolean | No | Include standard sample data (default: false) |
| `username` | string | No | Custom username for admin (must be globally unique) |

\* Not required if using `snapshot` or `sourceOrg`.

**Pass-through note:** fields not listed in this reference are relayed to the CLI unchanged. If the CLI doesn't accept a field, it reports the error itself — the skill does not pre-validate, rename, or rewrite. When the skill *authors* a definition file it writes only the documented fields below; if your existing file contains other fields, they are relayed as-is.

**CLI Flag Overrides:** When using a definition file with `--definition-file`, you can override any of these fields with CLI flags:
- `--edition` overrides `edition`
- `--name` overrides `orgName`
- `--username` overrides `username`
- `--description` overrides `description`
- `--admin-email` overrides `adminEmail`
- `--release` overrides `release`
- `--snapshot` overrides `snapshot`
- `--source-org` overrides `sourceOrg`

CLI flags take precedence over definition file values.

## Features Array

Enable org features by adding to `features` array. Common features:

```json
"features": [
  "Communities",
  "ServiceCloud",
  "Sites",
  "MultiCurrency",
  "PersonAccounts",
  "Walkthroughs",
  "AdvancedPersonAccountSecurity"
]
```

**Finding available features:**
- Run: `sf org list metadata-types --target-org <dev-hub>`
- Look for `FeatureParameterValueSet` type
- Or check: https://developer.salesforce.com/docs/atlas.en-us.sfdx_dev.meta/sfdx_dev/sfdx_dev_scratch_orgs_def_file.htm

## Settings Object

Configure org settings by type. Format:

```json
"settings": {
  "lightningExperienceSettings": {
    "enableS1DesktopEnabled": true
  },
  "mobileSettings": {
    "enableS1EncryptedStoragePref2": false
  },
  "securitySettings": {
    "passwordPolicies": {
      "minimumPasswordLength": 10
    }
  }
}
```

**Common settings:**

### Language Settings
```json
"languageSettings": {
  "enableTranslationWorkbench": true
}
```

### Chatter Settings
```json
"chatterSettings": {
  "enableChatter": true
}
```

### Path Settings
```json
"pathAssistantSettings": {
  "pathAssistantEnabled": true
}
```

## Alternative Creation Sources

### Snapshot
```json
{
  "snapshot": "BaselineSnapshot"
}
```

Creates org from a snapshot. The `edition` field is optional when using snapshots.

### Source Org (Org Shape)
```json
{
  "sourceOrg": "00D1234567890ABC"
}
```

Creates org from an org shape. The `edition` field is optional when using org shapes.

**Note:** `snapshot` and `sourceOrg` are mutually exclusive.

## Release Overrides

Control which Salesforce release the scratch org uses:

```json
{
  "release": "preview"
}
```

Options: `preview` (next release), `previous` (previous release). Only use during Salesforce release transition periods.

## Duration Control

While not part of the definition file, you can override duration with the CLI flag:
```bash
--duration-days 15
```

Maximum: 30 days. Default: 7 days.

## Packaging Options

```json
{
  "ancestorId": "04t...",
  "ancestorVersion": "1.0",
  "namespace": "myns"
}
```

Used for second-generation package (2GP) development.

**CLI Packaging Flags:**
- `--no-ancestors` - Exclude 2GP ancestors from the scratch org
- `--no-namespace` - Create scratch org without namespace, even if Dev Hub has one

## Example: Full Configuration

```json
{
  "orgName": "Acme Corp Dev Org",
  "edition": "Developer",
  "description": "Feature X development scratch org",
  "adminEmail": "dev-team@acme.com",
  "hasSampleData": false,
  "features": [
    "Communities",
    "ServiceCloud",
    "MultiCurrency"
  ],
  "settings": {
    "lightningExperienceSettings": {
      "enableS1DesktopEnabled": true
    },
    "securitySettings": {
      "passwordPolicies": {
        "minimumPasswordLength": 10,
        "minimumPasswordLifetime": false,
        "obscure": false
      }
    },
    "languageSettings": {
      "enableTranslationWorkbench": true
    }
  }
}
```

## Connected App Authentication

For enhanced security, use a Connected App for authentication:

```bash
sf org create scratch --definition-file config.json --client-id <consumer-key>
```

When `--client-id` is provided, CLI prompts for the client secret. The scratch org will use the Connected App for authentication instead of default JWT.

## Common Pitfalls

| Issue | Cause | Fix |
|-------|-------|-----|
| Features not available | Feature name spelled wrong or not available in edition | Check feature name spelling and edition compatibility |
| Settings ignored | Invalid setting name or structure | Verify setting exists in Metadata API docs |
| JSON parse error | Invalid JSON syntax | Validate JSON with linter |
| Conflicting options | Both `snapshot` and `sourceOrg` specified | Use only one alternative creation source |
| CLI flag ignored | Trying to override a field that doesn't support override | Only certain fields can be overridden (see CLI Flag Overrides section) |
