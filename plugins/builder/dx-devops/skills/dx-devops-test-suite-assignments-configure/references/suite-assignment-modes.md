# Modes B–D — Assign / Map / Manage Suite Classes

All three modes use the same `testSuiteStages` endpoint (`references/api-endpoint.md`). They differ in scope and the confirmation pattern required.

## Prerequisites & shared inputs

Run Prerequisites 1–4 **and** Prerequisite 5 (stage). You need:

| Variable | Description |
|---|---|
| `doce-org-alias` | Prerequisite 1 |
| `pipelineId` | Prerequisite 4 (pipeline selection) |
| `stageId` | Prerequisite 5 (stage selection) |
| `event` | `Pre-Promote`, `Post-Promote`, or `Review` |

---

## Mode B — Assign a single suite to a stage

Use when a relevant test suite already exists but is not yet linked to a stage and the user wants to add it as a single one-off assignment.

**Additional inputs:**

| Variable | Description |
|---|---|
| `testSuiteId` | ID of the suite to assign |
| `testSuiteName` | Name of the suite (for display in confirmation) |

**Confirmation gate (required before any API call):**

> "The suite `<testSuiteName>` is not currently assigned to the `<stageName>` stage (`<event>`). Would you like me to assign it now?"

Do not proceed until the user confirms.

**On success:**

> "Suite `<testSuiteName>` has been assigned to the `<stageName>` stage (`<event>`)."

---

## Mode C — Map multiple suites to a stage

Use when configuring suite-to-stage mappings across a pipeline or assigning multiple suites as part of a testing strategy.

**Additional inputs:**

| Input | Description |
|---|---|
| `testSuiteOperations` | List of `{testSuiteId, action: "add"\|"remove"}` |

**MANDATORY IMPACT PREVIEW — required before any changes.** Do not call the API until the user has confirmed the preview:

> "Here's the suite mapping I'll apply:
>
> | Suite | Stage | Event | Action |
> |---|---|---|---|
> | `<suiteName>` | `<stageName>` | `<event>` | Add |
> | `<suiteName2>` | `<stageName>` | `<event>` | Remove |
>
> Confirm to apply all changes?"

Only proceed after the user explicitly confirms.

**On success:**

> "Suite mapping applied. `<N>` suite(s) updated for the `<stageName>` stage."

---

## Mode D — Add/remove test classes in a suite

Use when the user wants to add or remove individual test classes within an existing suite assignment, sync reviewed tests into a suite, or promote tests to a suite.

**Additional inputs:**

| Input | Source |
|---|---|
| `testSuiteOperations` | List of `{testSuiteId, action: "add"\|"remove"}` |

**Governance rules:**

- **Never call this without explicit approval.** AI-reviewed or modified tests must be re-presented to the user before this call is made.
- Rejected tests must be EXCLUDED from the payload — do not include them even if they were previously in the suite.
- If tests were modified during review, re-present the final list before requesting confirmation.

**Confirmation gate (required — do not skip):**

> "I'm about to sync the following changes to the test suite:
> - **Add:** `<testSuiteName1>`, `<testSuiteName2>`
> - **Remove:** `<testSuiteName3>`
> - Stage: `<stageName>` | Event: `<event>`
>
> Confirm?"

Only proceed after explicit confirmation.

**On success:**

> "Test suite updated successfully for the `<stageName>` stage."
