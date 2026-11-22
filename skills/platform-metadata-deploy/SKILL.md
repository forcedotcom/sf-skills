---
name: platform-metadata-deploy
description: "Salesforce DevOps automation using sf CLI v2. TRIGGER when: user deploys metadata, validates a deploy or does a dry-run, deploys to a Production org, quick-deploys a validated job ID, ships/promotes to prod, creates/manages scratch orgs or sandboxes, sets up CI/CD pipelines, or troubleshoots deployment errors with sf project deploy. DO NOT TRIGGER when: writing Apex code, building LWC components (use experience-lwc-generate), creating metadata definitions (use platform-custom-object-generate), deleting metadata from an org (use platform-destructive-deploy), or querying org data (use platform-data-manage)."
metadata:
  version: "1.2"
  domains: ["Platform", "Developer Experience"]
  relatedSkills:
    - "agentforce-generate"
    - "agentforce-test"
    - "automation-flow-generate"
    - "experience-lwc-generate"
    - "integration-connectivity-connected-app-configure"
    - "integration-connectivity-generate"
    - "platform-apex-test-run"
    - "platform-custom-object-generate"
    - "platform-data-manage"
  cliTools:
    - tool: ["curl"]
      semver: ">=7.0.0"
    - tool: ["git"]
      semver: ">=2.0.0"
    - tool: ["jq"]
      semver: ">=1.7.0"
    - tool: ["sf"]
      semver: ">=2.0.0"
---

# platform-metadata-deploy: Comprehensive Salesforce DevOps Automation

Use this skill when the user needs **deployment orchestration**: dry-run validation, targeted or manifest-based deploys, CI/CD workflow advice, scratch-org management, failure triage, or safe rollout sequencing for Salesforce metadata.

## When This Skill Owns the Task

Use `platform-metadata-deploy` when the work involves:
- `sf project deploy start`, `quick`, `report`, or retrieval workflows
- release sequencing across objects, permission sets, Apex, and Flows
- CI/CD gates, test-level selection, or deployment reports
- troubleshooting deployment failures and dependency ordering

Delegate elsewhere when the user is:
- authoring Apex code (this skill only deploys it)
- authoring LWC components → [experience-lwc-generate](../experience-lwc-generate/SKILL.md)
- creating custom objects or fields → [platform-custom-object-generate](../platform-custom-object-generate/SKILL.md)
- building Flows → [automation-flow-generate](../automation-flow-generate/SKILL.md)
- doing org data operations → [platform-data-manage](../platform-data-manage/SKILL.md)
- authoring or testing Agentforce agents → [agentforce-generate](../agentforce-generate/SKILL.md)

---

## Critical Operating Rules

- Use **`sf` CLI v2 only**.
- On non-source-tracking orgs, deploy/retrieve commands require an explicit scope such as `--source-dir`, `--metadata`, or `--manifest`.
- Prefer **`--dry-run` first** before real deploys.
- **Never run `sf project deploy start` against a production org.** Production goes through the validate → quick-deploy path below (server-side validation returns a 10-day job ID; quick-deploy promotes it without re-running tests, behind an explicit confirmation).
- For Flows, deploy safely and activate only after validation.
- Keep test-data creation guidance delegated to **`platform-data-manage`** after metadata is validated or deployed.

### Default deployment order
| Phase | Metadata |
|---|---|
| 1 | Custom objects / fields |
| 2 | Permission sets |
| 3 | Apex |
| 4 | Flows as Draft |
| 5 | Flow activation / post-verify |

This ordering prevents many dependency and FLS failures.

---

## Required Context to Gather First

Ask for or infer:
- target org alias and environment type
- deployment scope: source-dir, metadata list, or manifest
- whether this is validate-only, deploy, quick deploy, retrieve, or CI/CD guidance
- required test level and rollback expectations
- whether special metadata types are involved (Flow, permission sets, agents, packages)

Preflight checks:
```bash
sf --version
sf org list --skip-connection-status
sf org display --target-org <alias> --json
test -f sfdx-project.json
```

---

## Recommended Workflow

### 1. Preflight
Confirm auth, repo shape, package directories, and target scope.

### 1a. Classify the target org (routes prod vs non-prod)

Before any deploy, classify the target from its `sf org list` record — the path forks on whether the org is **production**. Do NOT classify from `sf org display`: it reports only a plain My Domain and omits the sandbox/scratch/trial fields, so a Sandbox-or-Demo Org (SDO) is misclassified as production (forcedotcom/sf-skills#356). The `sf org list` record carries the real classification booleans. Pass `--skip-connection-status` so this stays a local read that does not refresh an OAuth token per authenticated org (forcedotcom/sf-skills#349):

```bash
sf org list --skip-connection-status --json
```

Find the record whose `alias`, `username`, or `orgId` matches the target, then classify from that record (first match wins):
- **Scratch** — `isScratch` is `true`.
- **Sandbox** — `isSandbox` is `true`, or the `instanceUrl` contains `--` (the My Domain sandbox marker) or `test.salesforce.com`.
- **Trial / Developer Edition** — `trailExpirationDate` (the CLI's spelling; also accept `trialExpirationDate`) is a date in the **future**, or the `instanceUrl` host contains `orgfarm-`, `.develop.my.salesforce.com`, `.pc-rnd.`, or `.scratch.my.salesforce.com`. A past date does not count — the date is cached at login and never refreshed, so a converted trial keeps a stale past date and is not a trial.

Anything else is **production** — including a **Dev Hub** (`isDevHub` is `true`) that shows none of the above signals, since Dev Hub is normally enabled in the customer's own production org. If no record matches or the record has no usable info (no `instanceUrl` and none of the flags), treat it as **unknown** and ask the user before proceeding, rather than assuming production or non-production.

- **Non-production** → the dry-run + deploy path (steps 2–6).
- **Production** → the validate → quick-deploy path ([Production deploys](#production-deploys-validate--quick-deploy)). Never run `sf project deploy start` against production.

### 2. Validate first (non-production)
```bash
sf project deploy start --dry-run --source-dir force-app --target-org <alias> --wait 30 --json
```
Use manifest- or metadata-scoped validation when the change set is targeted.

### 3. If validation succeeds, offer the next safe workflow
After a successful validation, guide the user to the correct next action:
1. deploy now
2. assign permission sets
3. create test data via [platform-data-manage](../platform-data-manage/SKILL.md)
4. run tests / smoke checks
5. orchestrate multiple post-deploy steps in order

### 4. Deploy the smallest correct scope
```bash
# source-dir deploy
sf project deploy start --source-dir force-app --target-org <alias> --wait 30 --json

# manifest deploy
sf project deploy start --manifest manifest/package.xml --target-org <alias> --test-level RunLocalTests --wait 30 --json

# manifest deploy with Spring '26 relevant-test selection
sf project deploy start --manifest manifest/package.xml --target-org <alias> --test-level RunRelevantTests --wait 30 --json
```

### 5. Verify
```bash
sf project deploy report --job-id <job-id> --target-org <alias> --json
```
Then verify tests, Flow state, permission assignments, and smoke-test behavior.

**Check the test count whenever a test level was requested.** A deploy or validation with `--test-level` can return success with `runTestsEnabled: true` and **zero tests run** — no warning (forcedotcom/sf-skills#391). Read the totals from the deploy, validate, or report JSON:

```bash
jq '{status: .result.status, runTestsEnabled: .result.runTestsEnabled, numberTestsTotal: .result.numberTestsTotal, numberTestsCompleted: .result.numberTestsCompleted, numberTestErrors: .result.numberTestErrors}'
```

If `numberTestsTotal` is `0` (or missing) while a test level other than `NoTestRun` was requested, do NOT report tests as passed. Report "deploy succeeded, but 0 tests ran", then run the tests separately with [platform-apex-test-run](../platform-apex-test-run/SKILL.md) and report those results. (`RunRelevantTests` can legitimately select 0 tests for a change with no Apex impact — say so rather than treating it as a pass.)

### 6. Report clearly
Summarize what deployed, what failed, what was skipped, and what the next safe action is.

Output template: [references/deployment-report-template.md](references/deployment-report-template.md)

---

## Production deploys (validate → quick-deploy)

Production is never deployed with `sf project deploy start`. It is a two-step promotion: a **server-side validation** produces a job ID, then a **quick deploy** promotes that validated job without re-running tests, behind an explicit confirmation.

### P1. Validate against production

Production validations REQUIRE a test level. Use `RunLocalTests` by default; switch to `RunSpecifiedTests --tests <ClassName>...` only if the user has explicitly listed tests.

```bash
sf project deploy validate --target-org <alias> --json [scope flags] --test-level RunLocalTests
```

Scope flags — use exactly one: `--source-dir <path>`, `--metadata <Type:Name>`, or `--manifest manifest/package.xml`.

Before treating the validation as good, apply the [test-count check](#5-verify): a validation that ran 0 tests is not a passing validation. The response returns a **job ID** (`result.id`) valid for **10 days**. Persist it **with the target's immutable identity** — the org ID and instance URL from `sf org display`, not just the alias — so the quick deploy can prove the validation belongs to the org it is about to promote to:

```bash
mkdir -p .sfdx
ORG_JSON=$(sf org display --target-org <alias> --json)
ORG_ID=$(printf '%s' "$ORG_JSON" | jq -r '.result.id')
INSTANCE_URL=$(printf '%s' "$ORG_JSON" | jq -r '.result.instanceUrl')
printf '{"jobId":"%s","createdAt":"%s","targetOrg":"%s","orgId":"%s","instanceUrl":"%s","testLevel":"RunLocalTests"}\n' \
  "<id>" "<iso8601>" "<alias>" "$ORG_ID" "$INSTANCE_URL" > .sfdx/last-validation.json
```

On validation failure, triage from `result.details.componentFailures` and `result.details.runTestResult.failures` — surface the top component errors and test failures with a scoped fix direction, then STOP. Never use `--ignore-errors`/`--ignore-warnings` during validation.

### P2. Gate the quick deploy strictly

Before promoting, verify all five:
1. **Target is production** — re-confirm via step 1a's classification.
2. **A validation exists** — read `.sfdx/last-validation.json`, or ask for the job ID, or fall back to `--use-most-recent`. Resolve `--use-most-recent` to a concrete job ID **now** (do not carry it forward as an unresolved flag), so the checks below run against a known job.
3. **Validation belongs to THIS target** — re-run `sf org display --target-org <alias> --json` and require the current `result.id` (org ID) to equal the `orgId` persisted in `.sfdx/last-validation.json`. This closes the stale-cache hazard: a cached job ID resolves its org from the deploy cache, so without this check the banner can show org B while the job promotes to org A. On any mismatch — or if the persisted record lacks an `orgId`/`instanceUrl` to compare — treat it as a **hard stop** and re-validate (P1) against the intended target. Never promote a validation whose target you cannot prove.
4. **Validation is fresh** — explicit `--job-id` ≤ 10 days; a `--use-most-recent` resolution ≤ 3 days. If stale, re-validate (P1) first.
5. **Explicit user confirmation** — print the banner below and require a literal "yes". Populate every banner field from the verified validation record and the just-fetched org data — never from unverified input. Never auto-confirm.

```text
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

`sf org display --json` does not return the edition. Read `<edition>` from the Organization object's `OrganizationType` (e.g. `Enterprise Edition`):

```bash
sf data query --query "SELECT OrganizationType FROM Organization" --target-org <alias> --json | jq -r '.result.records[0].OrganizationType'
```

### P3. Promote and audit

The literal "yes" from P2's banner is the authorization. In the **Salesforce development plugin** context, a PreToolUse hook (`sf-deploy-gate`) blocks a bare production `deploy quick` and only permits it when the command carries the machine-readable confirmation marker `CONFIRM_PROD=1`. Emit that marker to transmit the confirmation the user just gave — it is **not** an independent bypass, so add it **only after** the explicit "yes", never before:

```bash
# plugin context: CONFIRM_PROD=1 relays P2's confirmation to the safety hook
CONFIRM_PROD=1 sf project deploy quick --job-id <validation-id> --target-org <alias> --wait 30 --json
```

Outside the plugin (bare CLI, headless/MCP) there is no such hook — run the same command without the marker.

**Quick deploy starts a new deployment with its own job ID** — it does not reuse the validation ID. Capture the response, extract the new ID, and use *that* for polling, reporting, and the audit filename; keep the validation ID separately for traceability. Stop if the response carries no deployment ID:

```bash
QUICK_RESULT=$(CONFIRM_PROD=1 sf project deploy quick --job-id <validation-id> --target-org <alias> --wait 30 --json)
QUICK_DEPLOY_ID=$(printf '%s' "$QUICK_RESULT" | jq -r '.result.id')
[ -n "$QUICK_DEPLOY_ID" ] && [ "$QUICK_DEPLOY_ID" != "null" ] || { echo "No quick-deploy ID returned — do not report the validation ID as the deploy; investigate."; exit 1; }
```

Quick deploy promotes the validated components and does NOT re-run tests. Persist the report **for the quick-deploy operation** (not the validation) for the audit trail, then guide post-deploy verification (smoke-test critical paths, watch Setup → Deployment Status, prepare a rollback plan if anything regressed):

```bash
mkdir -p .sfdx/deploy-history
sf project deploy report --job-id "$QUICK_DEPLOY_ID" --target-org <alias> --json > ".sfdx/deploy-history/${QUICK_DEPLOY_ID}.json"
```

If quick deploy times out or stays in progress, poll with the **quick-deploy ID**, not the validation ID.

Adding `CONFIRM_PROD=1` after an explicit confirmation is the sanctioned path — it is not "working around" the gate. But never override a denial the user has **not** confirmed, and never override one raised for a different reason — a target mismatch (P2 check 3), a destructive deploy, or an unknown/unresolved org. Surface those denials and stop.

---

## High-Signal Failure Patterns

| Error / symptom | Likely cause | Default fix direction |
|---|---|---|
| `FIELD_CUSTOM_VALIDATION_EXCEPTION` | validation rule or bad test data | adjust data or rule timing |
| `INVALID_CROSS_REFERENCE_KEY` | missing dependency | include referenced metadata first |
| `CANNOT_INSERT_UPDATE_ACTIVATE_ENTITY` | trigger / Flow / validation side effect | inspect automation stack and failing logic |
| tests fail during deploy | broken code or fragile tests | run targeted tests, fix root cause, revalidate |
| field/object not found in permset | wrong order | deploy objects/fields before permission sets |
| Flow invalid / version conflict | dependency or activation problem | deploy as Draft, verify, then activate |

Full workflows: [references/orchestration.md](references/orchestration.md), [references/trigger-deployment-safety.md](references/trigger-deployment-safety.md)

---

## CI/CD Guidance

Default pipeline shape:
1. authenticate
2. validate repo / org state
3. static analysis
4. dry-run deploy
5. tests + coverage gates
6. deploy
7. verify + notify

- When org policy and release risk allow it, consider `--test-level RunRelevantTests` for Apex-heavy deployments.
- Pair this with modern Apex test annotations such as `@IsTest(testFor=...)` and `@IsTest(isCritical=true)`.

Static analysis now uses **Code Analyzer v5** (`sf code-analyzer`), not retired `sf scanner`.

Deep reference: [references/deployment-workflows.md](references/deployment-workflows.md)

---

## Agentforce Deployment Note

Use this skill to orchestrate **deployment/publish sequencing** around agents, but use the agent-specific skill for authoring decisions:
- [agentforce-generate](../agentforce-generate/SKILL.md) for `.agent` authoring, Agent Builder, Prompt Builder, and metadata config

For full agent DevOps details, including `Agent:` pseudo metadata, publish/activate, and sync-between-orgs, see:
- [references/agent-deployment-guide.md](references/agent-deployment-guide.md)

---

## Cross-Skill Integration

| Need | Delegate to | Reason |
|---|---|---|
| custom object / field creation | [platform-custom-object-generate](../platform-custom-object-generate/SKILL.md) | define objects and fields before deploy |
| run tests after deployment | [platform-apex-test-run](../platform-apex-test-run/SKILL.md) | post-deploy test execution and coverage |
| Flow creation / repair | [automation-flow-generate](../automation-flow-generate/SKILL.md) | Flow authoring and activation guidance |
| test data or seed records | [platform-data-manage](../platform-data-manage/SKILL.md) | describe-first data setup and cleanup |
| Agent authoring and publish readiness | [agentforce-generate](../agentforce-generate/SKILL.md) | agent-specific correctness |

---

## Reference Map

### Start here
- [references/orchestration.md](references/orchestration.md)
- [references/deployment-workflows.md](references/deployment-workflows.md)
- [references/deployment-report-template.md](references/deployment-report-template.md)

### Specialized deployment safety
- [references/trigger-deployment-safety.md](references/trigger-deployment-safety.md)
- [references/agent-deployment-guide.md](references/agent-deployment-guide.md)
- [references/deploy.sh](references/deploy.sh)

### Asset templates
- [assets/package.xml](assets/package.xml) — manifest template covering common metadata types
- [assets/destructiveChanges.xml](assets/destructiveChanges.xml) — template for removing metadata from target orgs

---

## Score Guide

| Score | Meaning |
|---|---|
| 90+ | strong deployment plan and execution guidance |
| 75–89 | good deploy guidance with minor review items |
| 60–74 | partial coverage of deployment risk |
| < 60 | insufficient confidence; tighten plan before rollout |

---

## Completion Format

```text
Deployment goal: <validate / deploy / retrieve / pipeline>
Target org: <alias>
Scope: <source-dir / metadata / manifest>
Result: <passed / failed / partial>
Key findings: <errors, ordering, tests, skipped items>
Next step: <safe follow-up action>
```
