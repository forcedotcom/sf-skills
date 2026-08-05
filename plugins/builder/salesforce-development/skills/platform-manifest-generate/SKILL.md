---
name: platform-manifest-generate
description: "Use this skill to generate a package.xml (and optionally destructiveChanges.xml, destructiveChangesPre.xml, or destructiveChangesPost.xml) from a local source directory, an explicit component list, or org introspection. Trigger when the user says \"generate a package.xml from this folder\", \"create a manifest for these classes\", \"I need a deploy manifest\", \"build package.xml for the contacts changes\", or \"create both package.xml and destructiveChanges.xml for these deletions\". Encodes which metadata types accept a wildcard member and which must be enumerated, avoiding the common \"Wildcards are not supported for this metadata type\" deploy failure. DO NOT TRIGGER for executing a deploy (use platform-metadata-deploy), performing the deletion in destructiveChanges.xml (use platform-destructive-deploy), or retrieving metadata (use platform-metadata-retrieve)."
metadata:
  version: "1.0"
  relatedSkills:
    - "platform-metadata-deploy"
    - "platform-metadata-retrieve"
    - "platform-destructive-deploy"
    - "platform-deploy-validate"
  cliTools:
    - tool: ["sf"]
      semver: ">=2.0.0"
---

# platform-manifest-generate

Produce a Salesforce metadata manifest — `package.xml` (or one of the destructive variants) — from local source, an org, or an explicit component list. This skill is purely about authoring the manifest file. Hand off to `platform-metadata-deploy` or `platform-destructive-deploy` once the file exists.

---

## Tool Restrictions

**Use ONLY the Bash tool** to run `sf project generate manifest`, and the `Write` tool for the hand-built fallback path. Do NOT use MCP tools.

---

## When This Skill Owns the Task

Use `platform-manifest-generate` when the work involves any of:
- Building a `package.xml` from a source directory (e.g. `force-app/main/default/classes/`)
- Building a manifest from an explicit list of components (e.g. `AccountService`, `ContactSelector`, `Account`)
- Building a manifest by introspecting an org via `--from-org`
- Producing `destructiveChanges.xml`, `destructiveChangesPre.xml`, or `destructiveChangesPost.xml` for a deletion
- Producing both a `package.xml` and a destructive manifest in one operation

Delegate elsewhere when the user is:
- Running the deploy itself → `platform-metadata-deploy`
- Validating before a prod release → `platform-deploy-validate`
- Executing the destructive deploy → `platform-destructive-deploy` (that skill **uses** the manifest this skill **generates**)
- Retrieving metadata to local → `platform-metadata-retrieve`

---

## Two Generation Paths

### Path A — CLI-driven (recommended)

Wrap `sf project generate manifest`. Always prefer this path; it knows about every metadata type and produces canonical XML — and never emits `*`, sidestepping the wildcard hazard entirely.

The CLI offers three input modes (mutually exclusive):

| Input | Flag | Use when |
|---|---|---|
| Source directory | `--source-dir` (`-p`) | User points to a folder containing already-on-disk metadata |
| Component list | `--metadata` (`-m`) | User names specific components, e.g. `ApexClass:AccountService CustomObject:Account` |
| Org introspection | `--from-org` | User wants every component currently in an org (or a filtered subset) |

You can specify either `--source-dir` or `--metadata`, not both. `--from-org` may be combined with `--metadata` (filter included types) or `--excluded-metadata` (filter out types).

**Verified flags** (do not invent flags — verify with `sf project generate manifest --help` if unsure):

| Flag | Purpose |
|---|---|
| `--source-dir`, `-p` | Local source paths to scan |
| `--metadata`, `-m` | Component names to include (e.g. `ApexClass:AccountService`) |
| `--from-org` | Username or alias of org to introspect |
| `--name`, `-n` | Custom output filename (mutually exclusive with `--type`) |
| `--type`, `-t` | Predefined manifest kind: `package` \| `pre` \| `post` \| `destroy` |
| `--output-dir`, `-d` | Directory to write the manifest into |
| `--api-version` | Override the API version for the request |
| `--include-packages`, `-c` | Include `managed` and/or `unlocked` package metadata when using `--from-org` |
| `--excluded-metadata` | Types to exclude when using `--from-org` |
| `--json` | Machine-readable output |

**Manifest filename by `--type`:**

| `--type` | Output file |
|---|---|
| `package` (default) | `package.xml` |
| `pre` | `destructiveChangesPre.xml` |
| `post` | `destructiveChangesPost.xml` |
| `destroy` | `destructiveChanges.xml` |

You can specify either `--type` or `--name`, not both.

#### Canonical CLI examples

```bash
# Build package.xml from a source dir
sf project generate manifest \
  --source-dir force-app/main/default \
  --name package.xml \
  --output-dir manifest \
  --json

# Build package.xml from an explicit component list
sf project generate manifest \
  --metadata ApexClass:AccountService \
  --metadata ApexClass:ContactSelector \
  --metadata CustomObject:Account \
  --name package.xml \
  --output-dir manifest \
  --json

# Build destructiveChanges.xml from a component list
sf project generate manifest \
  --metadata CustomField:Account.OldField__c \
  --metadata CustomField:Account.OldStatus__c \
  --type destroy \
  --output-dir manifest \
  --json

# Build a manifest by introspecting an org (filtered)
sf project generate manifest \
  --from-org <alias> \
  --metadata ApexClass,CustomObject,CustomLabels \
  --output-dir manifest \
  --json
```

If both a `package.xml` and a destructive manifest are needed, run the CLI twice — once with `--type package` (or default), once with `--type destroy` / `pre` / `post`.

### Path B — Hand-built fallback

Use this only when the CLI cannot express the user's intent — e.g. they want "just the Apex classes I changed today" and the change set is derived from `git diff` rather than a clean directory or component list. In that case:

1. Resolve the components yourself (e.g. parse `git diff --name-only` and map paths back to metadata types).
2. Group by metadata type.
3. Emit the XML inline using the schema below.
4. Always cross-check by running `sf project deploy start --manifest <file> --dry-run` (hand off to `platform-metadata-deploy`).

#### Manifest XML schema

Root element is `<Package>` in the metadata namespace. Each metadata type gets one `<types>` block containing one `<members>` per component plus a single `<name>`. The trailing `<version>` declares the API version for the manifest.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
    <types>
        <members>AccountService</members>
        <members>ContactSelector</members>
        <name>ApexClass</name>
    </types>
    <types>
        <members>Account</members>
        <name>CustomObject</name>
    </types>
    <types>
        <members>Account.Status__c</members>
        <name>CustomField</name>
    </types>
    <version>62.0</version>
</Package>
```

Notes:
- For component-bound types like `CustomField`, `BusinessProcess`, `RecordType`, `Layout`, `ListView`, `ValidationRule`, `WebLink`, members use `Object.Name` notation.
- `destructiveChanges.xml`, `destructiveChangesPre.xml`, and `destructiveChangesPost.xml` use the **same XML structure** — only the filename and intent differ.
- An empty manifest (no `<types>` blocks) is legal and is sometimes paired with a destructive manifest:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
    <version>62.0</version>
</Package>
```

---

## API Version Handling

The `<version>` element at the bottom of every manifest must reflect the project's API version.

**Resolution order:**
1. Read `sourceApiVersion` from `sfdx-project.json` at the project root.
2. If `--api-version` was passed by the user, use that instead.
3. If neither is available, fall back to the value reported by `sf --version` (the CLI's bundled API version) — but **warn the user** and recommend they set `sourceApiVersion` in `sfdx-project.json` for reproducibility.
4. Never silently hardcode a value (e.g. `62.0`) into output without surfacing the source.

```bash
# Quick read of sourceApiVersion
jq -r '.sourceApiVersion' sfdx-project.json
```

When using the CLI path, omit `--api-version` unless the user explicitly overrides — the CLI already reads `sourceApiVersion`.

---

## Wildcard Members (`<members>*</members>`)

A wildcard member matches every component of that metadata type. **It is not legal for every type.** Using `*` for a disallowed type causes deploy/retrieve errors like `Wildcards are not supported for this metadata type`.

### Wildcard NOT allowed (must enumerate)

These types require explicit member names. Common examples: `Profile`, `PermissionSet`, `PermissionSetGroup`, `CustomLabels`, `CustomObjectTranslation`, `Layout`, `Workflow` (in some package configurations), `SharingRules`, `StandardValueSet`, `ManagedTopics`, and most "container" types whose contents are object-bound (`CustomField`, `RecordType`, `BusinessProcess`, `ListView`, `ValidationRule`, `WebLink`, `CompactLayout`).

For these, enumerate explicitly:

```xml
<types>
    <members>Admin</members>
    <members>Standard User</members>
    <name>Profile</name>
</types>
```

### Wildcard generally allowed

Most "self-contained" component types accept `*`. Examples: `ApexClass`, `ApexTrigger`, `ApexComponent`, `ApexPage`, `AuraDefinitionBundle`, `LightningComponentBundle`, `CustomApplication`, `CustomTab`, `StaticResource`, `EmailTemplate`, `Report`, `Dashboard`, `Flow`, `FlexiPage`, `CustomMetadata`. See [references/wildcard-allowlist.md](references/wildcard-allowlist.md) for the full enumeration and edge cases.

Rule of thumb: if you are not certain, **list the components explicitly**. The CLI path (`--source-dir` / `--metadata`) sidesteps this problem because it never emits `*`.

---

## Examples

### Example 1 — Build `package.xml` from a directory

> "Generate package.xml from `force-app/main/default/classes/`"

```bash
sf project generate manifest \
  --source-dir force-app/main/default/classes \
  --name package.xml \
  --output-dir manifest \
  --json
```

Result: `manifest/package.xml` listing every Apex class in that folder.

### Example 2 — Build a manifest covering specific components

> "Build a manifest covering AccountService, ContactSelector, and the Account custom object"

```bash
sf project generate manifest \
  --metadata ApexClass:AccountService \
  --metadata ApexClass:ContactSelector \
  --metadata CustomObject:Account \
  --name package.xml \
  --output-dir manifest \
  --json
```

Result: `manifest/package.xml` containing exactly those three components.

### Example 3 — Generate both `package.xml` and `destructiveChanges.xml` for deletions

> "Create both package.xml and destructiveChanges.xml for these deletions: `Account.OldField__c`, `Account.OldStatus__c`"

```bash
# Empty/minimal package.xml (deletion-only deploy still needs a package descriptor)
sf project generate manifest \
  --metadata CustomLabels \
  --name package.xml \
  --output-dir manifest \
  --json

# destructiveChanges.xml
sf project generate manifest \
  --metadata CustomField:Account.OldField__c \
  --metadata CustomField:Account.OldStatus__c \
  --type destroy \
  --output-dir manifest \
  --json
```

After generation, hand off to `platform-destructive-deploy` to validate and execute the deletion.

---

## Failure Modes

| Symptom | Likely cause | Recovery |
|---|---|---|
| `Path does not exist: <dir>` | `--source-dir` points at a missing folder | Confirm the path; use `ls` to verify; default to `force-app/main/default` if the user is vague |
| Generated manifest is empty | Source dir contained no recognizable metadata, or all files were ignored | Check `.forceignore`; verify the path actually contains metadata files (`*.cls`, `*-meta.xml`, etc.) |
| `Wildcards are not supported for this metadata type` at deploy time | Hand-built manifest used `*` for a disallowed type | See the wildcard allowlist above; enumerate the components explicitly |
| `<version>` missing or mismatched | `sfdx-project.json` lacks `sourceApiVersion` | Add `sourceApiVersion` to `sfdx-project.json`, or pass `--api-version` to the CLI |
| `You can specify either --type or --name, but not both` | CLI invocation passed both flags | Drop one; use `--type` for predefined names, `--name` for a custom one |
| `You can specify either --source-dir or --metadata, but not both` | CLI invocation passed both | Pick one input mode |
| Components missing from `--from-org` output | Org introspection batched too aggressively, or the type is in a managed package | Set `SF_LIST_METADATA_BATCH_SIZE` lower; add `--include-packages managed` if intended |

---

## Cross-Skill Integration

| Need | Delegate to | Reason |
|---|---|---|
| Run a deploy with the generated manifest | `platform-metadata-deploy` | This skill stops at file generation |
| Validate before a prod release | `platform-deploy-validate` | Pre-flight test against prod |
| Actually delete the components in the destructive manifest | `platform-destructive-deploy` | That skill validates and executes the destructive deploy |
| Retrieve metadata listed in the manifest | `platform-metadata-retrieve` | Pulls org metadata to local |
| Author the metadata being listed in the manifest | Other `platform-*` generators (e.g. `platform-custom-object-generate`) | The manifest just lists what already exists on disk |

---

## Completion Format

```text
Manifest goal: <package | pre | post | destroy>
Input mode: <source-dir | metadata list | from-org | hand-built>
Output: <path/to/manifest.xml>
API version: <value> (source: sfdx-project.json | --api-version | CLI default)
Component count: <N> across <M> metadata types
Next step: <platform-metadata-deploy | platform-deploy-validate | platform-destructive-deploy>
```
