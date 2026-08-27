# Polling Configuration (Step 2)

**Confirmation required:** No — polling is automatic and read-only. No user confirmation gate is needed.

**What it does:** Polls the DevOps Center org for the status of an async test execution until it completes, times out, or fails.

## Prerequisites

You need an active `runId` (from Step 1, the execute call) and the confirmed `doce-org-alias`. If org context is not yet established, run Prerequisites 1–3 (`references/prerequisite-checks.md`).

## Inputs

| Input | Source |
|---|---|
| `runId` | Returned by the Step 1 execute call (or supplied by the user for an in-progress run) |
| `testType` | Derived from the suite's test provider (Apex, Code Analyzer, UI/Provar, Flow) |
| `doce-org-alias` | Established via prerequisites |

If the user is watching an already-running execution, resolve the `runId` by querying the most recent `DevopsTestExecution` for the relevant trigger, or use the runId the user provides.

## Polling intervals

| Test type | Poll interval | Max wait | Timeout action |
|---|---|---|---|
| Apex unit tests | 15 seconds | 5 minutes | Surface runId, offer retry |
| Code Analyzer | 10 seconds | 3 minutes | Surface runId, offer retry |
| UI tests (Provar) | 60 seconds | 20 minutes | Surface runId, mark as pending |
| Flow tests | 20 seconds | 8 minutes | Surface runId, offer retry |

## Object model — read the right object

The `runId` returned by the execute call is a **`DevopsTestSuiteExecution`** record Id (the suite-level run). Poll *that* object — it holds the status and the aggregate results. Per-test detail lives on child `DevopsTestExecution` records linked by `DevopsTestSuiteExecutionId`.

| Object | Role | Key fields |
|---|---|---|
| `DevopsTestSuiteExecution` (poll this) | Suite-level run = the `runId` | `Status`, `Coverage`, `SuccessCount`, `FailureCount`, `SuccessRate`, `FailureRate`, `QualityGateStatus`, `ExecutionEndTime`, `ResultDetails`, `ReportUrl` |
| `DevopsTestExecution` (per-test detail) | One row per test, linked via `DevopsTestSuiteExecutionId` | `Status`, `Message`, `Severity`, `ResultDetails`, `DevopsTestId` |

> Do NOT query `TestsRan`, `TestsPassed`, `TestsFailed`, or `CoveragePercentage` — those fields do not exist on either object and the query will fail with `INVALID_FIELD`. Use the field names in the table above.

## Poll query

Query the suite execution record by `runId` on each interval:

```bash
sf data query \
  --query "SELECT Id, Status, Coverage, SuccessCount, FailureCount, QualityGateStatus FROM DevopsTestSuiteExecution WHERE Id = '<runId>' LIMIT 1" \
  --target-org <doce-org-alias> \
  --json
```

Check the `Status` picklist on each poll (valid values: `Passed`, `Failed`, `InProgress`, `Error`):
- `InProgress` → wait and poll again
- `Passed` → run completed successfully; surface results
- `Failed` → run completed with test failures; surface results, then fetch per-test detail (below) and hand off to analysis
- `Error` → the run itself errored (not a test failure); surface the `ResultDetails`/`Message` in plain language and offer retry or skip

## On timeout

Surface the `runId` to the user:
> "The test run is taking longer than expected. Your run ID is `<runId>`. You can check the status manually in DevOps Center, or I can keep waiting — what would you prefer?"

Do not automatically retry after timeout. Wait for user instruction.

## On completion

When `Status` is `Passed` or `Failed`, surface `Coverage`, `SuccessCount`, `FailureCount`, and `QualityGateStatus` from the `DevopsTestSuiteExecution` record inline (no raw JSON).

If `FailureCount > 0` (or `Status = Failed`), fetch the per-test failure detail from the child `DevopsTestExecution` records, then pass that payload to the **`dx-devops-test-failures-analyze`** skill:

```bash
sf data query \
  --query "SELECT Id, Status, Message, Severity, ResultDetails, DevopsTestId FROM DevopsTestExecution WHERE DevopsTestSuiteExecutionId = '<runId>' AND Status = 'Failed'" \
  --target-org <doce-org-alias> \
  --json
```

**Empty / no-data case:** If no `DevopsTestSuiteExecution` record matches the runId, report that clearly and do NOT fabricate a runId, status, or result values.
