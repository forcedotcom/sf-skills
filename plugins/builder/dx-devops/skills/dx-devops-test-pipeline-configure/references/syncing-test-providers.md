# Mode B — Sync a Configured Provider

Re-syncs an already-*Configured* test provider on a DevOps Center pipeline so that suites added to the provider since it was last configured become available for assignment to stages.

**Confirmation required:** Yes — explicit confirmation before the sync is triggered.

## Inputs

| Variable | Source |
|---|---|
| `doce-org-alias` | Prerequisite 1 |
| `pipelineId` | Prerequisite 4 (pipeline selection) |
| `testProviderId` | Resolved by fetching the pipeline's test providers (Step 1 below) |

Prerequisite 5 (stage) is **not** required — providers are synced at the pipeline level.

---

## Step 1 — Fetch test providers to resolve the provider ID

```bash
sf api request rest \
  "/services/data/v67.0/connect/devopstesting/pipeline/<pipelineId>/testProviders?status=all" \
  --target-org <doce-org-alias>
```

Each provider entry includes `testProviderId`, `testProviderName`, and a status (Configured vs. Available). Present a short summary grouped by status (same format as Mode A).

- **Only a Configured provider can be synced.** If the user names an *Available* (not-yet-configured) provider, explain it must be configured first — use **Mode A** (`references/configuring-test-provider.md`).
- If the pipeline has no configured providers, report that and stop — do NOT fabricate a provider or ID.

## Step 2 — Confirmation gate

**Required — do not call the API before the user confirms.**

> "I'll re-sync `<testProviderName>` on the `<pipelineName>` pipeline to pick up any new suites. Confirm?"

Do not proceed until the user gives an affirmative response.

## Step 3 — Trigger the sync

On confirmation, call the sync endpoint with the provider ID(s) and pipeline ID:

```bash
sf api request rest \
  "/services/data/v67.0/connect/devops/sync" \
  --method POST \
  --body '{
    "testProviderIds": ["<testProviderId>"],
    "pipelineId": "<pipelineId>"
  }' \
  --target-org <doce-org-alias>
```

`testProviderIds` is a list — multiple configured providers can be synced in one call.

## On success

> "Provider `<testProviderName>` sync started. The operation is running asynchronously — new suites will be available shortly."

The sync runs asynchronously; newly synced suites can then be assigned to stages with `dx-devops-test-suite-assignments-configure`.

---

## Critical gotcha

**Do NOT use** `POST /connect/devops/pipeline/<pipelineId>/testProvider` to sync — that endpoint **creates a new provider configuration** and will result in duplicate `DevopsPipelineTestProvider` records. Sync only via `POST /connect/devops/sync`. See `references/gotchas.md`.

See `references/error-handling.md` for status-code responses.
