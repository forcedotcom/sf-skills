# DevOps Center Work Item CLI Commands Reference

Complete reference for `sf devops work-item` CLI commands with JSON output schemas and common patterns.

## Command Summary

| Command | Purpose | Required Flags | Optional Flags |
|---------|---------|---------------|----------------|
| `sf devops work-item list` | List all work items in a project | `--project-id` | `--api-version` |
| `sf devops work-item create` | Create new work item | `--project-id`, `--subject` | `--description`, `--api-version` |
| `sf devops work-item update` | Update work item fields or status | `--work-item-name` OR `--work-item-id`, plus at least one of: `--subject`, `--description`, `--status` | `--api-version` |
| `sf devops review create` | Create pull request for work item | `--work-item-name` OR `--work-item-id` | `--api-version` |

All commands support `--json` for structured output and `--target-org <alias>` for multi-org scenarios.

**Org Authentication:**
Before running any DevOps Center commands, verify org authentication:
```bash
sf org display --json
```

If no default org is set or the user wants to target a specific org, add `--target-org <alias>` to all commands.

---

## List Work Items

### Basic Usage

```bash
sf devops work-item list --project-id <project-id> --json
```

### Example

```bash
# List all work items for project 1Qg000000000001
sf devops work-item list --target-org my-devops-org --project-id 1Qg000000000001 --json
```

### JSON Output Schema

```json
{
  "status": 0,
  "result": [
    {
      "id": "0Wx000000000001AAA",
      "name": "WI-000001",
      "subject": "Fix login bug",
      "description": "Users can't log in on mobile devices",
      "branch": "feature/fix-login",
      "environment": "dev-scratch-1",
      "repositoryUrl": "https://github.com/org/repo",
      "status": "In Progress",
      "lastModifiedDate": "2026-07-22T10:30:00.000Z",
      "createdDate": "2026-07-20T08:15:00.000Z"
    },
    {
      "id": "0Wx000000000002AAA",
      "name": "WI-000002",
      "subject": "Add dark mode",
      "description": "",
      "branch": "feature/dark-mode",
      "environment": "dev-scratch-2",
      "repositoryUrl": "https://github.com/org/repo",
      "status": "Ready to Promote",
      "lastModifiedDate": "2026-07-21T15:45:00.000Z",
      "createdDate": "2026-07-19T09:00:00.000Z"
    }
  ]
}
```

### Key Fields

- `id`: Salesforce record ID (use with `--work-item-id`)
- `name`: Human-readable work item name like WI-000001 (use with `--work-item-name`)
- `subject`: Title of the work item
- `description`: Detailed description (may be empty string)
- `branch`: Git branch associated with this work item
- `environment`: Development environment name
- `status`: Current work item status

---

## Create Work Item

### Required Fields

```bash
sf devops work-item create \
  --project-id <project-id> \
  --subject "<subject>" \
  --json
```

### With Optional Description

```bash
sf devops work-item create \
  --project-id 1Qg000000000001 \
  --subject "Fix login bug" \
  --description "Users can't log in on mobile devices" \
  --json
```

### JSON Output Schema

```json
{
  "status": 0,
  "result": {
    "id": "0Wx000000000003AAA",
    "name": "WI-000003",
    "subject": "Fix login bug",
    "description": "Users can't log in on mobile devices",
    "branch": "feature/fix-login-bug",
    "environment": "dev-scratch-3",
    "repositoryUrl": "https://github.com/org/repo",
    "status": "New",
    "createdDate": "2026-07-22T11:00:00.000Z"
  }
}
```

---

## Update Work Item

### Update Subject

```bash
sf devops work-item update \
  --work-item-name WI-000001 \
  --subject "Fix critical login bug" \
  --json
```

### Update Description

```bash
sf devops work-item update \
  --work-item-name WI-000001 \
  --description "Updated description with repro steps: 1. Open app on iOS 2. Tap login..." \
  --json
```

### Update Status

```bash
sf devops work-item update \
  --work-item-name WI-000001 \
  --status "In Progress" \
  --json
```

Valid status values (exact strings):
- `"In Progress"` (with space and proper capitalization)
- `"Ready to Promote"` (with space and proper capitalization)

### Update Multiple Fields

```bash
sf devops work-item update \
  --work-item-name WI-000001 \
  --subject "Fix critical login bug [P0]" \
  --description "Updated with repro steps" \
  --status "In Progress" \
  --json
```

### Using Work Item ID Instead of Name

```bash
sf devops work-item update \
  --work-item-id 0Wx000000000001AAA \
  --status "Ready to Promote" \
  --json
```

> **Note:** Prefer `--work-item-name` (WI-000001) over `--work-item-id` when available — names are human-readable and easier to reference.

### JSON Output Schema

```json
{
  "status": 0,
  "result": {
    "id": "0Wx000000000001AAA",
    "name": "WI-000001",
    "subject": "Fix critical login bug [P0]",
    "description": "Updated with repro steps",
    "status": "In Progress",
    "lastModifiedDate": "2026-07-22T11:15:00.000Z"
  }
}
```

---

## Error Handling

### Common Error Scenarios

**Work item not found:**
```json
{
  "status": 1,
  "name": "NOT_FOUND",
  "message": "The requested resource does not exist",
  "exitCode": 1
}
```

**Invalid status value:**
```json
{
  "status": 1,
  "name": "INVALID_STATUS",
  "message": "Invalid status value. Allowed values: 'In Progress', 'Ready to Promote'",
  "exitCode": 1
}
```

**Missing required field (create):**
```json
{
  "status": 1,
  "name": "RequiredFlagsError",
  "message": "Missing required flag --subject",
  "exitCode": 1
}
```

**Missing update field:**
```json
{
  "status": 1,
  "name": "RequiredFlagsError",
  "message": "At least one of --subject, --description, or --status must be provided",
  "exitCode": 1
}
```

**Project not found:**
```json
{
  "status": 1,
  "name": "NOT_FOUND",
  "message": "Project with ID 1Qg000000000999 does not exist or is not accessible",
  "exitCode": 1
}
```

**Authentication failure:**
```json
{
  "status": 1,
  "name": "NoOrgFound",
  "message": "No org configuration found for target-org. Run 'sf org login web' to authenticate.",
  "exitCode": 1
}
```

---

## Parsing JSON Output

### Extract Work Item Name (create operation)

```bash
# Store work item name in a variable
WORK_ITEM_NAME=$(sf devops work-item create \
  --project-id 1Qg000000000001 \
  --subject "Test WI" \
  --json | jq -r '.result.name')

echo "Created work item: $WORK_ITEM_NAME"
# Output: Created work item: WI-000004
```

### Check for Empty List

```bash
# Count returned work items
COUNT=$(sf devops work-item list --project-id 1Qg000000000001 --json | jq '.result | length')

if [ "$COUNT" -eq 0 ]; then
  echo "No work items found for this project"
else
  echo "Found $COUNT work items"
fi
```

### Extract Specific Fields

```bash
# List work item names and subjects
sf devops work-item list --project-id 1Qg000000000001 --json | \
  jq -r '.result[] | "\(.name): \(.subject)"'

# Output:
# WI-000001: Fix login bug
# WI-000002: Add dark mode
```

### Filter by Status

```bash
# Find all work items with "Ready to Promote" status
sf devops work-item list --project-id 1Qg000000000001 --json | \
  jq -r '.result[] | select(.status == "Ready to Promote") | "\(.name): \(.subject)"'
```

---

## Idempotent Create Pattern

To avoid duplicate work items, check for existing work items with the same subject before creating:

```bash
PROJECT_ID="1Qg000000000001"
SUBJECT="Fix login bug"

# Check if work item with subject exists
EXISTING_NAME=$(sf devops work-item list \
  --project-id "$PROJECT_ID" \
  --json | \
  jq -r ".result[] | select(.subject == \"$SUBJECT\") | .name" | head -n1)

if [ -n "$EXISTING_NAME" ]; then
  echo "Work item already exists: $EXISTING_NAME"
else
  # Create new work item
  NEW_NAME=$(sf devops work-item create \
    --project-id "$PROJECT_ID" \
    --subject "$SUBJECT" \
    --json | jq -r '.result.name')
  echo "Created new work item: $NEW_NAME"
fi
```

---

## Authentication Requirements

All `sf devops work-item` commands require:

1. **Authenticated org**: `sf org login web` or JWT auth
2. **DevOps Center enabled**: Org must have DOCe provisioned
3. **Appropriate permissions**: User must have access to the project

Verify authentication before running commands:

```bash
sf org display --target-org <alias> --json
```

If authentication fails, the user must run:

```bash
sf org login web --set-default --alias <alias>
```

---

## Create Pull Request

### Basic Usage

```bash
sf devops review create \
  --work-item-name <WI-name> \
  --json
```

### Example with Work Item Name

```bash
sf devops review create \
  --work-item-name WI-000001 \
  --json
```

### Example with Work Item ID

```bash
sf devops review create \
  --work-item-id 0Wx000000000001AAA \
  --json
```

> **Note:** Prefer `--work-item-name` (WI-000001) over `--work-item-id` when available — names are human-readable and easier to reference.

### JSON Output Schema

```json
{
  "status": 0,
  "result": {
    "id": "0PR000000000001AAA",
    "workItemId": "0Wx000000000001AAA",
    "workItemName": "WI-000001",
    "pullRequestUrl": "https://github.com/org/repo/pull/42",
    "pullRequestNumber": 42,
    "pullRequestStatus": "open",
    "createdDate": "2026-07-23T10:00:00.000Z"
  }
}
```

### Key Fields

- `pullRequestUrl`: Direct link to the PR in VCS (GitHub or Bitbucket)
- `pullRequestNumber`: PR number in the VCS system
- `pullRequestStatus`: Current status (typically "open" at creation)
- `workItemName`: Work item the PR was created for
- `id`: Salesforce record ID for the review record

### How It Works

- Uses VCS credentials stored in DevOps Center org (not local git auth)
- Creates PR from work item's branch to the pipeline's base branch
- Works with GitHub and Bitbucket
- Requires VCS connection configured in DevOps Center UI first

### Error Scenarios

**VCS credentials not configured:**
```json
{
  "status": 1,
  "name": "VCS_NOT_CONFIGURED",
  "message": "VCS connection not configured for this project. Configure in DevOps Center UI first.",
  "exitCode": 1
}
```

**Work item not found:**
```json
{
  "status": 1,
  "name": "NOT_FOUND",
  "message": "Work item WI-000999 does not exist or is not accessible",
  "exitCode": 1
}
```

**PR already exists:**
```json
{
  "status": 1,
  "name": "PR_ALREADY_EXISTS",
  "message": "A pull request already exists for work item WI-000001",
  "exitCode": 1
}
```

---

## Getting Project ID

If the user doesn't provide a project ID, list available projects first:

```bash
sf devops project list --json | jq -r '.result[] | "\(.id): \(.name)"'
```

Output:
```text
1Qg000000000001: Project Alpha
1Qg000000000002: Project Beta
```

Then use the ID in subsequent work item commands.
