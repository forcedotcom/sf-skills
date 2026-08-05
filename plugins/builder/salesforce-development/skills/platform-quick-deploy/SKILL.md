---
name: platform-quick-deploy
description: "Deploy validated metadata to a Production Salesforce org without re-running tests. TRIGGER when the user wants to deploy to production, says 'quick deploy', 'promote', 'ship to prod', or has just validated and wants to push the change live. REQUIRES a recent `sf project deploy validate` job ID (≤10 days old, ≤3 days for --use-most-recent). DO NOT TRIGGER for sandbox/scratch deploys (use platform-metadata-deploy) or unvalidated deploys (use platform-deploy-validate first)."
allowed-tools:
  - Bash
  - Read
---

# Quick Deploying to Prod

Promote a validated deploy to a Production org using the job ID from a prior `sf project deploy validate`. No tests re-run, no components re-validated — just the promotion.

## Preconditions (gate strictly)

Before doing ANYTHING, verify all four:

1. **Target is Production**
   ```bash
   sf org display --target-org <alias> --json
   ```
   Confirm the target really is production. The reliable check is the gate's classifier (returns `production|sandbox|scratch|trial|devhub|unknown`):
   ```bash
   sf org display --target-org <alias> --json | "${CLAUDE_PLUGIN_ROOT}/scripts/sf-deploy-gate" classify
   ```
   Production means `isSandbox=false` AND `isScratch=false` AND instance URL has no `--` (sandbox marker) AND no `test.salesforce.com` **AND it is not a trial/Developer Edition host** (`orgfarm-*`, `*.develop.my.salesforce.com`, `*.pc-rnd.*`, or a `trialExpirationDate` in the response — these report `isSandbox`/`isScratch` as `null` and must not be taken for production).

   If target is NOT production (classifier returns anything other than `production`) → STOP and redirect to `platform-metadata-deploy` (which handles non-prod natively).

2. **A validation exists**
   - Read `.sfdx/last-validation.json` if it exists (left there by `platform-deploy-validate`)
   - OR ask the user for the job ID
   - OR fall back to `--use-most-recent` (validates within last 3 days)

3. **Validation is fresh enough**
   - Explicit `--job-id`: must be ≤10 days old per Salesforce's quick-deploy window
   - `--use-most-recent`: must be ≤3 days old
   - If the recorded `createdAt` exceeds the window → STOP and run `platform-deploy-validate` first

4. **Explicit user confirmation**
   - Print a confirmation block (alias, instance URL, edition, validated component count, test results) and ask: "Confirm deploy to PRODUCTION? (yes/no)"
   - Do NOT proceed without an explicit "yes"

## Workflow

### Step 1 — Display the production confirmation banner

Format exactly:

```
┌─ PRODUCTION DEPLOY ─────────────────────────────┐
│ Org alias:      <alias>                         │
│ Instance:       <instanceUrl>                   │
│ Edition:        <edition>                       │
│ Validation ID:  <jobId>                         │
│ Validated:      <createdAt> (X days ago)        │
│ Components:     <componentCount> queued         │
│ Tests:          <run>/<passed>/<failed>         │
└─────────────────────────────────────────────────┘
Confirm deploy to PRODUCTION? (yes/no)
```

### Step 2 — Run the quick deploy

After "yes":

```bash
sf project deploy quick --job-id <id> --target-org <alias> --wait 30 --json
```

Or with `--use-most-recent` if the user opted in.

The quick deploy will:
- Promote the validated components to the org
- NOT re-run tests (per Salesforce platform behavior)
- Return final deploy status

### Step 3 — Capture the deploy report

After completion, persist for audit:

```bash
mkdir -p .sfdx/deploy-history
sf project deploy report --job-id <id> --target-org <alias> --json > ".sfdx/deploy-history/<id>.json"
```

Surface to the user:
- ✅ Deploy succeeded — components deployed, time taken
- ⚠️ Deploy failed — error summary; recommend looking at the report

### Step 4 — Post-deploy guidance

After a successful prod deploy, suggest:
- Smoke-test critical paths in the org (provide direct URLs if known)
- Monitor the prod environment for the next 30 min
- Check Setup → Deployment Status to confirm
- If anything regressed: prepare a rollback plan (re-deploy the previous version's package)

## Rules

- NEVER run `sf project deploy start` against a Production target (always validate then quick-deploy)
- NEVER use `--ignore-errors` or `--ignore-warnings` on production
- NEVER auto-confirm — require an explicit "yes" from the user
- NEVER quick-deploy a job ID older than its validity window — re-validate instead
- ALWAYS persist the deploy report to `.sfdx/deploy-history/` for the audit trail
- If the prod-check hook denies the operation, do NOT bypass it — surface the denial to the user and recommend `platform-deploy-validate` first
