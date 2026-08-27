# Common Work Item Management Workflows

Real-world examples of typical work item operations in DevOps Center autonomous release scenarios.

---

## Workflow 1: Full Lifecycle — Create, Develop, Commit, and PR

**User request:** "Create a work item for adding email validation to Contact records, implement it, then create a PR when done"

**Steps:**

1. **Get project ID** (if not already known):
   ```bash
   sf devops project list --json
   ```
   Output: Project ID `1Qg000000000001`

2. **Create work item**:
   ```bash
   sf devops work-item create \
     --project-id 1Qg000000000001 \
     --subject "Add email validation to Contact" \
     --description "Enforce @salesforce.com domain on Contact email field" \
     --json
   ```
   Output: Work item name `WI-000001`, branch name `feature/wi-000001-add-email-validation`

3. **Update status to In Progress** when development starts:
   ```bash
   sf devops work-item update \
     --work-item-name WI-000001 \
     --status "In Progress" \
     --json
   ```

4. **Make code changes on the work item branch**:
   ```bash
   # Get branch name from work item
   BRANCH=$(sf devops work-item list --project-id 1Qg000000000001 --json | \
     jq -r '.result[] | select(.name == "WI-000001") | .branch')
   
   # Checkout the branch
   git checkout "$BRANCH"
   
   # Make changes to files
   # (user implements email validation here)
   ```

5. **Commit and push changes**:
   ```bash
   git add force-app/main/default/objects/Contact/fields/Email.field-meta.xml
   git commit -m "Add email validation rule for @salesforce.com domain"
   git push origin "$BRANCH"
   ```

6. **Update status to Ready to Promote** when work is complete:
   ```bash
   sf devops work-item update \
     --work-item-name WI-000001 \
     --status "Ready to Promote" \
     --json
   ```

7. **Create pull request** for code review:
   ```bash
   sf devops review create \
     --work-item-name WI-000001 \
     --json
   ```
   Output: PR URL `https://github.com/org/repo/pull/42`

8. **List work items** to confirm final state:
   ```bash
   sf devops work-item list --project-id 1Qg000000000001 --json | \
     jq -r '.result[] | select(.name == "WI-000001") | {name, subject, status}'
   ```

---

## Workflow 2: Bulk Status Update for Promotion

**User request:** "Mark all work items with 'In Progress' status as Ready to Promote"

**Steps:**

1. **List work items in In Progress status**:
   ```bash
   sf devops work-item list --project-id 1Qg000000000001 --json | \
     jq -r '.result[] | select(.status == "In Progress") | .name'
   ```
   Output: Work item names `WI-000001`, `WI-000002`

2. **Update each to Ready to Promote**:
   ```bash
   for WI in WI-000001 WI-000002; do
     sf devops work-item update \
       --work-item-name $WI \
       --status "Ready to Promote" \
       --json
   done
   ```

3. **Verify all transitioned**:
   ```bash
   sf devops work-item list --project-id 1Qg000000000001 --json | \
     jq -r '.result[] | select(.status == "Ready to Promote") | {name, subject}'
   ```

---

## Workflow 3: Commit Changes to Work Item Branch

**User request:** "I made changes to the Apex class for work item WI-000003, commit and push them"

**Steps:**

1. **Get the work item's branch name**:
   ```bash
   BRANCH=$(sf devops work-item list --project-id 1Qg000000000001 --json | \
     jq -r '.result[] | select(.name == "WI-000003") | .branch')
   echo "Work item branch: $BRANCH"
   ```
   Output: `feature/wi-000003-refactor-service`

2. **Checkout the work item branch** (if not already on it):
   ```bash
   git checkout "$BRANCH"
   ```

3. **Stage the changed files**:
   ```bash
   git add force-app/main/default/classes/AccountService.cls
   git add force-app/main/default/classes/AccountService.cls-meta.xml
   ```

4. **Commit with a descriptive message**:
   ```bash
   git commit -m "Refactor AccountService for better testability"
   ```
   Output: Commit SHA `a1b2c3d4`

5. **Push to the work item branch**:
   ```bash
   git push origin "$BRANCH"
   ```

---

## Workflow 4: Update Work Item After Requirements Change

**User request:** "Update work item WI-000001 subject to include P0 priority tag"

**Steps:**

1. **Update subject**:
   ```bash
   sf devops work-item update \
     --work-item-name WI-000001 \
     --subject "[P0] Add email validation to Contact" \
     --json
   ```

2. **Update description** with new requirements:
   ```bash
   sf devops work-item update \
     --work-item-name WI-000001 \
     --description "UPDATED: Enforce @salesforce.com domain. Must deploy by EOD Friday." \
     --json
   ```

3. **Update multiple fields at once** (alternative):
   ```bash
   sf devops work-item update \
     --work-item-name WI-000001 \
     --subject "[P0] Add email validation to Contact" \
     --description "UPDATED: Enforce @salesforce.com domain. Must deploy by EOD Friday." \
     --json
   ```

---

## Workflow 5: Find Work Items Ready for Promotion

**User request:** "Show me all work items ready to promote in Project Alpha"

**Steps:**

1. **Get project ID** (if using project name):
   ```bash
   PROJECT_ID=$(sf devops project list --json | \
     jq -r '.result[] | select(.name == "Project Alpha") | .id')
   ```

2. **List work items with Ready to Promote status**:
   ```bash
   sf devops work-item list --project-id "$PROJECT_ID" --json | \
     jq -r '.result[] | select(.status == "Ready to Promote") | {name, subject, branch}'
   ```

3. **Delegate to promotion skill**:
   User intent is to promote these work items → delegate to `dx-devops-promote` skill with the work item names

---

## Workflow 6: Idempotent Work Item Creation

**User request:** "Create work item for API rate limit fix (if it doesn't exist)"

**Steps:**

1. **Check for existing work item**:
   ```bash
   PROJECT_ID="1Qg000000000001"
   SUBJECT="Fix API rate limit on bulk operations"

   EXISTING_NAME=$(sf devops work-item list \
     --project-id "$PROJECT_ID" \
     --json | \
     jq -r ".result[] | select(.subject == \"$SUBJECT\") | .name" | head -n1)
   ```

2. **Create only if not found**:
   ```bash
   if [ -n "$EXISTING_NAME" ]; then
     echo "Work item already exists: $EXISTING_NAME"
   else
     NEW_NAME=$(sf devops work-item create \
       --project-id "$PROJECT_ID" \
       --subject "$SUBJECT" \
       --json | jq -r '.result.name')
     echo "Created new work item: $NEW_NAME"
   fi
   ```

---

## Workflow 7: List Work Items with Filtering

**User request:** "Show me all work items in Project Beta that haven't been started yet"

**Steps:**

1. **List all work items and filter by status**:
   ```bash
   PROJECT_ID="1Qg000000000002"
   
   sf devops work-item list --project-id "$PROJECT_ID" --json | \
     jq -r '.result[] | select(.status != "In Progress" and .status != "Ready to Promote") | 
     {name, subject, status, branch}'
   ```

2. **Alternative: show work items in progress**:
   ```bash
   sf devops work-item list --project-id "$PROJECT_ID" --json | \
     jq -r '.result[] | select(.status == "In Progress") | 
     "\(.name): \(.subject) (branch: \(.branch))"'
   ```

---

## Workflow 8: Batch Create Work Items

**User request:** "Create work items for three bug fixes: login issue, search timeout, and export error"

**Steps:**

1. **Create each work item**:
   ```bash
   PROJECT_ID="1Qg000000000001"
   
   # Bug 1
   WI1=$(sf devops work-item create \
     --project-id "$PROJECT_ID" \
     --subject "Fix login issue on mobile" \
     --description "Users unable to authenticate on iOS 17+" \
     --json | jq -r '.result.name')
   
   # Bug 2
   WI2=$(sf devops work-item create \
     --project-id "$PROJECT_ID" \
     --subject "Fix search timeout" \
     --description "Search queries timing out for large datasets" \
     --json | jq -r '.result.name')
   
   # Bug 3
   WI3=$(sf devops work-item create \
     --project-id "$PROJECT_ID" \
     --subject "Fix export error" \
     --description "CSV export failing with special characters" \
     --json | jq -r '.result.name')
   
   echo "Created work items: $WI1, $WI2, $WI3"
   ```

---

## Workflow 9: Sequential Status Progression

**User request:** "Move work item WI-000005 from initial creation to Ready to Promote"

**Steps:**

1. **Verify current status**:
   ```bash
   WORK_ITEM="WI-000005"
   CURRENT_STATUS=$(sf devops work-item list --project-id 1Qg000000000001 --json | \
     jq -r ".result[] | select(.name == \"$WORK_ITEM\") | .status")
   echo "Current status: $CURRENT_STATUS"
   ```

2. **Update to In Progress** (if currently in initial state):
   ```bash
   sf devops work-item update \
     --work-item-name $WORK_ITEM \
     --status "In Progress" \
     --json
   ```

3. **Update to Ready to Promote** (when work is complete):
   ```bash
   sf devops work-item update \
     --work-item-name $WORK_ITEM \
     --status "Ready to Promote" \
     --json
   ```

4. **Verify final status**:
   ```bash
   sf devops work-item list --project-id 1Qg000000000001 --json | \
     jq -r ".result[] | select(.name == \"$WORK_ITEM\") | .status"
   ```

---

## Workflow 10: Get Work Item Details by Name

**User request:** "Show me all details for work item WI-000001"

**Steps:**

1. **List work items and filter by name**:
   ```bash
   sf devops work-item list --project-id 1Qg000000000001 --json | \
     jq '.result[] | select(.name == "WI-000001")'
   ```

2. **Extract specific fields**:
   ```bash
   sf devops work-item list --project-id 1Qg000000000001 --json | \
     jq -r '.result[] | select(.name == "WI-000001") | 
     "Name: \(.name)\nSubject: \(.subject)\nStatus: \(.status)\nBranch: \(.branch)\nEnvironment: \(.environment)\nDescription: \(.description)"'
   ```

---

## Workflow 11: Multi-Project Work Item Search

**User request:** "Find all work items across all projects with 'login' in the subject"

**Steps:**

1. **List all projects**:
   ```bash
   sf devops project list --json | jq -r '.result[].id'
   ```
   Output: Project IDs `1Qg000000000001`, `1Qg000000000002`

2. **Search each project for matching work items**:
   ```bash
   for PROJECT_ID in 1Qg000000000001 1Qg000000000002; do
     echo "Project: $PROJECT_ID"
     sf devops work-item list --project-id "$PROJECT_ID" --json | \
       jq -r '.result[] | select(.subject | contains("login")) | 
       "  \(.name): \(.subject)"'
   done
   ```

---

## Workflow 12: Create Work Item with Empty Description

**User request:** "Create work item 'Refactor user service' with no description"

**Steps:**

1. **Create without description flag** (defaults to blank):
   ```bash
   sf devops work-item create \
     --project-id 1Qg000000000001 \
     --subject "Refactor user service" \
     --json
   ```

2. **Add description later** (if needed):
   ```bash
   sf devops work-item update \
     --work-item-name WI-000006 \
     --description "Refactor for better testability and performance" \
     --json
   ```

---

## Workflow 13: Using Work Item ID Instead of Name

**User request:** "Update work item 0Wx000000000001AAA to Ready to Promote"

**Steps:**

1. **Update using work item ID**:
   ```bash
   sf devops work-item update \
     --work-item-id 0Wx000000000001AAA \
     --status "Ready to Promote" \
     --json
   ```

> **Note:** Work item IDs (like `0Wx000000000001AAA`) are less human-readable than names (like `WI-000001`). Prefer using `--work-item-name` when possible.

---

## Workflow 14: Bulk PR Creation

**User request:** "Create PRs for all work items that are Ready to Promote"

**Steps:**

1. **List work items with Ready to Promote status**:
   ```bash
   sf devops work-item list --project-id 1Qg000000000001 --json | \
     jq -r '.result[] | select(.status == "Ready to Promote") | .name'
   ```
   Output: Work item names `WI-000001`, `WI-000003`, `WI-000005`

2. **Create PR for each work item**:
   ```bash
   for WI in WI-000001 WI-000003 WI-000005; do
     sf devops review create \
       --work-item-name $WI \
       --json | \
       jq -r '.result.pullRequestUrl'
   done
   ```
   Output: PR URLs for each work item

3. **Verify PRs were created** by listing work items again and checking for associated review records:
   ```bash
   sf devops work-item list --project-id 1Qg000000000001 --json | \
     jq -r '.result[] | select(.name == "WI-000001" or .name == "WI-000003" or .name == "WI-000005") | {name, subject, status}'
   ```

---

## Workflow 15: Check if PR Already Exists Before Creating

**User request:** "Create a PR for WI-000002, but only if one doesn't already exist"

**Steps:**

1. **Attempt to create PR** and handle "PR already exists" error:
   ```bash
   OUTPUT=$(sf devops review create --work-item-name WI-000002 --json)
   STATUS=$(echo "$OUTPUT" | jq -r '.status')
   
   if [ "$STATUS" -eq 0 ]; then
     PR_URL=$(echo "$OUTPUT" | jq -r '.result.pullRequestUrl')
     echo "PR created: $PR_URL"
   else
     ERROR_NAME=$(echo "$OUTPUT" | jq -r '.name')
     if [ "$ERROR_NAME" = "PR_ALREADY_EXISTS" ]; then
       echo "PR already exists for WI-000002"
     else
       echo "Error creating PR: $ERROR_NAME"
     fi
   fi
   ```

> **Note:** The CLI will return a non-zero status with error name `PR_ALREADY_EXISTS` if a PR already exists for that work item.
