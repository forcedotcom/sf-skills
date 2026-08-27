# Mode A — Configure a Test Provider

Configures an *Available* (not-yet-configured) test provider on a DevOps Center pipeline, making its test suites available for assignment to pipeline stages.

**Confirmation required:** Yes — explicit confirmation before the provider is configured.

## Inputs

| Variable | Source |
|---|---|
| `doce-org-alias` | Prerequisite 1 |
| `pipelineId` | Prerequisite 4 (pipeline selection) |
| `testProviderId` | Resolved by fetching the pipeline's test providers (Step 1 below) |

Prerequisite 5 (stage) is **not** required — providers are configured at the pipeline level.

---

## Step 1 — Fetch test providers to resolve the provider ID

```bash
sf api request rest \
  "/services/data/v67.0/connect/devopstesting/pipeline/<pipelineId>/testProviders?status=all" \
  --target-org <doce-org-alias>
```

Each provider entry includes `testProviderId`, `testProviderName`, and a status (Configured vs. Available). Present a short summary grouped by status:

```text
Test providers for <pipelineName>:

✓ Configured:
- Code Analyzer (63 suites)
- Apex Unit Tests (5 suites)

Available (not yet configured):
- Flow Tests
```

- **Only an Available provider can be configured.** If the pipeline has no available providers, report that and stop — do NOT fabricate a provider or ID.

### If the named provider is already Configured

Do **not** present the confirmation gate and do **not** POST to the configure endpoint (Steps 2–3) — that would create a duplicate `DevopsPipelineTestProvider`. Instead:

1. State plainly that the provider is already configured, including its synced suite count and last-sync time if returned (e.g. *"Flow Tests is already configured on `<pipelineName>` with 3 suites synced (last sync 2026-06-23)."*).
2. Diagnose the user's actual goal and redirect **by name**:
   - If the user says the provider's **suites don't appear when assigning tests to a stage**, this is a **stage-assignment gap, not a provider-configuration gap** — the suites already exist at the pipeline level; they just need to be linked to the stage. Redirect to **`dx-devops-test-suite-assignments-configure`**.
   - If the user expects **newly created suites** that aren't yet synced, use **Mode B — Sync a configured provider** (`references/syncing-test-providers.md`) to pull them in.
3. Do not loop back to configuring — finish cleanly after the explanation and redirect.

## Step 2 — Confirmation gate

**Required — do not call the API before the user confirms.**

> "I'll configure `<testProviderName>` on the `<pipelineName>` pipeline. This will make its suites available for assignment to stages. Confirm?"

Do not proceed until the user gives an affirmative response.

## Step 3 — Configure the provider

On confirmation, call the configure endpoint with the provider ID:

```bash
sf api request rest \
  "/services/data/v67.0/connect/devops/pipeline/<pipelineId>/testProvider" \
  --method POST \
  --body '{"testProviderId": "<testProviderId>"}' \
  --target-org <doce-org-alias>
```

## On success

> "Provider `<testProviderName>` is now configured on the `<pipelineName>` pipeline. Its suites are available for assignment to stages."

Newly configured suites can then be assigned to stages with `dx-devops-test-suite-assignments-configure`.

---

See `references/gotchas.md` for the duplicate-provider trap and `references/error-handling.md` for status-code responses.
