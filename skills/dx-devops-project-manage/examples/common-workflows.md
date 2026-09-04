# Common Project Management Workflows

Real-world examples of typical project operations in DevOps Center autonomous release scenarios.

---

## Workflow 1: List All Projects

**User request:** "Show me all DevOps Center projects in this org"

**Steps:**

1. **Verify authentication**:
   ```bash
   sf org display --json
   ```

2. **List projects**:
   ```bash
   sf devops project list --target-org my-devops-org --json
   ```

3. **Present in a readable format**:
   ```bash
   sf devops project list --target-org my-devops-org --json | \
     jq -r '.result.projects[] | "\(.Id): \(.Name) — \(.Description // "(no description)")"'
   ```
   Output:
   ```text
   1Qg000000000001: Project Alpha — Core platform release pipeline
   1Qg000000000002: Project Beta — (no description)
   ```

---

## Workflow 2: Create a New Project (Entry Point for a Release)

**User request:** "Set up a new DevOps Center project called 'Release Q3' for our Q3 features"

**Steps:**

1. **Idempotent check** — confirm it doesn't already exist:
   ```bash
   NAME="Release Q3"
   EXISTING_ID=$(sf devops project list --target-org my-devops-org --json | \
     jq -r ".result.projects[] | select(.Name == \"$NAME\") | .Id" | head -n1)
   ```

2. **Create only if not found**:
   ```bash
   if [ -n "$EXISTING_ID" ]; then
     echo "Project already exists: $EXISTING_ID"
   else
     # Create, then read the ID back from the authoritative list envelope
     sf devops project create \
       --target-org my-devops-org \
       --name "$NAME" \
       --description "Q3 feature release pipeline" \
       --json >/dev/null
     NEW_ID=$(sf devops project list --target-org my-devops-org --json | \
       jq -r ".result.projects[] | select(.Name == \"$NAME\") | .Id" | head -n1)
     echo "Created project: $NEW_ID"
   fi
   ```

   > In practice, use `scripts/create-project.sh "$NAME" "Q3 feature release pipeline"` — it performs this idempotent create-then-verify and prints `EXISTING <id>` or `CREATED <id>`.

3. **Hand off the project ID** to `dx-devops-work-item-manage` or `dx-devops-pipeline-manage` for the next steps.

---

## Workflow 3: Resolve a Project Name to Its ID

**User request:** "What's the project ID for Project Alpha?"

**Steps:**

1. **Filter the list by name**:
   ```bash
   sf devops project list --target-org my-devops-org --json | \
     jq -r '.result.projects[] | select(.Name == "Project Alpha") | .Id'
   ```
   Output: `1Qg000000000001`

2. **Return the ID** so downstream skills (work items, pipelines) can use it.

---

## Workflow 4: Rename a Project

**User request:** "Rename 'Project Alpha' to 'Platform Core'"

Resolve the name to an ID, update it, then verify:

```bash
PROJECT_ID=$(sf devops project list --target-org my-devops-org --json | \
  jq -r '.result.projects[] | select(.Name == "Project Alpha") | .Id')

sf devops project update \
  --target-org my-devops-org \
  --project-id "$PROJECT_ID" \
  --name "Platform Core" \
  --json

sf devops project list --target-org my-devops-org --json | \
  jq -r ".result.projects[] | select(.Id == \"$PROJECT_ID\") | .Name"   # -> Platform Core
```

---

## Workflow 5: Update Project Description

**User request:** "Update the description for project 1Qg000000000001 to note it now covers services too"

```bash
sf devops project update \
  --target-org my-devops-org \
  --project-id 1Qg000000000001 \
  --description "Core platform + services release pipeline" \
  --json

# Confirm from the authoritative list envelope
sf devops project list --target-org my-devops-org --json | \
  jq -r '.result.projects[] | select(.Id == "1Qg000000000001") | .Description'
```

---

## Workflow 6: Update Multiple Fields at Once

**User request:** "Rename project 1Qg000000000002 to 'Beta Program' and update its description"

Pass every field in a single `update` call, then verify from the list envelope:

```bash
sf devops project update \
  --target-org my-devops-org \
  --project-id 1Qg000000000002 \
  --name "Beta Program" \
  --description "Early-access beta feature pipeline" \
  --json

sf devops project list --target-org my-devops-org --json | \
  jq -r '.result.projects[] | select(.Id == "1Qg000000000002") | "\(.Name) — \(.Description)"'
```

---

## Workflow 6b: Deactivate (Archive) a Project

**User request:** "Archive project 1Qg000000000002 — we're done with the beta"

**Steps:**

1. **Deactivate the project**:
   ```bash
   sf devops project update \
     --target-org my-devops-org \
     --project-id 1Qg000000000002 \
     --no-is-active \
     --json
   ```

2. **Confirm** the project is inactive by re-reading the authoritative list envelope:
   ```bash
   sf devops project list --target-org my-devops-org --json | \
     jq -r '.result.projects[] | select(.Id == "1Qg000000000002") | .IsActive'
   ```
   Output: `false`

> To reactivate later, run the same command with `--is-active` instead of `--no-is-active`.

---

## Workflow 7: Bootstrap — First Project in a Fresh Org

**User request:** "I just enabled DevOps Center. Get me started with a project."

**Steps:**

1. **Confirm the org has DevOps Center and list existing projects**:
   ```bash
   sf devops project list --target-org my-devops-org --json | jq '.result.projects | length'
   ```
   Output: `0` (empty — no projects yet)

2. **Create the first project**:
   ```bash
   sf devops project create \
     --target-org my-devops-org \
     --name "Main Release Pipeline" \
     --description "Primary continuous delivery project" \
     --json
   ```

3. **Report the project ID** and guide the user to the next step:
   > Project created (ID: `1Qg000000000010`). Next, create a pipeline with `dx-devops-pipeline-manage` and work items with `dx-devops-work-item-manage`.
