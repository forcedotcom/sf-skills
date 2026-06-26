---
name: running-devops-test-suite
description: "Triggers async execution of one or more DevOps Center test suites on a pipeline stage (Pre-Promote, Post-Promote, or Review event) via the Connect API, after an explicit user confirmation gate, then hands off to result polling via the `polling-test-results` skill. Also re-runs (retriggers) a quality gate after fixes — but only once validation confirms the coverage threshold is now met. TRIGGER when: the user wants to run, kick off, or launch test suites on a pipeline stage; execute tests before or after a promotion; trigger a Pre-Promote, Post-Promote, or Review-event run; re-run a quality gate after fixing failures; retry a failed gate once coverage is met; or unblock a blocked promotion after adding tests. DO NOT TRIGGER when: running sf apex run test directly (use platform-apex-test-run); or configuring a NEW gate or threshold (use configuring-quality-gate)."
metadata:
  version: "1.0"
  minApiVersion: "67.0"
---

# Running a DevOps Center Test Suite

## Prerequisites

Load and follow `checking-devops-prerequisites` first — run Prerequisites 1–4 AND Prerequisite 5 (pipeline stage), since this skill operates on a specific stage. You need the confirmed `doce-org-alias`, `pipelineId`, and `stageId` before proceeding.

## Inputs required before calling this skill

| Input | How to obtain |
|---|---|
| `pipelineId` | From Prerequisite 4 (pipeline selection) |
| `stageId` | From Prerequisite 5 (pipeline stage confirmation) |
| `event` | Confirm with user: `Pre-Promote` or `Post-Promote` (or `Review` if the context is a review environment) |
| `testSuiteIds` | Confirmed suite IDs from the suite selection or recommendation step |
| `doce-org-alias` | Established in Prerequisite 1 |

## Confirmation gate

**This call mutates org state — do not proceed without explicit user confirmation.**

Before calling the API, show the user:

> "I'm about to run tests with the following configuration:
> - Pipeline: `<pipelineName>`
> - Stage: `<stageName>`
> - Event: `<event>`
> - Suite(s): `<suiteName(s)>`
> - Org: `<doce-org-alias>`
>
> Shall I proceed?"

Do not make the API call until the user confirms.

## API call

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

### Body schema

| Field | Type | Description |
|---|---|---|
| `stageId` | string | The ID of the pipeline stage to execute tests on |
| `event` | string | `Pre-Promote`, `Post-Promote`, or `Review` |
| `testSuiteIds` | string[] | One or more test suite IDs to execute |

## On success

Extract the `runId` (or execution ID) from the response. Inform the user:

> "Tests are running in `<doce-org-alias>`. I'll update you when results are ready."

Immediately hand off the `runId` to the `polling-test-results` skill to begin the polling loop.

## On error

| Status | Message to user |
|---|---|
| 400 | "The test execution request was invalid. Check that the stage and suite IDs are correct." |
| 403 | "You don't have permission to run tests on this pipeline. Check your DevOps Testing API access." |
| 404 | "The pipeline or stage was not found. It may have been deleted." |
| 500 | "The DevOps Center org returned a server error. Try again in a few minutes." |

Never expose raw API errors to the user.

---

## Retrigger mode (re-running a quality gate)

Use this mode when a promotion was blocked by a quality gate failure and the coverage gap has since been addressed.

### Extra preconditions — all must be true before proceeding

1. The `Coverage` field on the latest `DevopsTestSuiteExecution` meets or exceeds the threshold defined in the `DevopsQualityGateRule`
2. The user has explicitly asked to retrigger the gate
3. The same `pipelineId`, `stageId`, and `event` from the blocked promotion are known

If coverage is still below threshold, do **not** retrigger. Instead, respond:

> "Coverage is still at `<X>%`, below the `<threshold>%` gate. The gate cannot be retriggered until the threshold is met. Here are the remaining uncovered methods: `<list>`."

Do not retry. Explain what must be resolved first and stop.

### Inputs required for retrigger

| Input | Source |
|---|---|
| `pipelineId` | From the blocked promotion context |
| `stageId` | From the blocked promotion context |
| `event` | Same event type that originally blocked (`Pre-Promote` or `Post-Promote`) |
| `suiteIds` | Same suites that were originally run |
| `doce-org-alias` | Established in Prerequisite 1 |

### Confirmation gate (retrigger)

Before executing the API call, present this confirmation prompt and wait for explicit user approval:

> "Coverage is confirmed at `<X>%`, which meets the `<threshold>%` gate. I'll retrigger the quality gate check for the `<stageName>` stage (`<event>`). Confirm?"

Only proceed after the user confirms. If the user declines, stop without making any API call.

### API call (retrigger)

Uses the same Connect API stage/execute endpoint:

```bash
sf api request rest "/services/data/v67.0/connect/devopstesting/pipeline/<pipelineId>/stage/execute" --method POST --body '{"stageId":"<stageId>","event":"<event>","testSuiteIds":["<suiteId1>"]}' --target-org <doce-org-alias>
```

After the call returns a `runId`, hand off to the `polling-test-results` skill with the new `runId` to monitor the execution result.

### Error handling (retrigger)

If the API returns an error indicating the gate cannot be retriggered, respond with:

> "The quality gate cannot be retriggered right now. Reason: `<plain-language summary>`. Here's what needs to be resolved first: `<list>`."

Never expose raw API error details to the user.

---

## Related skills

- **`polling-test-results`** — poll for async run results after receiving the `runId`
- **`recommending-devops-tests`** — recommend which suites to run first before triggering execution
- **`managing-suite-assignments`** — assign or map a suite to a pipeline stage if it isn't linked yet
- **`configuring-quality-gate`** — configure a new gate or threshold
