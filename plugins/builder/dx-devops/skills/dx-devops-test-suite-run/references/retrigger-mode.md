# Retrigger Mode — Re-running a Quality Gate

Use this mode when a promotion was blocked by a quality gate failure and the coverage gap has since been addressed.

## Extra preconditions — all must be true before proceeding

1. The `Coverage` field on the latest `DevopsTestSuiteExecution` meets or exceeds the threshold defined in the `DevopsQualityGateRule`.
2. The user has explicitly asked to retrigger the gate.
3. The same `pipelineId`, `stageId`, and `event` from the blocked promotion are known.

If coverage is still below threshold, do **not** retrigger. Instead respond:

> "Coverage is still at `<X>%`, below the `<threshold>%` gate. The gate cannot be retriggered until the threshold is met. Here are the remaining uncovered methods: `<list>`."

Do not retry. Explain what must be resolved first and stop.

## Inputs required for retrigger

| Input | Source |
|---|---|
| `pipelineId` | From the blocked promotion context |
| `stageId` | From the blocked promotion context |
| `event` | Same event type that originally blocked (`Pre-Promote` or `Post-Promote`) |
| `suiteIds` | Same suites that were originally run |
| `doce-org-alias` | Prerequisite 1 |

## Confirmation gate (retrigger)

Before executing the API call, present this confirmation prompt and wait for explicit user approval:

> "Coverage is confirmed at `<X>%`, which meets the `<threshold>%` gate. I'll retrigger the quality gate check for the `<stageName>` stage (`<event>`). Confirm?"

Only proceed after the user confirms. If the user declines, stop without making any API call.

## API call (retrigger)

Uses the same Connect API stage/execute endpoint:

```bash
sf api request rest "/services/data/v67.0/connect/devopstesting/pipeline/<pipelineId>/stage/execute" --method POST --body '{"stageId":"<stageId>","event":"<event>","testSuiteIds":["<suiteId1>"]}' --target-org <doce-org-alias>
```

After the call returns a `runId`, hand off to Step 2 (polling) with the new `runId` to monitor the execution result.

## Error handling (retrigger)

If the API returns an error indicating the gate cannot be retriggered, respond with:

> "The quality gate cannot be retriggered right now. Reason: `<plain-language summary>`. Here's what needs to be resolved first: `<list>`."

Never expose raw API error details to the user.
