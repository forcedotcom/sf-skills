# Mode C — Configure a Quality Gate

Creates a DevOps Center quality gate with associated rules (`PASS_PERCENTAGE`, `SEVERITY`, `ESSENTIAL`) and links it to a pipeline-stage suite assignment, after a mandatory impact preview and explicit confirmation.

## Prerequisites

Run Prerequisites 1–4 **and** Prerequisite 5 (stage). You need `doce-org-alias`, `pipelineId`, and `stageId`. Prereq 5 resolves only the **`DevopsPipelineStage`** — it does **not** give you the `DevopsTestSuiteStage` record. Resolve that separately in Step 0 below.

## Inputs required

| Input | Source |
|---|---|
| `name` | User-provided name for the quality gate |
| `rules` | List of `{type, threshold?}` — see rule types below |
| `doce-org-alias` | Prerequisite 1 |
| `event` | `Pre-Promote`, `Post-Promote`, or `Review` — which trigger the gate applies to |
| `testSuiteName` | The suite the gate will gate (the gate links to a specific suite-on-stage) |
| `testSuiteStageId` | Target `DevopsTestSuiteStage` record Id — **resolved in Step 0**, not from Prereq 5 |

---

## Step 0 — Resolve the target `DevopsTestSuiteStage` record

A quality gate links to a specific suite assigned to a stage's trigger, represented by a `DevopsTestSuiteStage` record. That object is keyed by `DevopsPipelineStageTriggerId` + `TestSuiteId` (it is **not** linked directly to `DevopsPipelineStage`), so resolve it in two queries.

**0a — Find the stage's trigger for the chosen event:**

```bash
sf data query \
  --query "SELECT Id, TriggerType FROM DevopsPipelineStageTrigger WHERE RelatedRecordId = '<stageId>' AND TriggerType = '<event>'" \
  --target-org <doce-org-alias> --json
```

> For a `Review` gate the trigger is pipeline-level — use `RelatedRecordId = '<pipelineId>'` with `TriggerType = 'Review'` instead. Record the returned Id as `<triggerId>`.

**0b — Find the suite-stage row for the target suite on that trigger:**

```bash
sf data query \
  --query "SELECT Id, TestSuiteId, TestSuite.Name, IsQualityGateEnabled, DevopsQualityGateId FROM DevopsTestSuiteStage WHERE DevopsPipelineStageTriggerId = '<triggerId>'" \
  --target-org <doce-org-alias> --json
```

Match the row whose `TestSuite.Name` is the suite the user named; its `Id` is `<testSuiteStageId>`.

- If **no** `DevopsTestSuiteStage` row matches (the suite isn't assigned to that trigger), stop and report it — the suite must be assigned first via `dx-devops-test-suite-assignments-configure`. Do **not** fabricate a `testSuiteStageId` or proceed.
- If the matched row already has `IsQualityGateEnabled = true`, tell the user a gate is already linked and confirm whether to replace it before continuing.

## Rule types

| Type | Description | Threshold |
|---|---|---|
| `PASS_PERCENTAGE` | Minimum % of tests that must pass | Required (0–100) |
| `SEVERITY` | Maximum allowed severity level of failures | Required (numeric, e.g. 1–5) |
| `ESSENTIAL` | All essential tests must pass | Not required |

---

## MANDATORY IMPACT PREVIEW

**Before executing any commands**, show the user this preview and wait for explicit confirmation:

> "Here's what this quality gate will enforce on `<stageName>`:
> - Rule: `<type>` — `<description>`
> - Threshold: `<value>`
> - Affected pipelines: `<list>`
>
> Confirm to apply?"

**Never proceed past this point without showing the impact preview first and receiving explicit confirmation.**

## Confirmation gate

Only proceed after the user has explicitly confirmed (e.g., "yes", "confirm", "go ahead"). If the user declines or does not confirm, stop and do not execute any commands.

---

## Step 1 — Create the gate record

```bash
sf api request rest \
  "/services/data/v67.0/connect/devopstesting/qualityGate" \
  --method POST \
  --body '{"name": "<gateName>"}' \
  --target-org <doce-org-alias>
```

Extract `qualityGateId` from the response.

## Step 2 — Create each rule as an sObject record

Rules are not accepted in the Connect API payload — create them as `DevopsQualityGateRule` records directly. Only create rules the user has requested. `ESSENTIAL` has no threshold.

```bash
sf data create record \
  --sobject DevopsQualityGateRule \
  --values "DevopsQualityGateId='<qualityGateId>' Rule='PASS_PERCENTAGE' Threshold=<value>" \
  --target-org <doce-org-alias> --json

sf data create record \
  --sobject DevopsQualityGateRule \
  --values "DevopsQualityGateId='<qualityGateId>' Rule='ESSENTIAL'" \
  --target-org <doce-org-alias> --json

sf data create record \
  --sobject DevopsQualityGateRule \
  --values "DevopsQualityGateId='<qualityGateId>' Rule='SEVERITY' Threshold=<value>" \
  --target-org <doce-org-alias> --json
```

## Step 3 — Link the gate to the suite stage

Update the `DevopsTestSuiteStage` record to link the new gate:

```bash
sf data update record \
  --sobject DevopsTestSuiteStage \
  --record-id <testSuiteStageId> \
  --values "IsQualityGateEnabled=true DevopsQualityGateId='<qualityGateId>'" \
  --target-org <doce-org-alias> --json
```

---

## On success

> "Quality gate `<gateName>` created with `<N>` rule(s) and assigned to `<suiteName>` on `<stageName>`."

## Note

To *re-run* an existing gate after meeting its threshold, that is **not** this mode — use `dx-devops-test-suite-run` (retrigger mode). To assign or map suites to stages first, use `dx-devops-test-suite-assignments-configure`.

See `references/error-handling.md` for status-code responses.
