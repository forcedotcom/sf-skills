# Opportunity Stage Descriptions

The Pipeline Management agent reads stage semantics from the `OpptStageDescription` setup entity (Tooling API), NOT from the standard `OpportunityStage.Description` field.

---

## Storage Entity: `OpptStageDescription`

| Fact | Detail |
|------|--------|
| **Entity** | `OpptStageDescription` (setup BPO) |
| **Fields** | `DeveloperName` (required), `MasterLabel` (required), `OpportunityStageApiName` (required), `Description` (required) |
| **Access** | Tooling API only — full CRUD |
| **Scope** | Per-record-type |
| **Requirement** | Pipeline Management must be enabled |

**CRITICAL — Visibility Prerequisite**: The `OpptStageDescription` Tooling API object is **ONLY visible and accessible AFTER Pipeline Management is enabled** (`SalesDealAgentSettings.enableDealAgent = true`). Before enablement:
- Tooling API queries return `INVALID_TYPE` or empty results
- The object does not appear in Tooling API describe calls
- Setup UI pages for stage descriptions are hidden

**You MUST enable Pipeline Management (Phase 3 in setup-all.sh) BEFORE attempting any OpptStageDescription queries or DML.**

**How it feeds the prompt**: The flow calls `GetOpportunityStageDetailsInvocableAction`, which queries `OpptStageDescription` records and injects them as grounding data into the Recommend Stage for Opportunity prompt template.

---

## Auto-Provisioned Descriptions

**Important**: When Pipeline Management is enabled, the platform MAY auto-provision stage descriptions for all active stages. This behavior was observed in test orgs — MEDDIC-aligned descriptions appeared automatically.

**Always check for existing descriptions BEFORE creating**. If you attempt to create a description for a stage that already has one, you get a `DUPLICATE_VALUE` error.

---

## CLI Automation (Tooling API)

### Query existing stage descriptions

```bash
sf data query -q "SELECT Id, OpportunityStageApiName, Description FROM OpptStageDescription" \
  --target-org pipeline-mgmt-org --use-tooling-api --json 2>/dev/null
```

### Detect stages without descriptions

```bash
# Get all active stages
sf data query -q "SELECT MasterLabel, ApiName FROM OpportunityStage WHERE IsActive = true ORDER BY SortOrder" \
  --target-org pipeline-mgmt-org --json 2>/dev/null

# Get all described stages
sf data query -q "SELECT OpportunityStageApiName FROM OpptStageDescription" \
  --target-org pipeline-mgmt-org --use-tooling-api --json 2>/dev/null

# Compare — any active stage NOT in OpptStageDescription needs a description
```

### Create a stage description

```bash
sf data create record --sobject OpptStageDescription \
  --values "DeveloperName='Qualification' MasterLabel='Qualification' OpportunityStageApiName='Qualification' Description='Budget confirmed, decision-maker identified, need validated, timeline discussed. All four BANT criteria must be met to advance past this stage.'" \
  --target-org pipeline-mgmt-org --use-tooling-api --json 2>/dev/null
```

### Update an existing stage description

```bash
sf data update record --sobject OpptStageDescription --record-id <Id> \
  --values "Description='Updated: Budget confirmed AND authority identified AND need validated AND timeline within 6 months.'" \
  --target-org pipeline-mgmt-org --use-tooling-api --json 2>/dev/null
```

### Upsert pattern (create-or-update)

Use this to avoid DUPLICATE_VALUE errors when descriptions may already exist:

```bash
ORG="pipeline-mgmt-org"
STAGE_API="Prospecting"
DESCRIPTION="Initial outreach and qualification. Entry: Lead converted. Exit: Meeting scheduled."

# Check if description exists
EXISTING_ID=$(sf data query -q "SELECT Id FROM OpptStageDescription WHERE OpportunityStageApiName='${STAGE_API}'" \
  --target-org $ORG --use-tooling-api --json 2>/dev/null | jq -r '.result.records[0].Id // empty')

if [[ -n "$EXISTING_ID" ]]; then
  # Update
  sf data update record --sobject OpptStageDescription --record-id "$EXISTING_ID" \
    --values "Description='${DESCRIPTION}'" \
    --target-org $ORG --use-tooling-api --json 2>/dev/null
else
  # Create
  sf data create record --sobject OpptStageDescription \
    --values "DeveloperName='${STAGE_API}' MasterLabel='${STAGE_API}' OpportunityStageApiName='${STAGE_API}' Description='${DESCRIPTION}'" \
    --target-org $ORG --use-tooling-api --json 2>/dev/null
fi
```

---

## OOTB Default Descriptions

Use the "propose and correct" pattern — present these defaults to the user, ask what doesn't match their process, then deploy the corrected set.

### Standard B2B Stages

| Stage API Name | Description |
|----------------|-------------|
| `Prospecting` | Initial outreach and qualification. Entry: Lead converted or manual creation. Exit: Meeting scheduled or qualified out. |
| `Qualification` | Budget confirmed, decision-maker identified, need validated, timeline discussed. Entry: Prospecting complete. Exit: All BANT criteria met. |
| `Needs_Analysis` | Deep discovery underway. Pain points validated, technical requirements gathered. Entry: Qualification passed. Exit: Requirements documented. |
| `Value_Proposition` | Solution presented addressing specific needs. ROI quantified. Entry: Needs analysis complete. Exit: Prospect agrees solution fits needs. |
| `Id_Decision_Makers` | All stakeholders identified and engaged. Decision process documented. Entry: Value prop accepted. Exit: All decision-makers on board. |
| `Perception_Analysis` | Prospect evaluating and comparing solutions. Objections being handled. Entry: Decision-makers identified. Exit: Objections resolved, ready for proposal. |
| `Proposal_Price_Quote` | Formal proposal submitted. Pricing under review. Entry: Perception analysis complete. Exit: Proposal accepted or counter-proposal submitted. |
| `Negotiation_Review` | Contract terms under discussion. Legal review in progress. Entry: Proposal accepted. Exit: Terms agreed, ready to close. |
| `Closed_Won` | Deal closed successfully. Contract signed. Entry: Negotiation complete. Exit: None (terminal stage). |
| `Closed_Lost` | Deal lost. Entry: Any stage. Exit: None (terminal stage). Lost reason required. |

### MEDDIC Methodology

| Stage API Name | Description |
|----------------|-------------|
| `Metrics` | Quantify economic impact. Entry: Initial contact. Exit: Customer agrees on measurable value. |
| `Economic_Buyer` | Identify who controls budget. Entry: Metrics defined. Exit: Economic buyer engaged. |
| `Decision_Criteria` | Understand evaluation criteria. Entry: Economic buyer identified. Exit: Criteria documented and aligned. |
| `Decision_Process` | Map decision-making process. Entry: Criteria defined. Exit: Process timeline documented. |
| `Identify_Pain` | Validate business pain. Entry: Decision process mapped. Exit: Pain confirmed and quantified. |
| `Champion` | Identify internal advocate. Entry: Pain validated. Exit: Champion actively selling internally. |
| `Proposal` | Present formal proposal. Entry: Champion engaged. Exit: Proposal accepted. |
| `Negotiation` | Finalize terms. Entry: Proposal accepted. Exit: Contract signed. |

### SPICED Methodology

| Stage API Name | Description |
|----------------|-------------|
| `Situation` | Understand current state. Entry: First contact. Exit: Current state documented. |
| `Pain` | Identify pain points. Entry: Situation understood. Exit: Pain points validated. |
| `Impact` | Quantify impact of pain. Entry: Pain identified. Exit: Impact measured and agreed. |
| `Critical_Event` | Identify urgency driver. Entry: Impact quantified. Exit: Critical event confirmed. |
| `Decision` | Understand decision process. Entry: Critical event identified. Exit: Decision process mapped. |
| `Proposal` | Present solution. Entry: Decision process mapped. Exit: Proposal accepted. |
| `Negotiation` | Finalize terms. Entry: Proposal accepted. Exit: Contract signed. |

---

## Bulk Create Script

```bash
ORG="pipeline-mgmt-org"

# Standard B2B stages
declare -a STAGES=(
  "Prospecting|Initial outreach and qualification. Entry: Lead converted or manual creation. Exit: Meeting scheduled or qualified out."
  "Qualification|Budget confirmed, decision-maker identified, need validated, timeline discussed. Entry: Prospecting complete. Exit: All BANT criteria met."
  "Needs_Analysis|Needs Analysis|Deep discovery underway. Pain points validated, technical requirements gathered. Entry: Qualification passed. Exit: Requirements documented."
  "Value_Proposition|Value Proposition|Solution presented addressing specific needs. ROI quantified. Entry: Needs analysis complete. Exit: Prospect agrees solution fits needs."
  "Id_Decision_Makers|Id. Decision Makers|All stakeholders identified and engaged. Decision process documented. Entry: Value prop accepted. Exit: All decision-makers on board."
  "Perception_Analysis|Perception Analysis|Prospect evaluating and comparing solutions. Objections being handled. Entry: Decision-makers identified. Exit: Objections resolved."
  "Proposal_Price_Quote|Proposal/Price Quote|Formal proposal submitted. Pricing under review. Entry: Perception analysis complete. Exit: Proposal accepted."
  "Negotiation_Review|Negotiation/Review|Contract terms under discussion. Legal review in progress. Entry: Proposal accepted. Exit: Terms agreed."
  "Closed_Won|Closed Won|Deal closed successfully. Contract signed. Entry: Negotiation complete. Exit: None (terminal stage)."
  "Closed_Lost|Closed Lost|Deal lost. Entry: Any stage. Exit: None (terminal stage). Lost reason required."
)

for stage_line in "${STAGES[@]}"; do
  API_NAME=$(echo "$stage_line" | cut -d'|' -f1)
  LABEL=$(echo "$stage_line" | cut -d'|' -f2)
  DESC=$(echo "$stage_line" | cut -d'|' -f3)
  
  # Handle two-field vs three-field format
  if [ -z "$DESC" ]; then
    DESC="$LABEL"
    LABEL="$API_NAME"
  fi
  
  echo "Creating description for stage: $LABEL"
  sf data create record --sobject OpptStageDescription \
    --values "DeveloperName='${API_NAME}' MasterLabel='${LABEL}' OpportunityStageApiName='${LABEL}' Description='${DESC}'" \
    --target-org $ORG --use-tooling-api --json 2>/dev/null
done
```

---

## Propose-and-Correct Pattern

Use this workflow with users:

1. **Query active stages** in their org:
   ```bash
   sf data query -q "SELECT MasterLabel, ApiName FROM OpportunityStage WHERE IsActive = true ORDER BY SortOrder" --target-org $ORG --json 2>/dev/null
   ```

2. **Present matching default descriptions** from the tables above

3. **Ask**: "Review these defaults — tell me which ones don't match your process and I'll adjust before deploying"

4. **Apply corrections** based on user feedback

5. **Bulk-create** via Tooling API using the corrected descriptions

---

## Troubleshooting

### Stage suggestions fail

**Symptom**: Next Step suggestions work, but Stage suggestions never appear

**Cause**: Missing stage descriptions (prompt template calls `GetOpportunityStageDetailsInvocableAction` which returns empty if no descriptions exist)

**Fix**: Create descriptions for all active stages

### DUPLICATE_VALUE error

**Symptom**: `sf data create record` fails with "Duplicate value"

**Cause**: Description already exists for that stage

**Fix**: Query existing descriptions, update instead of create

### Stage description not visible in UI

**Symptom**: Created via Tooling API but doesn't show in Pipeline Management setup UI

**Cause**: UI caching or record type mismatch

**Fix**: 
- Refresh UI (hard refresh: Cmd+Shift+R)
- Verify `OpportunityStageApiName` matches exact stage API name (case-sensitive)
- Check if stage is active: `SELECT IsActive FROM OpportunityStage WHERE ApiName = 'YourStage'`

---

## Notes

- Stage descriptions are **per-record-type** (Setup UI has record type dropdown)
- If multiple record types use different stages, create separate descriptions for each
- Use **active voice** ("Entry: X happens", not "Entry: When X happens")
- Include **entry criteria** (what must be true to enter this stage) and **exit criteria** (what must be true to move to next stage)
- Descriptions feed the LLM prompt — be specific and actionable
- `OpptStageDescription` is Tooling API only — NOT accessible via standard SOQL
- Always use `2>/dev/null` on `sf ... --json` piped to jq
