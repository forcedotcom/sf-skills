---
name: dx-devops-test-suite-run
description: "Runs DevOps Center test suites on a pipeline stage (Pre-Promote, Post-Promote, or Review event) end to end: triggers async execution via the Connect API after an explicit confirmation gate, then polls by runId at provider-specific intervals until it completes, fails, or times out, and hands results to failure analysis. Also retriggers a quality gate after fixes, but only once coverage meets the threshold. Use this skill when a user wants to run, kick off, or launch test suites on a stage, re-run a quality gate, or watch an in-progress run to completion. TRIGGER when: the user wants to run/launch suites on a stage, execute tests before or after promotion, re-run a quality gate after fixing failures, unblock a blocked promotion after adding tests, or poll/watch an in-progress run. DO NOT TRIGGER when: running sf apex run test directly (use platform-apex-test-run), or configuring a NEW gate or threshold (use dx-devops-test-pipeline-configure)."
metadata:
  cliTools:
    - tool: ["sf"]
      semver: ">=2.67.0"
  relatedSkills:
    - "dx-devops-test-failures-analyze"
    - "dx-devops-test-pipeline-configure"
    - "dx-devops-test-suite-assignments-configure"
    - "platform-apex-test-run"
  version: "1.0"
  domains: ["Developer Experience"]
  minApiVersion: "67.0"
---

# Run a DevOps Center Test Suite

Triggers a DevOps Center test suite execution and watches it to completion. Running and polling are two halves of one operation — never poll without first having (or being handed) a `runId`.

> **API version:** All DevOps testing system calls target Salesforce API **v67.0** (minimum required).

**Important:** All DevOps Center data lives in the Salesforce org — NOT the local repo. Always query the org with `sf data query` or `sf api request rest`.

---

## Prerequisites

Run the prerequisite checks in `references/prerequisite-checks.md` — Prerequisites 1–4 **and** Prerequisite 5 (stage), since this skill operates on a specific stage. You need the confirmed `doce-org-alias`, `pipelineId`, and `stageId`.

## Inputs required

| Input | How to obtain |
|---|---|
| `pipelineId` | Prerequisite 4 (pipeline selection) |
| `stageId` | Prerequisite 5 (pipeline stage confirmation) |
| `event` | Confirm with user: `Pre-Promote`, `Post-Promote`, or `Review` |
| `testSuiteIds` | Confirmed suite IDs from selection or recommendation |
| `doce-org-alias` | Prerequisite 1 |

---

## Step 1 — Trigger execution

### Confirmation gate

**This call mutates org state — do not proceed without explicit user confirmation.** Before calling the API, show:

> "I'm about to run tests with the following configuration:
> - Pipeline: `<pipelineName>`
> - Stage: `<stageName>`
> - Event: `<event>`
> - Suite(s): `<suiteName(s)>`
> - Org: `<doce-org-alias>`
>
> Shall I proceed?"

Do not make the API call until the user confirms.

### API call

```bash
sf api request rest \
  "/services/data/v67.0/connect/devopstesting/pipeline/<pipelineId>/stage/execute" \
  --method POST \
  --body '{
    "stageId": "<stageId>",
    "event": "<event>",
    "testSuiteIds": ["<suiteId1>", "<suiteId2>"]
  }' \
  --target-org <doce-org-alias>
```

| Field | Type | Description |
|---|---|---|
| `stageId` | string | The ID of the pipeline stage to execute tests on |
| `event` | string | `Pre-Promote`, `Post-Promote`, or `Review` |
| `testSuiteIds` | string[] | One or more test suite IDs to execute |

### On success

Extract the `runId` (execution ID) from the response. Inform the user:

> "Tests are running in `<doce-org-alias>`. I'll update you when results are ready."

Then proceed **immediately** to Step 2 (polling) with the `runId`.

### On error

See `references/error-handling.md`. If the org rejects execution (e.g. `environmentId: null`, or `classIdList is null or empty — no tests to execute`), read the actual error, explain the root cause and required fix in plain language, and finish cleanly. **Do not retry in a loop and do not fabricate a `runId` or results.**

---

## Step 2 — Poll until completion

**Confirmation required:** No — polling is automatic and read-only.

Poll the execution record by `runId` at the provider-appropriate interval. Full intervals, timeout behavior, and the poll query are in `references/polling-configuration.md`.

Summary of the loop (the `runId` is a `DevopsTestSuiteExecution` Id — poll that object, not `DevopsTestExecution`):
- Query `DevopsTestSuiteExecution` by `runId` each interval for `Status, Coverage, SuccessCount, FailureCount, QualityGateStatus`.
- `InProgress` → wait and poll again.
- `Passed` / `Failed` → surface `Coverage`, `SuccessCount`, `FailureCount`, and `QualityGateStatus` inline (no raw JSON). If `FailureCount > 0`, fetch the child `DevopsTestExecution` failure rows and hand off to **`dx-devops-test-failures-analyze`**.
- `Error` → the run itself errored (not test failures); surface `ResultDetails`/`Message` in plain language and offer retry or skip.
- **Timeout** → surface the `runId`, do NOT auto-retry, wait for user instruction.

---

## Retrigger mode (re-running a quality gate)

Use when a promotion was blocked by a gate failure and the coverage gap has since been addressed. **All preconditions, gate, and the retrigger API call are in `references/retrigger-mode.md`.** Key rule: do **not** retrigger unless the latest `Coverage` meets or exceeds the `DevopsQualityGateRule` threshold. After the retrigger returns a new `runId`, hand it to Step 2 (polling).

---

## Related skills

- **`dx-devops-test-failures-analyze`** — receives the failure payload on completion; can also create a fix work item.
- **`dx-devops-test-suite-assignments-configure`** — recommend which suites to run, or assign a suite to the stage if it isn't linked yet.
- **`dx-devops-test-pipeline-configure`** — configure a new quality gate or threshold (this skill only re-runs existing gates).
