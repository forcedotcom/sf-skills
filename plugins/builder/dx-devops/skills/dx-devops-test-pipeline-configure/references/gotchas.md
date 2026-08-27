# Critical Gotchas

## Duplicate provider configuration (the big one)

`POST /connect/devops/pipeline/<pipelineId>/testProvider` **creates a new provider configuration record** (`DevopsPipelineTestProvider`). Use it ONLY to configure a provider for the **first time** (Mode A).

To re-sync an already-configured provider for new suites, use `POST /connect/devops/sync` (Mode B). Calling the configure endpoint on an already-configured provider produces **duplicate** `DevopsPipelineTestProvider` records.

**Decision tree:**

- Provider is **Available** → configure via `POST .../pipeline/<id>/testProvider` (Mode A).
- Provider is **Configured**, new suites missing → sync via `POST /connect/devops/sync` (Mode B).
- Provider is **Configured**, suites missing only when assigning to a stage → stage-assignment gap; redirect to `dx-devops-test-suite-assignments-configure`.

## API name differences

| Issue | Resolution |
|---|---|
| `DevopsPipeline` query returns empty | DevOps Center not installed on the target org, or wrong org alias — ask the user to verify |
| `DevopsWorkItem` sObject not supported | Use `WorkItem` (no namespace) — the correct API name for this org version |
| `sf plugins` doesn't match `agentforce` | The installed plugin is `@salesforce/plugin-agent` — match on `plugin-agent` too |

## Trigger-type rules

| Issue | Resolution |
|---|---|
| Review trigger is pipeline-level, not stage-level | Query `DevopsPipelineStageTrigger` where `TriggerType = 'Review'` and `RelatedRecordId = <pipelineId>` |
| Connect API `testSuites` returns empty with `?stageId=` | Use `?triggerId=<reviewTriggerId>` — `stageId` only works for stage-level triggers |

## Endpoint families

- **Configure provider:** `POST /connect/devops/pipeline/<pipelineId>/testProvider`
- **Sync provider:** `POST /connect/devops/sync`
- **List providers:** `GET /connect/devopstesting/pipeline/<pipelineId>/testProviders?status=all`
- **Quality gate:** `POST /connect/devopstesting/qualityGate`

Note the `devops` vs `devopstesting` path segment differs between sync/configure and the listing/quality-gate endpoints — copy them exactly.
