# Error Handling — Execution & Polling

Never expose raw API errors, stack traces, or JSON payloads to the user.

## Step 1 — Execute call

| Status | Message to user |
|---|---|
| 400 | "The test execution request was invalid. Check that the stage and suite IDs are correct." |
| 403 | "You don't have permission to run tests on this pipeline. Check your DevOps Testing API access." |
| 404 | "The pipeline or stage was not found. It may have been deleted." |
| 500 | "The DevOps Center org returned a server error. Try again in a few minutes." |

## Org-side execution rejections (read the real error, explain, finish — do NOT loop)

| Org error | Explanation to user |
|---|---|
| `environmentId: null` | "The environment connection isn't resolving for this stage. Re-authenticate or reconnect the stage's environment in DevOps Center, then try again." |
| `classIdList is null or empty — no tests to execute` | "The assigned suite(s) contain no test classes, so there's nothing to run. Add test classes to the suite (via dx-devops-test-suite-assignments-configure) and try again." |

In both cases: attempt the call once, explain the root cause and required fix, finish cleanly. Do NOT retry in a loop and do NOT fabricate a `runId` or results.

**Empty-org / no-data case:** If the stage has no assigned suites, report that clearly and do NOT call the execute endpoint or fabricate a suite/run.

## Step 2 — Polling

If no `DevopsTestExecution` record matches the runId, report it gracefully and do not fabricate result data. On timeout, surface the runId and wait for user instruction — never auto-retry.

## Do NOT use `sf apex run test`

That command is for the `platform-apex-test-run` skill, not DevOps Center test suites.
