# Mode A — Recommend Suites for a Commit/Diff

**Type:** Pure reasoning — no system calls beyond the prerequisite data-fetch queries documented below. No writes.

**What it does:** Analyzes the commit diff and available suite metadata to recommend the most relevant existing test suites assigned to the Review pipeline stage. Flags coverage gaps where no suite covers a new method.

## Prerequisites

Run Prerequisites 1–4 (`references/prerequisite-checks.md`). A confirmed DevOps Center org alias and `pipelineId` are required before proceeding. No stage prompt — recommendation reads the pipeline-level Review trigger.

---

## Step 1 — Fetch suite metadata

Two queries are required before reasoning.

**1a — Find the Review pipeline stage trigger:**

```bash
sf data query \
  --query "SELECT Id FROM DevopsPipelineStageTrigger WHERE TriggerType = 'Review' AND RelatedRecordId = '<pipelineId>'" \
  --target-org <doce-org-alias> \
  --json
```

Record the `Id` returned as `<reviewTriggerId>`.

**1b — Fetch suites assigned to that trigger:**

```bash
sf data query \
  --query "SELECT Id, TestSuiteId, TestSuite.Name, IsQualityGateEnabled, DevopsQualityGateId FROM DevopsTestSuiteStage WHERE DevopsPipelineStageTriggerId = '<reviewTriggerId>'" \
  --target-org <doce-org-alias> \
  --json
```

Each row provides: `TestSuiteId`, `TestSuite.Name`, `IsQualityGateEnabled`, and `DevopsQualityGateId` (when a gate is configured).

> Note: Do NOT use the beta `/connect/devops/.../testSuites` endpoint — it returns empty results. Query `DevopsTestSuiteStage` directly as shown above.

Never expose raw API errors or raw JSON to the user. If a query fails, report the problem in plain language and stop. The commit diff comes from the user or surrounding context.

---

## Reasoning steps

### 1 — Classify the diff by change type

| File pattern | Change type |
|---|---|
| `*.cls`, `*.trigger` | Apex |
| `*.flow-meta.xml`, `*.flow` | Flow |
| `*.java` | Java |
| `*.js`, `*.html` (LWC paths) | LWC / JavaScript |

A single commit may contain multiple change types. Identify all of them.

### 2 — Map change types to test providers

For each change type, match against the `testProviderName` of the fetched suites:

| Change type | Match suites whose `testProviderName` contains |
|---|---|
| Apex | `Apex` |
| Flow | `Flow` |
| Java | `Java` |
| LWC / JavaScript | `LWC` or `JavaScript` |
| Code Analyzer (any) | `Code Analyzer` — then sub-filter by suite name convention: `recommended` → Apex/general rules (suggest for Apex and Java changes), `html` → suggest for HTML/LWC template changes, `css` → suggest for CSS changes. If no suite name matches the convention, suggest all Code Analyzer suites and note the ambiguity. |

Only recommend suites whose provider matches at least one change type in the diff. Suites from non-matching providers are excluded.

### 3 — Rank matched suites

Within each matched provider group, rank suites by:
1. `triggerType` alignment — `Pre-Promote` suites first for commit-time checks
2. Quality gate presence — suites with a `qualityGateRuleName` are higher priority (they gate promotion)
3. Suite name relevance — if the suite name contains a term from the modified file names, boost it

### 4 — Flag new methods with no suite coverage

For any new method added in the diff, flag it as a gap regardless of provider matching:
> "⚠ `processRefund()` in `OrderService.cls` is a new method. No existing suite can confirm it's covered until tests are authored and linked."

### 5 — Return the recommendation list

Group recommendations by change type so it's clear why each suite was suggested.

---

## Output format

```text
Recommended suite(s) for this commit:

Apex changes detected (OrderService.cls, InvoiceService.cls):
1. <SuiteName> — Apex Test Provider | Trigger: Pre-Promote | Gate: <gateName or none>
2. <SuiteName2> — Apex Test Provider | Trigger: Post-Promote | Gate: <gateName or none>

Flow changes detected (OrderApproval.flow):
1. <SuiteName3> — Flow Test Provider | Trigger: Pre-Promote | Gate: <gateName or none>

Code Analyzer — Apex rules:
1. <SuiteName4> — Code Analyzer | Trigger: Pre-Promote | Gate: <gateName or none>

No matching suite found for:
- LWC changes — no LWC test suite is assigned to this stage

Coverage gaps (new methods — manual authoring required):
- `processRefund()` in `OrderService.cls` — new method, not yet covered by any suite
```

---

## v1 constraint

Only recommend existing suites. Never suggest generating new tests. If gaps exist, direct the developer to author tests manually and explain exactly which methods need coverage.

## How recommendations feed assignment

- A relevant suite that exists but is **not assigned** to the stage → use **Mode B/C** (`references/suite-assignment-modes.md`) to assign it.
- To actually execute a recommended suite, use **`dx-devops-test-suite-run`**.
