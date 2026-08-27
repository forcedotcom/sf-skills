# API Endpoint — testSuiteStages (Modes B–D)

All three assignment modes (B, C, D) use the same Connect API endpoint. Substitute all `<placeholder>` values before executing.

```bash
sf api request rest "/services/data/v67.0/connect/devopstesting/pipeline/<pipelineId>/testSuiteStages" --method POST --body '{"pipelineStageId":"<stageId>","event":"<event>","assignments":[{"testSuiteId":"<id>","action":"add|remove"}]}' --target-org <doce-org-alias>
```

## Full payload schema

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

| Field | Type | Description |
|---|---|---|
| `pipelineStageId` | string | The pipeline stage ID (from Prerequisite 5) |
| `event` | string | `Pre-Promote`, `Post-Promote`, or `Review` |
| `assignments` | array | One or more `{testSuiteId, action}` entries — `action` is `add` or `remove` |

- **Mode B** sends a single `add` assignment.
- **Mode C** sends multiple `add`/`remove` entries in one call (bulk mapping).
- **Mode D** sends `add`/`remove` entries for the classes/suites being synced — rejected tests excluded.
