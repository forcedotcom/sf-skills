---
name: managing-suite-assignments
description: "Manages all forms of test suite assignment for DevOps Center pipeline stages via the Connect API testSuiteStages endpoint. Covers three modes: (A) attaching a single suite to a stage as a one-off add, (B) bulk-mapping multiple suites to a stage as a testing strategy with a mandatory impact-preview table before any changes, and (C) adding or removing individual test classes within a suite assignment with governance rules that exclude rejected tests and re-present the final list before committing. TRIGGER when: a suite is found unlinked from a pipeline stage and the user wants to assign it; the user wants to configure suite-to-stage mappings across a pipeline or assign multiple suites to stages as part of a testing strategy; the user wants to add or remove tests in a suite, sync reviewed tests into a suite, or promote tests to a suite. DO NOT TRIGGER when: authoring new test classes (use platform-apex-test-generate) or running tests directly (use platform-apex-test-run)."
metadata:
  version: "1.0"
  minApiVersion: "67.0"
---

# Managing Suite Assignments

## Prerequisites

Load `checking-devops-prerequisites` first — Prerequisites 1–4 AND Prerequisite 5 (stage). You need `doce-org-alias`, `pipelineId`, and `stageId` before proceeding in any mode.

| Variable | Description |
|---|---|
| `doce-org-alias` | Established in Prerequisite 1 |
| `pipelineId` | Identified in Prerequisite 4 (pipeline selection) |
| `stageId` | Identified in Prerequisite 5 (stage selection) |
| `event` | `Pre-Promote`, `Post-Promote`, or `Review` |

---

## Mode A — Assign a single suite to a stage

Use this mode when a relevant test suite already exists but is not yet linked to a pipeline stage and the user wants to add it as a single one-off assignment.

**Additional inputs required:**

| Variable | Description |
|---|---|
| `testSuiteId` | ID of the suite to assign |
| `testSuiteName` | Name of the suite (for display in confirmation) |

**Confirmation gate**

**Confirmation required before any API call is made.**

Present the following prompt to the user and wait for an affirmative response:

> "The suite `<testSuiteName>` is not currently assigned to the `<stageName>` stage (`<event>`). Would you like me to assign it now?"

Do not proceed until the user confirms.

**On success**

Report to the user:

> "Suite `<testSuiteName>` has been assigned to the `<stageName>` stage (`<event>`)."

---

## Mode B — Map multiple suites to a stage

Use this mode when configuring suite-to-stage mappings across a pipeline or assigning multiple suites to stages as part of a testing strategy.

**Additional inputs required:**

| Input | Description |
|---|---|
| `testSuiteOperations` | List of `{testSuiteId, action: "add"\|"remove"}` |

**MANDATORY IMPACT PREVIEW — Required Before Any Changes**

**Do not call the API until the user has confirmed the preview below.**

Present the full mapping summary and wait for explicit confirmation:

> "Here's the suite mapping I'll apply:
>
> | Suite | Stage | Event | Action |
> |---|---|---|---|
> | `<suiteName>` | `<stageName>` | `<event>` | Add |
> | `<suiteName2>` | `<stageName>` | `<event>` | Remove |
>
> Confirm to apply all changes?"

Only proceed after the user explicitly confirms.

**On success**

> "Suite mapping applied. `<N>` suite(s) updated for the `<stageName>` stage."

---

## Mode C — Add/remove test classes in a suite

Use this mode when the user wants to add or remove individual test classes within an existing suite assignment, sync reviewed tests into a suite, or promote tests to a suite.

**Additional inputs required:**

| Input | Source |
|---|---|
| `testSuiteOperations` | List of `{testSuiteId, action: "add"\|"remove"}` |

**Governance rules**

- **Never call this without explicit approval.** AI-reviewed or modified tests must be re-presented to the user before this call is made.
- Rejected tests must be EXCLUDED from the payload — do not include them even if they were previously in the suite.
- If tests were modified during review, re-present the final list of tests before requesting confirmation.

**Confirmation gate**

**REQUIRED — do not skip.** Show the user the full list of changes before calling:

> "I'm about to sync the following changes to the test suite:
> - **Add:** `<testSuiteName1>`, `<testSuiteName2>`
> - **Remove:** `<testSuiteName3>`
> - Stage: `<stageName>` | Event: `<event>`
>
> Confirm?"

Only proceed after receiving explicit confirmation.

**On success**

Confirm to the user:
> "Test suite updated successfully for the `<stageName>` stage."

---

## The system call

All three modes use the same endpoint. Substitute all `<placeholder>` values before executing.

```bash
sf api request rest "/services/data/v67.0/connect/devopstesting/pipeline/<pipelineId>/testSuiteStages" --method POST --body '{"pipelineStageId":"<stageId>","event":"<event>","assignments":[{"testSuiteId":"<id>","action":"add|remove"}]}' --target-org <doce-org-alias>
```

Full payload schema:

```json
{
  "pipelineStageId": "<stageId>",
  "event": "<event>",
  "assignments": [
    {"testSuiteId": "<suiteId1>", "action": "add"},
    {"testSuiteId": "<suiteId2>", "action": "remove"}
  ]
}
```

**Error handling**

Never expose raw API error messages to the user. Map response status codes to the following user-facing messages:

| Status | User-facing message |
|---|---|
| 400 | "The request was invalid. Check that all suite and stage IDs are correct and the event type is valid." |
| 403 | "You don't have permission to modify suite assignments on this pipeline." |
| 404 | "The pipeline or stage was not found." |
| 500 | "A server error occurred. Try again in a few minutes." |

---

## Related skills

- **`syncing-test-providers`** — use when the suite you want to assign doesn't appear yet; re-syncing the provider pulls in newly added suites.
- **`recommending-devops-tests`** — use when a suite has not yet been identified and you need a recommendation for which suite to assign.
- **`configuring-quality-gate`** — use to configure a quality gate on the stage after mapping suites.
- **`analyzing-test-failures`** — use for failure analysis and suggested improvements to the tests within a suite.
