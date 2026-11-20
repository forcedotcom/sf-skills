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

If the validate command times out, or its JSON has no `result.id`, don't guess a job ID. Check the job ID the output names with `sf project deploy report --job-id <id> --json`, and STOP unless that shows a successful validation.

If `--purge-on-delete` is wanted, add it to this validate command. On production the deletion runs as a quick deploy of this validation. Quick deploy has no `--purge-on-delete` flag of its own, so purge can only be requested on this validation.

Keep this command synchronous: don't add `--async`. The job ID and test count below come from its final JSON output.

If validation succeeds, keep two values from its JSON output and show both to the user:
- `result.id`: the validation job ID. The Production path promotes this job.
- `result.numberTestsTotal`: how many Apex tests the validation ran. If it is missing or not a number, treat it as 0.

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

Take this path for every Step 3a result except `sandbox`, `scratch`, or `trial`. On production, a deletion runs only as a quick deploy of the Phase 2 validation, never as `sf project deploy start`.

Check the validation's test count from Phase 2 first:
- Above 0: follow the steps below.
- 0: Salesforce won't quick-deploy a validation that ran no Apex tests. Before you ask for any confirmation, tell the user, and take the **No-test handoff** below instead of these steps.

1. Display destructive confirmation banner (mirroring `platform-metadata-deploy`'s production confirmation banner)
2. List EVERY component that will be deleted, the validation job ID, and the number of tests it ran
3. Require explicit "yes, delete from PRODUCTION" confirmation. Without it, STOP.
   On Codex, the user's single reply `yes, confirm production deploy to <alias>` replaces this phrase. That confirmation works once, only in this session, and expires after 10 minutes. Ask for it only after Phase 2 validation has finished. If it has expired, or the gate says it was already used, ask for it again.
4. Reject `--purge-on-delete` unless the user types it explicitly. If they ask for it only now, re-run Phase 2 with it, because quick deploy can't add it. Then go back to step 2 and show the new job ID and test count, and ask step 3's confirmation again. The earlier confirmation covered the old job.
5. After confirmation, promote the validated job:

```bash
CONFIRM_PROD=1 sf project deploy quick --job-id <validation-id> --target-org <alias> --wait 30 --json
```

`CONFIRM_PROD=1` passes the user's confirmation on to the plugin's deploy gate. Add it only after the user confirms, never before. Without the plugin, run the same command without it. On Codex, the deploy gate ignores `CONFIRM_PROD=1` and accepts only the user's reply from step 3, so run the command without it.

Quick deploy starts a new job with its own ID. Report that ID, not the validation ID.

If the quick deploy times out or fails with any error, find out what happened before you do anything else. "Job ID can't be used for quick deployment" can mean the validation expired, or that it was already deployed.
- If the output gave a quick-deploy job ID, run `sf project deploy report --job-id <quick-job-id> --json` (or `sf project deploy resume --job-id <quick-job-id> --json` to wait for it).
- If it gave none, check whether the components still exist with `sf org list metadata --metadata-type <type> --target-org <alias> --json`.

Never retry with `sf project deploy start`, and never re-run the quick deploy without checking first. Then:
- The deletion went through: report the quick-deploy job ID and continue with Phase 4.
- It did not, and the validation ran 0 tests: take the No-test handoff.
- It did not, and the validation is more than 10 days old: tell the user, and re-run Phase 2.
- Anything else, or you can't tell: tell the user what you found and what is unclear, and stop.

When the Salesforce Development plugin is installed, its PreToolUse deploy gate denies `sf project deploy start` with destructive changes, and `sf project delete`, against an org it classifies as production, even after the confirmation above. If the gate denies a command, show the denial to the user and stop. Don't change the command or retry another way to get past it. Without the plugin there is no hook, and the confirmation above is the only gate.

#### No-test handoff

The agent can't finish this deletion. Tell the user so before you ask for any confirmation, and give them:
- the reason: the validation ran 0 Apex tests, so Salesforce won't quick-deploy it, and the plugin's deploy gate blocks every other way the agent could delete from production;
- every component the command deletes;
- the exact command to run themselves, in their own terminal outside this session. Use the same destructive-changes flag and file as Phase 2. Add `--purge-on-delete` only if they asked for it:

```bash
sf project deploy start \
  --pre-destructive-changes manifest/destructiveChangesPre.xml \
  --manifest manifest/package.xml \
  --target-org <alias> \
  --test-level RunLocalTests \
  --wait 30
```

Don't run it yourself. Don't ask for "yes, delete from PRODUCTION". Don't try another route, such as `sf project delete`, a different test level, or the Metadata API. When the user says it finished, continue with Phase 4.

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
- NEVER run `sf project deploy start` with destructive changes against production. Promote the validated job with a confirmed quick deploy, or, if the validation ran 0 tests, give the user the command to run themselves
- ALWAYS take the Production path unless the last line of the deploy gate's output is exactly `sandbox`, `scratch`, or `trial`. A missing gate, an error, empty output, or `unknown` means production.
- NEVER ask the user for the org type, or classify the org yourself, to skip the production confirmation
- NEVER add `--purge-on-delete` without explicit user request
- NEVER use `--ignore-errors` on a destructive deploy
- ALWAYS use the API version from `sfdx-project.json`, not a hardcoded value
- If the user is deleting a field with `required="true"` or that's used in `RecordType` picklist values, surface the cascade impact before proceeding
