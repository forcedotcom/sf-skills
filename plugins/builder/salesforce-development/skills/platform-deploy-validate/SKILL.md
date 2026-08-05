---
name: platform-deploy-validate
description: "Validate Salesforce metadata before deploying. TRIGGER when the user asks to validate a deploy, do a dry-run, check before deploying, or targets a Production org for any deploy operation. Routes prod targets to `sf project deploy validate` (returns a 10-day quick-deploy job ID) and sandbox/scratch targets to `sf project deploy start --dry-run`. DO NOT TRIGGER for actual deploys (use platform-metadata-deploy) or destructive changes (use platform-destructive-deploy)."
allowed-tools:
  - Bash
  - Read
  - Write
metadata:
  cliTools:
    - tool: ["sf"]
      semver: ">=2.0.0"
  relatedSkills:
    - "platform-metadata-deploy"
    - "platform-destructive-deploy"
    - "platform-quick-deploy"
---

# Validating Deployment

Run a server-side validation before deploying metadata. Validation surfaces errors without modifying the org and — for production targets — produces a job ID usable with `platform-quick-deploy` for a fast, test-free deploy.

## Capability Resolution

Always prefer `sf project deploy validate` (prod) or `sf project deploy start --dry-run` (sandbox/scratch) over the Tooling API directly.

## Workflow

### Step 1 — Confirm the target org

Classify the org with the gate's classifier — it is the authoritative source of truth (it handles sandbox/scratch markers, trial and Developer Edition hosts, and dev hubs, and returns one of `production|sandbox|scratch|trial|devhub|unknown`):

```bash
sf org display --target-org <alias> --json | "${CLAUDE_PLUGIN_ROOT}/scripts/sf-deploy-gate" classify
```

Only `production` takes the production path (Step 2b); every other result takes the sandbox/scratch path (Step 2a).

### Step 2a — Sandbox/Scratch path (dry-run)

```bash
sf project deploy start --dry-run --target-org <alias> --json [scope flags]
```

Scope flags (use exactly one, not all):
- `--source-dir <path>` — deploy a directory
- `--metadata <Type:Name>` — deploy specific components
- `--manifest manifest/package.xml` — deploy from manifest

Default test level: omit `--test-level` for sandboxes (defers to org default). Add `--test-level RunLocalTests` only if the user asks.

Report back: success/failure, components attempted, any errors. **No job ID is returned** for dry-runs (this is expected).

### Step 2b — Production path (validate)

```bash
sf project deploy validate --target-org <alias> --json [scope flags] --test-level RunLocalTests
```

Production validations REQUIRE a test level. Use `RunLocalTests` by default; switch to `RunSpecifiedTests --tests <ClassName>...` if the user has explicitly listed tests.

The response returns a **job ID** (`result.id`) valid for **10 days**. Persist it for `platform-quick-deploy`:

```bash
mkdir -p .sfdx
echo '{"jobId":"<id>","createdAt":"<iso8601>","targetOrg":"<alias>","testLevel":"RunLocalTests"}' > .sfdx/last-validation.json
```

Report:
- Validation result (passed / failed)
- Job ID and 10-day expiry date
- Test results summary (run / passed / failed)
- Recommended next step: `platform-quick-deploy` with this job ID

### Step 3 — Failure triage

If validation fails, parse `result.details.componentFailures` and `result.details.runTestResult.failures` and surface:
- Top 5 component errors with full message
- Top 5 test failures with stack
- Suggested fix (component name → likely cause: missing dependency, FLS, syntax, etc.)

Do NOT propose fixes that change unrelated metadata. Stay scoped to what the validation reported.

## Rules

- ALWAYS use `--json` on every CLI call
- NEVER skip validation when targeting Production (do not run `sf project deploy start` against prod from this skill)
- NEVER use `--ignore-errors` or `--ignore-warnings` during validation; those flags belong to actual deploys, not validation
- If the user asks to "deploy to prod" without prior validation, FIRST run validation, THEN hand off to `platform-quick-deploy` (do not start a regular deploy against prod)
- Persist the validation job ID to `.sfdx/last-validation.json` so the quick-deploy skill can find it

## Output

Always end with:
- ✅ Validation passed → next-step pointer to `platform-quick-deploy` (with job ID + expiry) OR to `platform-metadata-deploy` for non-prod
- ❌ Validation failed → categorized error list and suggested next iteration
