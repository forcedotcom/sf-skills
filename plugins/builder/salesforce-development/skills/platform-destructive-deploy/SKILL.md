---
name: platform-destructive-deploy
description: "Execute the destructiveChanges.xml delete-and-deploy workflow against a Salesforce org. TRIGGER when the user asks to delete/remove a custom object, field, Apex class, flow, or any metadata component FROM an org, or to perform a 'destructive deploy' / removal as part of a release. Validates first and gates production with explicit confirmation. DO NOT TRIGGER for local file deletion (use Bash), or for net-new deploys (use platform-metadata-deploy)."
metadata:
  internal: true
  domains: ["Platform"]
  relatedSkills: ["platform-metadata-deploy"]
  cliTools:
    - tool: ["sf"]
      semver: ">=2.0.0"
allowed-tools:
  - Bash
  - Read
  - Write
  - Glob
  - Grep
---

# Handling Destructive Changes

Coordinate metadata deletion against a Salesforce org via the destructiveChanges manifest. Runs in three phases: scope → validate → execute, with stricter guardrails for production.

**Plugin required.** This skill runs commands that ship with its plugin, and a standalone `npx skills add` install doesn't include them. If one of those commands isn't found, or `CLAUDE_PLUGIN_ROOT` is empty, tell the user this skill needs its plugin installed. Don't improvise a replacement for the command. Where a step says what to do when its command fails, do that.

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

### Step 3a — Classify the target org

Classify the target with the plugin's deploy gate, which resolves the org the same way the deploy hook does:

```bash
"${CLAUDE_PLUGIN_ROOT}/scripts/sf-deploy-gate" bucket <alias>
```

Take the **Sandbox / Scratch / Trial path** only when the last line of the output is exactly `sandbox`, `scratch`, or `trial`.
Every other result takes the **Production path** with full confirmation: `production`, `unknown`, empty output, `command not found` or `No such file or directory` (exit 127), an unresolved `${CLAUDE_PLUGIN_ROOT}`, or a non-zero exit with no bucket word.
Don't ask the user what type of org it is, and don't classify the org yourself (with `sf org display`, `sf org list`, or the instance URL).
Judge by the output, not the exit code: `unknown` can come with exit 0 or 2.

Tell the user why the org is treated as production:
- No bucket word: the deploy gate isn't available here (the Salesforce Development plugin isn't installed, or its script couldn't run).
- `unknown`: the org type couldn't be confirmed (usually an incomplete org record, or Python 3 isn't on `PATH`). Re-authenticating with `sf org login web` usually restores the classification.

### Production path

Take this path for every Step 3a result except `sandbox`, `scratch`, or `trial`:
1. Display destructive confirmation banner (mirroring `platform-metadata-deploy`'s production confirmation banner)
2. List EVERY component that will be deleted
3. Require explicit "yes, delete from PRODUCTION" confirmation. Without it, STOP.
4. Reject `--purge-on-delete` unless the user types it explicitly
5. After confirmation, run the deploy command below

When the Salesforce Development plugin is installed, its PreToolUse deploy gate also denies every destructive deploy or delete against an org it classifies as production, even after the confirmation above. It has no override. If it denies the command, show the denial to the user and stop. Don't change the command or retry another way to get past it. Without the plugin there is no hook, and the confirmation above is the only gate.

### Sandbox / Scratch / Trial path

Take this path only when the last line of the Step 3a output is exactly `sandbox`, `scratch`, or `trial`. Run the deploy command below; no production confirmation is needed.

### Deploy command

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
- ALWAYS take the Production path unless the last line of the deploy gate's output is exactly `sandbox`, `scratch`, or `trial`. A missing gate, an error, empty output, or `unknown` means production.
- NEVER ask the user for the org type, or classify the org yourself, to skip the production confirmation
- NEVER add `--purge-on-delete` without explicit user request
- NEVER use `--ignore-errors` on a destructive deploy
- ALWAYS use the API version from `sfdx-project.json`, not a hardcoded value
- If the user is deleting a field with `required="true"` or that's used in `RecordType` picklist values, surface the cascade impact before proceeding
