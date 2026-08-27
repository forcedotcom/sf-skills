# DevOps Center Pipeline — Parsing, Errors & Auth

jq snippets for parsing `sf devops` JSON output, error-handling reference, the idempotent check-before-create pattern, and authentication requirements. For command flags and JSON schemas, see `references/cli-commands.md`.

## Parsing Stage Chains

Stages form a linked list via `nextStageId` (see the schema in `references/cli-commands.md`). Use these snippets against `pipeline get`:

```bash
# List stage names and IDs with their next pointer
sf devops pipeline get --pipeline-id 1PJWt000000HLUfOAO --json | \
  jq -r '.result.stages[] | "\(.name) (\(.id)) -> next: \(.nextStageId)"'

# Find the terminal stage ID (nextStageId is null)
sf devops pipeline get --pipeline-id 1PJWt000000HLUfOAO --json | \
  jq -r '.result.stages[] | select(.nextStageId == null) | .id'

# Find a stage ID by name (e.g. to anchor an insert before "Production")
sf devops pipeline get --pipeline-id 1PJWt000000HLUfOAO --json | \
  jq -r '.result.stages[] | select(.name == "Production") | .id'
```

---

## Resolve a Pipeline ID by Name

`pipeline list` is the reliable way to turn a pipeline name into an ID (note the `.pipelines[]` wrapper and capitalized `Name`/`Id`):

```bash
PIPELINE_ID=$(sf devops pipeline list --json | \
  jq -r '.result.pipelines[] | select(.Name == "Release Pipeline") | .Id' | head -n1)
echo "Pipeline: $PIPELINE_ID"
```

### List Pipelines (name, ID, active state)

`pipeline list` does not carry stages — to show the stage chain, feed each ID into `pipeline get`:

```bash
sf devops pipeline list --json | \
  jq -r '.result.pipelines[] | "\(.Name) [\(.IsActive)] (\(.Id))"'
# Release Pipeline [true] (1PJWt000000HLUfOAO)
```

---

## Resolve a Project ID by Name

`project list` returns SObject records under `.result.projects[]` with capitalized fields (`Id`, `Name`):

```bash
sf devops project list --json | jq -r '.result.projects[] | "\(.Id): \(.Name)"'

# Extract a specific project ID by name
sf devops project list --json | \
  jq -r '.result.projects[] | select(.Name == "Release Project 1") | .Id'
```

---

## Idempotent Create (Check-Before-Create)

The CLI does not dedupe pipelines. Check for an existing pipeline before creating:

```bash
PIPELINE_NAME="Release Pipeline"

EXISTING_ID=$(sf devops pipeline list --json | \
  jq -r ".result.pipelines[] | select(.Name == \"$PIPELINE_NAME\") | .Id" | head -n1)

if [ -n "$EXISTING_ID" ]; then
  echo "Pipeline already exists: $EXISTING_ID"
else
  sf devops pipeline create \
    --name "$PIPELINE_NAME" \
    --repo https://github.com/myorg/myrepo \
    --json
  NEW_ID=$(sf devops pipeline list --json | \
    jq -r ".result.pipelines[] | select(.Name == \"$PIPELINE_NAME\") | .Id" | head -n1)
  echo "Created new pipeline: $NEW_ID"
fi
```

---

## Error Handling

**Missing required repo (create):**
```json
{ "status": 1, "name": "RequiredFlagsError", "message": "Missing required flag --repo", "exitCode": 1 }
```

**Pipeline not found:**
```json
{ "status": 1, "name": "NOT_FOUND", "message": "Pipeline 0XB000000000999 does not exist or is not accessible", "exitCode": 1 }
```

**Activation without a stage:**
```json
{ "status": 1, "name": "NO_STAGES", "message": "A pipeline must have at least one stage before you can activate it", "exitCode": 1 }
```

**Environment delete on active pipeline:**
```json
{ "status": 1, "name": "PIPELINE_ACTIVE", "message": "The environment must belong to an inactive pipeline", "exitCode": 1 }
```

**Project already attached:**
```json
{ "status": 1, "name": "PROJECT_ALREADY_ATTACHED", "message": "You can attach a project to only one pipeline", "exitCode": 1 }
```

**Authentication failure:**
```json
{ "status": 1, "name": "NoOrgFound", "message": "No org configuration found for target-org. Run 'sf org login web' to authenticate.", "exitCode": 1 }
```

> **Note:** Error `name`/`message` strings are representative — match on the non-zero `status` and the substring of `message`, not exact strings.

---

## Authentication Requirements

All `sf devops pipeline` / `sf devops stage` commands require:

1. **Authenticated org**: `sf org login web` or JWT auth
2. **DevOps Center enabled**: org must have DOCe provisioned
3. **Appropriate permissions**: access to the pipeline, its stages, and connected environments

```bash
sf org display --target-org <alias> --json
```

If auth fails: `sf org login web --set-default --alias <alias>`.
