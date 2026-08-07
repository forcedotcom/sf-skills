---
name: dx-devops-test-suite-assignments-configure
description: "Recommends and manages DevOps Center test suite assignments for pipeline stages. Mode A analyzes a commit diff against assigned suite metadata to recommend relevant existing suites and flag coverage gaps (pure reasoning). Modes B-D assign a single suite, bulk-map multiple suites with a mandatory impact preview, or add/remove test classes with governance rules, via the testSuiteStages Connect API. Use this skill to recommend suites for a commit, assign or map suites to stages, or add/remove tests in a suite. TRIGGER when: the user asks which suites to run for a commit/diff or what covers their changes; a suite is unlinked and the user wants it assigned; the user wants to configure suite-to-stage mappings, assign multiple suites, or add/remove/sync tests in a suite. DO NOT TRIGGER when: configuring or syncing a test provider (use dx-devops-test-pipeline-configure), running suites (use dx-devops-test-suite-run), or authoring/running tests directly (use platform-apex-test-generate or platform-apex-test-run)."
metadata:
  cliTools:
    - tool: ["sf"]
      semver: ">=2.67.0"
  relatedSkills:
    - "dx-devops-test-failures-analyze"
    - "dx-devops-test-pipeline-configure"
    - "dx-devops-test-suite-run"
    - "platform-apex-test-generate"
    - "platform-apex-test-run"
  version: "1.0"
  minApiVersion: "67.0"
---

# Configure DevOps Center Suite Assignments

Recommends which existing test suites to run for a change, and manages how suites are assigned and mapped to pipeline stages. These operations share the same suite-stage metadata: a recommendation surfaces relevant suites and flags gaps, and those gaps lead directly into assignment.

> **API version:** All DevOps testing system calls target Salesforce API **v67.0** (minimum required).

**Important:** All DevOps Center data lives in the Salesforce org — NOT the local repo. Never search the filesystem for suite configuration. Always query the org with `sf data query` or `sf api request rest`.

---

## Step 1 — Run prerequisites first (always)

Run the prerequisite checks in `references/prerequisite-checks.md` before any query or system call. On any failure, surface the plain-language message and stop.

- **Mode A (recommend):** Prerequisites 1–4 (org login, plugin, DevOps Center org auth, pipeline identified). No stage required — recommendation reads the pipeline-level Review trigger.
- **Modes B–D (assign/map/classes):** Prerequisites 1–4 **and** Prerequisite 5 (stage). You need `doce-org-alias`, `pipelineId`, and `stageId`.

---

## Step 2 — Select the mode

| If the user wants to… | Mode | Follow |
|---|---|---|
| Know **which suites to run** for a commit/diff, or what covers their changes | **A — Recommend suites** | `references/recommendation-logic.md` |
| Assign **one** suite to a stage as a one-off | **B — Assign a single suite** | `references/suite-assignment-modes.md` |
| **Bulk-map** multiple suites to a stage as a testing strategy | **C — Map multiple suites** | `references/suite-assignment-modes.md` |
| **Add/remove** individual test classes within a suite assignment | **D — Add/remove classes** | `references/suite-assignment-modes.md` |

Mode A is pure reasoning (no writes). Modes B–D mutate org state via the same `testSuiteStages` endpoint (`references/api-endpoint.md`).

**How A feeds B–D:** When recommendation flags a relevant suite that is *not assigned* to the stage, that gap is the input to Mode B/C. When it flags a *new method with no suite coverage*, direct the developer to author tests manually (v1 constraint — never suggest generating tests here).

---

## Step 3 — Governance & confirmation (Modes B–D)

Modes B–D **must** confirm before any write:

- **Mode B** — single confirmation prompt naming the suite, stage, and event.
- **Mode C** — a **mandatory impact-preview table** (Suite / Stage / Event / Action) before the confirmation gate.
- **Mode D** — re-present the final test list before confirming. **Rejected tests must be EXCLUDED from the payload.** If tests were modified during review, re-present the final list before requesting confirmation. Never call without explicit approval.

Do not call the API until the user gives an affirmative response. If the user declines, stop without writing. Full wording for each gate is in `references/suite-assignment-modes.md`.

Mode A (recommendation) makes no writes and needs no confirmation gate.

---

## Step 4 — Execute and report

Follow the chosen reference file:

- `references/recommendation-logic.md` — Mode A: diff classification, provider matching, ranking, gap flagging, output format.
- `references/suite-assignment-modes.md` — Modes B–D: inputs, confirmation wording, success messages.
- `references/api-endpoint.md` — the shared `testSuiteStages` POST payload schema (Modes B–D).
- `references/error-handling.md` — status-code → plain-language tables.

Never expose raw API errors, stack traces, or JSON to the user.

---

## Related skills

- **`dx-devops-test-pipeline-configure`** — if the suite you want to assign doesn't appear yet, configure or re-sync the provider; also configures quality gates on a stage after mapping.
- **`dx-devops-test-suite-run`** — execute a recommended/assigned suite on a stage.
- **`dx-devops-test-failures-analyze`** — analyze failures and improvement suggestions for the tests within a suite.
