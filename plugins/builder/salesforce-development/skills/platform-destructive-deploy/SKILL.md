---
name: platform-destructive-deploy
description: "Execute the destructiveChanges.xml delete-and-deploy workflow against a Salesforce org. TRIGGER when the user asks to delete/remove a custom object, field, Apex class, flow, or any metadata component FROM an org, or to perform a 'destructive deploy' / removal as part of a release. Validates first and gates production with explicit confirmation. DO NOT TRIGGER for local file deletion (use Bash), or for net-new deploys (use platform-metadata-deploy)."
allowed-tools:
  - Bash
  - Read
  - Write
  - Glob
  - Grep
---

# Handling Destructive Changes

Coordinate metadata deletion against a Salesforce org via the destructiveChanges manifest. Runs in three phases: scope → validate → execute, with stricter guardrails for production.

## Phase 1 — Scope the deletion

### Step 1a — Gather the components to remove

Ask the user (or infer from context) which components to delete. For each, capture:
- Metadata type (e.g. `CustomObject`, `CustomField`, `ApexClass`, `Flow`, `PermissionSet`)
- API name (e.g. `Project__c`, `Account.Status__c`, `MyController`)

### Step 1b — Local dependency scan (best-effort)

Before generating the manifest, scan the local project for references to each component. Use Grep over `force-app/`:

```bash
grep -rn "<componentApiName>" force-app/ --include='*.cls' --include='*.trigger' --include='*.xml' --include='*.js' --include='*.html'
```

If references are found:
- List them to the user
- Recommend either updating those references first OR removing them in the same destructive deploy
- Do NOT proceed silently — surface the dependency risk

### Step 1c — Generate `destructiveChanges.xml`

Write to `manifest/destructiveChangesPre.xml` (for pre-deploy deletion) or `manifest/destructiveChangesPost.xml` (for post-deploy deletion). Use the standard Salesforce metadata format:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
    <types>
        <members>Project__c</members>
        <members>OldThing__c</members>
        <name>CustomObject</name>
    </types>
    <types>
        <members>Account.Status__c</members>
        <name>CustomField</name>
    </types>
    <version>62.0</version>
</Package>
```

Use the API version from `sfdx-project.json`'s `sourceApiVersion`.

Group components by metadata type (one `<types>` block per type). For namespaced fields, use `Object.Field` notation.

## Phase 2 — Validate

ALWAYS validate before executing a destructive deploy:

```bash
sf project deploy validate \
  --pre-destructive-changes manifest/destructiveChangesPre.xml \
  --manifest manifest/package.xml \
  --target-org <alias> \
  --test-level RunLocalTests \
  --json
```

(For post-destructive: use `--post-destructive-changes`.)

If `package.xml` doesn't exist, create an empty one alongside (deletion-only deploy needs a package descriptor):

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
    <version>62.0</version>
</Package>
```

If validation fails, surface errors and STOP. Common failure modes:
- "Cannot delete: referenced by Apex/Flow/Layout" → component still has references
- "Cannot delete: required for license" → managed-package or license dependency
- "Insufficient access" → user lacks delete permission

## Phase 3 — Execute

### Production path

Confirm whether the target is production before executing. The reliable check is the gate's classifier (returns `production|sandbox|scratch|trial|devhub|unknown`):

```bash
sf org display --target-org <alias> --json | "${CLAUDE_PLUGIN_ROOT}/scripts/sf-deploy-gate" classify
```

If the classifier returns `production`:
1. Display destructive confirmation banner (mirroring `platform-quick-deploy`)
2. List EVERY component that will be deleted
3. Require explicit "yes, delete from PRODUCTION" confirmation
4. Reject `--purge-on-delete` unless the user types it explicitly

The PreToolUse hook (`sf-deploy-gate destructive`) will already block bare destructive commands against prod — surface that denial to the user, do not work around it.

### Sandbox / Scratch path

```bash
sf project deploy start \
  --pre-destructive-changes manifest/destructiveChangesPre.xml \
  --manifest manifest/package.xml \
  --target-org <alias> \
  --json \
  --wait 30
```

Add `--purge-on-delete` only if the user explicitly asked to permanently delete (skip the recycle bin).

## Phase 4 — Post-delete cleanup

After a successful destructive deploy:
- Recommend a `sf project retrieve start --metadata <Type>:<Name>` is NOT useful (component is gone) — instead suggest cleaning up the local source:
  ```bash
  # Remove the now-deleted local files to keep source tracking accurate
  rm -rf force-app/main/default/<path-to-component>
  ```
- If deleting a custom field with data, remind the user that data is gone (or in the recycle bin until purged)
- Recommend running tests to confirm no runtime regressions

## Rules

- ALWAYS validate first; NEVER skip Phase 2
- ALWAYS scan for local references; NEVER delete blindly
- ALWAYS gate production with explicit user confirmation
- NEVER add `--purge-on-delete` without explicit user request
- NEVER use `--ignore-errors` on a destructive deploy
- ALWAYS use the API version from `sfdx-project.json`, not a hardcoded value
- If the user is deleting a field with `required="true"` or that's used in `RecordType` picklist values, surface the cascade impact before proceeding
