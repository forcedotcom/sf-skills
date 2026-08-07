# Common Pipeline Management Workflows

Real-world examples of typical pipeline operations in DevOps Center autonomous release scenarios. All commands use `--json`; add `--target-org <alias>` when not relying on the default org.

---

## Workflow 1: End-to-End Pipeline Setup — Create, Stage, Bind Environments, Activate

**User request:** "Set up a release pipeline on repo myorg/myrepo with Integration → UAT → Production and activate it"

**Steps:**

1. **Create the pipeline** against the existing repo, then resolve its ID from the list:
   ```bash
   sf devops pipeline create \
     --name "Release Pipeline" \
     --repo https://github.com/myorg/myrepo \
     --json
   PIPELINE_ID=$(sf devops pipeline list --json | \
     jq -r '.result.pipelines[] | select(.Name == "Release Pipeline") | .Id' | head -n1)
   ```

2. **Inspect the initial stages** (a new pipeline always starts with at least one seeded stage):
   ```bash
   sf devops pipeline get --pipeline-id "$PIPELINE_ID" --json | \
     jq -r '.result.stages[] | "\(.name) (\(.id)) -> next: \(.nextStageId)"'
   ```

3. **Add stages in promotion order.** `stage add` inserts a stage *before* `--next-stage-id`, so anchor each new stage to the one that should follow it. To build Integration → UAT → Production, add Production first (or anchor to the terminal stage), then insert UAT before Production, then Integration before UAT:
   ```bash
   # Assume Production stage id is 0Xc...PROD (from step 2 or a prior add)
   sf devops pipeline stage add --pipeline-id "$PIPELINE_ID" \
     --name "UAT" --next-stage-id 0XcPROD --json
   sf devops pipeline stage add --pipeline-id "$PIPELINE_ID" \
     --name "Integration" --next-stage-id 0XcUAT --json
   ```

4. **Bind an environment to each stage** (re-fetch stage IDs with `pipeline get`). In CI, add `--no-browser`:
   ```bash
   sf devops stage environment add --pipeline-id "$PIPELINE_ID" \
     --stage-id 0XcINT --environment-name integration-org --org-type Sandbox --no-browser --json
   sf devops stage environment add --pipeline-id "$PIPELINE_ID" \
     --stage-id 0XcUAT --environment-name uat-org --org-type Sandbox --no-browser --json
   sf devops stage environment add --pipeline-id "$PIPELINE_ID" \
     --stage-id 0XcPROD --environment-name prod-org --org-type Production --no-browser --json
   ```

5. **Activate** once every stage has an environment:
   ```bash
   sf devops pipeline update --pipeline-id "$PIPELINE_ID" --activate --json
   ```

6. **Verify** the final shape:
   ```bash
   sf devops pipeline get --pipeline-id "$PIPELINE_ID" --json | \
     jq -r '.result | "\(.name) [\(.isActive)]: \([.stages[].name] | join(", "))"'
   ```

**Report:** "Release Pipeline created and activated: Integration → UAT → Production, environments bound."

---

## Workflow 2: Insert a Staging Stage Before Production

**User request:** "Add a Staging stage between UAT and Production on the Release Pipeline"

**Steps:**

1. **Find the pipeline and stage IDs**:
   ```bash
   PIPELINE_ID=$(sf devops pipeline list --json | \
     jq -r '.result.pipelines[] | select(.Name == "Release Pipeline") | .Id' | head -n1)
   sf devops pipeline get --pipeline-id "$PIPELINE_ID" --json | \
     jq -r '.result.stages[] | "\(.name) (\(.id)) -> next: \(.nextStageId)"'
   # Integration (0XcINT) -> next: 0XcUAT
   # UAT (0XcUAT) -> next: 0XcPROD
   # Production (0XcPROD) -> next: null
   ```

2. **Insert Staging before Production**:
   ```bash
   sf devops pipeline stage add --pipeline-id "$PIPELINE_ID" \
     --name "Staging" --next-stage-id 0XcPROD --json
   ```

3. **Bind the staging environment** (get the new stage ID from `pipeline get`):
   ```bash
   sf devops stage environment add --pipeline-id "$PIPELINE_ID" \
     --stage-id 0XcSTG --environment-name staging-org --org-type Sandbox --no-browser --json
   ```

4. **Verify** Staging now sits between UAT and Production.

> **Constraint:** This works only if the pipeline is not yet locked. Stages can't be modified after the pipeline is activated and changes have been promoted through it.

**Report:** "Staging stage inserted before Production, bound to staging-org."

---

## Workflow 3: Attach a Project to a Pipeline

**User request:** "Connect Project Alpha to the Release Pipeline"

**Steps:**

1. **Resolve IDs**:
   ```bash
   PIPELINE_ID=$(sf devops pipeline list --json | \
     jq -r '.result.pipelines[] | select(.Name == "Release Pipeline") | .Id' | head -n1)
   PROJECT_ID=$(sf devops project list --json | \
     jq -r '.result.projects[] | select(.Name == "Project Alpha") | .Id' | head -n1)
   ```

2. **Attach**:
   ```bash
   sf devops pipeline project add --pipeline-id "$PIPELINE_ID" --project-id "$PROJECT_ID" --json
   ```

3. **Verify** via `pipeline get` that Project Alpha appears in `.result.connectedProjects[]`.

> **Constraint:** A project attaches to only one pipeline. If attach fails with "already attached," detach it from the other pipeline first: `sf devops pipeline project delete --pipeline-id <other> --project-id "$PROJECT_ID" --json`.

**Report:** "Project Alpha attached to Release Pipeline."

---

## Workflow 4: Rename and Deactivate a Pipeline

**User request:** "Deactivate the Release Pipeline and rename it to Legacy Pipeline"

**Steps:**

1. **Combine deactivate + rename** in one command:
   ```bash
   sf devops pipeline update --pipeline-id 0XB000000000001 \
     --deactivate --name "Legacy Pipeline" --json
   ```

2. **Verify** via `pipeline get` that `.result.isActive` is false and the name updated.

**Report:** "Pipeline deactivated and renamed to 'Legacy Pipeline'."

---

## Workflow 5: Idempotent Pipeline Setup (Safe Re-Run in CI)

**User request:** "Ensure the Release Pipeline exists — runs on every CI job"

**Steps:**

```bash
PIPELINE_NAME="Release Pipeline"

EXISTING_ID=$(sf devops pipeline list --json | \
  jq -r ".result.pipelines[] | select(.Name == \"$PIPELINE_NAME\") | .Id" | head -n1)

if [ -n "$EXISTING_ID" ]; then
  echo "Pipeline already exists: $EXISTING_ID"
else
  sf devops pipeline create --name "$PIPELINE_NAME" \
    --repo https://github.com/myorg/myrepo --json
fi
```

**Report:** either the existing pipeline ID or the newly created one — no duplicate created.

---

## Notes for Autonomous Runs

- Confirm org auth with `sf org display --json` before the first command.
- **Stage IDs come from `sf devops pipeline get`** — always fetch them before `stage add` / `stage update` / `stage delete` / `stage environment add`.
- `stage add` inserts *before* `--next-stage-id`; plan the anchor stage to get the order you want.
- `stage environment add` opens a browser OAuth flow — always pass `--no-browser` in CI and complete auth via the printed redirect URL.
- Finish all stage/environment configuration **before** activating; an active, promoted pipeline locks its stage structure.
- Deactivate before deleting an environment; the pipeline must be inactive.
- Treat a same-name create as idempotent — check-before-create and report the existing pipeline.
