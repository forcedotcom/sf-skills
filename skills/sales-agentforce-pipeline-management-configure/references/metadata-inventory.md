# Pipeline Management Metadata Inventory

Complete inventory of all metadata components auto-provisioned by Pipeline Management. Use this as a reference for org inspection, troubleshooting, and metadata migration.

---

## Metadata Types and Components

### 1. Settings

| Metadata Type | Full Name | Key Fields | API | Notes |
|--------------|-----------|-----------|-----|-------|
| `SalesDealAgentSettings` | `SalesDealAgent` | `enableDealAgent`, `enableDealAgentAutoApproveAllTasks` | SOAP v64.0+ only | CLI returns 'Settings type is unknown' |
| `EinsteinGptSettings` | `EinsteinGpt` | `enableGptAnswerGenerationForKbArticles` | SOAP v62.0+ or CLI | Required prerequisite |
| `EinsteinCopilotSettings` | `EinsteinCopilot` | `enableAgentLiveSuggestionsInTab` | SOAP v62.0+ or CLI | Required prerequisite |
| `EnhancedNotesSettings` | `EnhancedNotes` | `enableEnhancedNotes` | CLI retrieve+deploy | Prerequisite for note ingestion |
| `EmailAdministrationSettings` | `EmailAdministration` | `enableInternalNotesInEmailSnippet` | CLI retrieve+deploy | Prerequisite for email ingestion |
| `OpportunitySettings` | `Opportunity` | `enableFindSimilarOpportunities` | CLI retrieve+deploy | Prerequisite for grounding data |

**Retrieval**:
```bash
sf project retrieve start --metadata "Settings:SalesDealAgentSettings" --target-org $ORG 2>/dev/null
sf project retrieve start --metadata "Settings:EinsteinGptSettings" --target-org $ORG 2>/dev/null
sf project retrieve start --metadata "Settings:EinsteinCopilotSettings" --target-org $ORG 2>/dev/null
sf project retrieve start --metadata "Settings:EnhancedNotesSettings" --target-org $ORG 2>/dev/null
sf project retrieve start --metadata "Settings:EmailAdministrationSettings" --target-org $ORG 2>/dev/null
sf project retrieve start --metadata "Settings:OpportunitySettings" --target-org $ORG 2>/dev/null
```

---

### 2. Permission Set Groups

| Developer Name | API Name | Purpose | Auto-Assigned To |
|----------------|----------|---------|------------------|
| `SalesManagementUserPsg` | `SalesManagementUserPsg` | Grants end users access to Pipeline Management features | Sales users (manual assignment required) |
| `SalesManagementAgentUserPsg` | `SalesManagementAgentUserPsg` | Grants agent system user access to opportunity data | Agent user (auto-assigned on creation) |

**SOQL Query**:
```bash
sf data query -q "SELECT Id, DeveloperName, MasterLabel FROM PermissionSetGroup WHERE DeveloperName LIKE 'SalesManagement%'" --target-org $ORG --json 2>/dev/null
```

**Contained Permission Sets** (in `SalesManagementAgentUserPsg`):
- `PipelineManagementAgentAutonomousUser` — Allows autonomous field updates
- `PipelineManagementAgentBase` — Base permissions for agent operations
- (Other permission sets may vary by org edition/license)

---

### 3. Bot (Agent)

| Developer Name | Label | Type | Status | Template |
|----------------|-------|------|--------|----------|
| `SalesAgent` | `Sales Management Agent` | Agentforce | Active/Draft | `SalesMgmt__SalesAgent` |

**SOQL Query** (standard SOQL — BotDefinition has no `Label` or `Status` column, and is not supported by the Tooling API):
```bash
sf data query -q "SELECT Id, DeveloperName, Description FROM BotDefinition WHERE DeveloperName = 'SalesAgent'" --target-org $ORG --json 2>/dev/null
```

**Retrieval**:
```bash
sf project retrieve start --metadata "Bot:SalesAgent" --target-org $ORG 2>/dev/null
```

**Components**:
- Bot metadata file: `force-app/main/default/bots/SalesAgent.bot-meta.xml`
- Bot versions (auto-versioned on publish)

---

### 4. BotVersion

Active bot version(s) for `SalesAgent`. Multiple versions may exist (draft, published, active).

**SOQL Query** (standard SOQL — `BotVersion`, like `BotDefinition`, is NOT supported by the Tooling API):
```bash
sf data query -q "SELECT Id, BotDefinition.DeveloperName, VersionNumber, Status FROM BotVersion WHERE BotDefinition.DeveloperName = 'SalesAgent' ORDER BY VersionNumber DESC" --target-org $ORG --json 2>/dev/null
```

---

### 5. Flows

| API Name | Label | Type | Template | Purpose |
|----------|-------|------|----------|---------|
| `sales_pipe_mgmt__OppSuggGenSchFlow` | `Opportunity Suggestion Generation Scheduled Flow` | Scheduled-Triggered | **Yes** (do not activate directly) | Template flow for suggestion processing |
| `Process_Field_Update_Suggestions` | `Process Field Update Suggestions` | Scheduled-Triggered | No (cloned from template) | Active flow that processes suggestions |
| `sales_pipe_mgmt__GetOppGroundingData` | `Get Opportunity Grounding Data` | Invocable | No | Retrieves notes, emails, calls for grounding |
| `sales_pipe_mgmt__GetRcmdConvTscp` | `Get Recommended Conversation Transcript` | Invocable | No | Retrieves conversation transcripts |

**SOQL Queries** — use `FlowDefinitionView` (data API). `FlowDefinition` is a **metadata**
type, not a data-API sObject (`sObject type 'FlowDefinition' is not supported`, and
`--use-tooling-api` does NOT fix it — it lives in the Metadata API); `FlowDefinitionView`
is the queryable view, uses `IsActive` (not `Status`), and is what the live scripts use:
```bash
# Check all Pipeline Management flows
sf data query -q "SELECT ApiName, Label, ProcessType, IsActive, IsTemplate FROM FlowDefinitionView WHERE ApiName LIKE '%sales_pipe_mgmt%' OR ApiName LIKE '%Field_Update_Suggestions%'" --target-org $ORG --json 2>/dev/null

# Check if template flow exists
sf data query -q "SELECT ApiName, IsTemplate FROM FlowDefinitionView WHERE ApiName = 'sales_pipe_mgmt__OppSuggGenSchFlow'" --target-org $ORG --json 2>/dev/null

# Check cloned flow — query by ApiName. A Metadata-API deploy of the template does NOT
# populate FlowDefinitionView.SourceTemplateId (org-verified), so detect by name;
# SourceTemplateId is populated only for Setup-UI "Save As" clones.
sf data query -q "SELECT Id, ApiName, Label, IsActive, SourceTemplateId FROM FlowDefinitionView WHERE ApiName = 'Process_Field_Update_Suggestions' AND IsTemplate = false" --target-org $ORG --json 2>/dev/null
```

**Retrieval**:
```bash
sf project retrieve start --metadata "Flow:sales_pipe_mgmt__OppSuggGenSchFlow" --target-org $ORG 2>/dev/null
sf project retrieve start --metadata "Flow:Process_Field_Update_Suggestions" --target-org $ORG 2>/dev/null
sf project retrieve start --metadata "Flow:sales_pipe_mgmt__GetOppGroundingData" --target-org $ORG 2>/dev/null
sf project retrieve start --metadata "Flow:sales_pipe_mgmt__GetRcmdConvTscp" --target-org $ORG 2>/dev/null
```

---

### 6. GenAiPromptTemplate

| Developer Name | Label | Type | Purpose |
|----------------|-------|------|---------|
| `sales_pipe_mgmt__RecommendStageforOpp` | `Recommend Stage for Opportunity` | Prompt Template | Generates stage recommendations |
| `sales_pipe_mgmt__RecommendNextStepforOpp` | `Recommend Next Step for Opportunity` | Prompt Template | Generates next step suggestions |

**Discovery** — `GenAiPromptTemplate` is **not SOQL-queryable** (Tooling or standard both return "sObject type 'GenAiPromptTemplate' is not supported"). Use the REST discovery endpoint instead:
```bash
sf api request rest "/services/data/v64.0/einstein/prompt-templates" --target-org $ORG 2>/dev/null \
  | jq -r '.promptRecords[]? | select(.fields.DeveloperName.value | test("sales_pipe_mgmt")) | "\(.fields.DeveloperName.value)  active=\(.fields.IsActive.value)"'
```

**Retrieval**:
```bash
sf project retrieve start --metadata "GenAiPromptTemplate:sales_pipe_mgmt__RecommendStageforOpp" --target-org $ORG 2>/dev/null
sf project retrieve start --metadata "GenAiPromptTemplate:sales_pipe_mgmt__RecommendNextStepforOpp" --target-org $ORG 2>/dev/null
```

---

### 7. Agent User

| Field | Value |
|-------|-------|
| **Username pattern** | `salesmanagementagentuser@<uuid>.<org-domain>.ext` |
| **Profile** | `System Administrator` or dedicated agent profile |
| **IsActive** | `true` |
| **UserType** | `CspLitePortal` or similar agent-specific type |

**SOQL Query**:
```bash
sf data query -q "SELECT Id, Username, Name, Profile.Name, IsActive, UserType FROM User WHERE Username LIKE '%salesmanagementagentuser%'" --target-org $ORG --json 2>/dev/null
```

**Permission Set Group Assignment**:
```bash
# Get agent user ID
AGENT_USER_ID=$(sf data query -q "SELECT Id FROM User WHERE Username LIKE '%salesmanagementagentuser%'" --target-org $ORG --json 2>/dev/null | jq -r '.result.records[0].Id')

# Check PSG assignment
sf data query -q "SELECT AssigneeId, PermissionSetGroup.DeveloperName FROM PermissionSetAssignment WHERE AssigneeId = '${AGENT_USER_ID}' AND PermissionSetGroup.DeveloperName = 'SalesManagementAgentUserPsg'" --target-org $ORG --json 2>/dev/null
```

---

### 8. Setup Entities & Standard Objects

#### OpptStageDescription (Opportunity Stage Descriptions)

`OpptStageDescription` is a **Tooling-API setup entity** — NOT a `__c` custom object. It has no
`Stage__c`/`Description__c` fields and is not accessible via `sf sobject describe` or the plain data
API. It appears in `EntityDefinition`, is queryable **only with `--use-tooling-api`**, and is
auto-provisioned when Pipeline Management is enabled (test orgs show pre-populated MEDDIC rows).
Field names verified on a live org (`pm-new-org`).

| Purpose | Key fields (Tooling) | API Name | Access |
|---------|----------------------|----------|--------|
| Stores stage-to-description mappings for stage-suggestion grounding | `OpportunityStageApiName` (the stage picklist value), `Description`, `MasterLabel`, `DeveloperName` | `OpptStageDescription` (no `__c`) | Tooling API only |

> **Note:** `OpptStageDescription` has **no `OpportunityRecordTypeId` column** — descriptions are global-per-stage, keyed only by `OpportunityStageApiName`. A single description record applies across all Opportunity record types that expose that stage. (W-23356857)

**SOQL Query** (Tooling API):
```bash
sf data query -q "SELECT Id, OpportunityStageApiName, Description FROM OpptStageDescription" --target-org $ORG --use-tooling-api --json 2>/dev/null
```

`setup-all.sh` creates/updates these rows via `sf data create/update record --sobject OpptStageDescription`
(Tooling-backed); see the stage-description handling in `scripts/shared/stage-descriptions.sh`
(`run_stage_descriptions`), invoked from setup-all.sh Phase 4c.5 — BEFORE the StageName
prompt is deployed/tested, since the descriptions are that prompt's grounding.

#### AiGenActionItem (Field Update Suggestions)

`AiGenActionItem` is the **standard** object (no `__c` suffix) where Pipeline Management stores every field-update suggestion. There is **no** `FieldCompletion` / `FieldCompletion__c` object — that name does not exist on any org; do not query it.

| Purpose | Key fields (all standard) | API Name |
|---------|---------------------------|----------|
| Stores field-update suggestions (pending/applied/expired) | `ParentId` (= the Opportunity Id, filterable), `Subject` (= the field API name, e.g. `Risk__c`), `Type` (`FIELD_UPDATE`), `Status` (`WAITING`/`EXPIRED`), `SuggestedNewValue` (textarea), `AgentType` (`SALES_MANAGEMENT_AGENT`) | `AiGenActionItem` |

**SOQL Query** (filter by Opportunity via `ParentId`; `SuggestedNewValue` is not filterable):
```bash
sf data query -q "SELECT Id, ParentId, Subject, Type, Status, SuggestedNewValue FROM AiGenActionItem WHERE Type = 'FIELD_UPDATE' AND ParentId = '<oppId>' ORDER BY CreatedDate DESC LIMIT 10" --target-org $ORG --json 2>/dev/null
```

---

### 9. Apex Classes (if present)

Pipeline Management may deploy supporting Apex classes for:
- Custom grounding data retrieval
- Stage transition validation
- Suggestion filtering logic

**Check for Apex**:
```bash
sf data query -q "SELECT Id, Name FROM ApexClass WHERE Name LIKE '%SalesPipeMgmt%' OR Name LIKE '%DealAgent%'" --target-org $ORG --use-tooling-api --json 2>/dev/null
```

---

## Metadata Dependency Graph

```text
SalesDealAgentSettings (root)
├── EinsteinGptSettings (required)
│   └── EinsteinCopilotSettings (required)
├── EnhancedNotesSettings (recommended)
├── EmailAdministrationSettings (recommended)
├── OpportunitySettings (recommended)
├── BotDefinition: SalesAgent
│   ├── Agent User (salesmanagementagentuser@...)
│   │   └── PermissionSetGroup: SalesManagementAgentUserPsg
│   ├── Flows
│   │   ├── sales_pipe_mgmt__OppSuggGenSchFlow (template)
│   │   ├── Process_Field_Update_Suggestions (active)
│   │   ├── sales_pipe_mgmt__GetOppGroundingData
│   │   └── sales_pipe_mgmt__GetRcmdConvTscp
│   ├── GenAiPromptTemplates
│   │   ├── sales_pipe_mgmt__RecommendStageforOpp
│   │   └── sales_pipe_mgmt__RecommendNextStepforOpp
│   ├── Setup Entities (Tooling API)
│   │   └── OpptStageDescription (OpportunityStageApiName, Description) ← global-per-stage, no RT column
│   └── Standard Objects
│       └── AiGenActionItem (field-update suggestions)
└── PermissionSetGroup: SalesManagementUserPsg (assigned to end users)
```

---

## Metadata Retrieval Script

Complete script to retrieve all Pipeline Management metadata:

```bash
#!/bin/bash
ORG="pipeline-mgmt-org"

echo "Retrieving Pipeline Management metadata..."

# Settings
sf project retrieve start --metadata "Settings:SalesDealAgentSettings" --target-org $ORG 2>/dev/null
sf project retrieve start --metadata "Settings:EinsteinGptSettings" --target-org $ORG 2>/dev/null
sf project retrieve start --metadata "Settings:EinsteinCopilotSettings" --target-org $ORG 2>/dev/null
sf project retrieve start --metadata "Settings:EnhancedNotesSettings" --target-org $ORG 2>/dev/null
sf project retrieve start --metadata "Settings:EmailAdministrationSettings" --target-org $ORG 2>/dev/null
sf project retrieve start --metadata "Settings:OpportunitySettings" --target-org $ORG 2>/dev/null

# Permission Set Groups
sf project retrieve start --metadata "PermissionSetGroup:SalesManagementUserPsg" --target-org $ORG 2>/dev/null
sf project retrieve start --metadata "PermissionSetGroup:SalesManagementAgentUserPsg" --target-org $ORG 2>/dev/null

# Bot
sf project retrieve start --metadata "Bot:SalesAgent" --target-org $ORG 2>/dev/null

# Flows
sf project retrieve start --metadata "Flow:sales_pipe_mgmt__OppSuggGenSchFlow" --target-org $ORG 2>/dev/null
sf project retrieve start --metadata "Flow:Process_Field_Update_Suggestions" --target-org $ORG 2>/dev/null
sf project retrieve start --metadata "Flow:sales_pipe_mgmt__GetOppGroundingData" --target-org $ORG 2>/dev/null
sf project retrieve start --metadata "Flow:sales_pipe_mgmt__GetRcmdConvTscp" --target-org $ORG 2>/dev/null

# Prompt Templates
sf project retrieve start --metadata "GenAiPromptTemplate:sales_pipe_mgmt__RecommendStageforOpp" --target-org $ORG 2>/dev/null
sf project retrieve start --metadata "GenAiPromptTemplate:sales_pipe_mgmt__RecommendNextStepforOpp" --target-org $ORG 2>/dev/null

# Setup entities / standard objects need no metadata retrieve:
#   OpptStageDescription is a Tooling setup entity (query with --use-tooling-api)
#   AiGenActionItem is a standard object

echo "Retrieval complete. Check force-app/main/default/ for metadata."
```

---

## Metadata Inspection Queries

### Check All Pipeline Management Components

```bash
# Settings
sf data query -q "SELECT enableDealAgent, enableDealAgentAutoApproveAllTasks FROM SalesDealAgentSettings" --target-org $ORG --json 2>/dev/null

# Agent (BotDefinition has no Status column; query Id/DeveloperName only)
sf data query -q "SELECT Id, DeveloperName FROM BotDefinition WHERE DeveloperName = 'SalesAgent'" --target-org $ORG --json 2>/dev/null

# Agent User
sf data query -q "SELECT Id, Username FROM User WHERE Username LIKE '%salesmanagementagentuser%'" --target-org $ORG --json 2>/dev/null

# Flows (FlowDefinition is unsupported on the data API — query FlowDefinitionView; use IsActive, not Status)
sf data query -q "SELECT ApiName, IsActive, IsTemplate FROM FlowDefinitionView WHERE ApiName LIKE '%sales_pipe_mgmt%'" --target-org $ORG --json 2>/dev/null

# Prompt Templates (GenAiPromptTemplate is NOT SOQL-queryable — use the REST endpoint)
sf api request rest "/services/data/v64.0/einstein/prompt-templates" --target-org $ORG 2>/dev/null | jq -r '.promptRecords[]?.fields.DeveloperName.value'

# Stage Descriptions (Tooling setup entity — requires --use-tooling-api)
sf data query -q "SELECT COUNT() FROM OpptStageDescription" --target-org $ORG --use-tooling-api --json 2>/dev/null

# Recent Suggestions
sf data query -q "SELECT COUNT() FROM AiGenActionItem WHERE Type = 'FIELD_UPDATE' AND CreatedDate = TODAY" --target-org $ORG --json 2>/dev/null
```

---

## Notes

- Not all components are retrievable via Metadata API (e.g., agent user must be queried via SOQL)
- Component availability varies by org edition and license
- Template flows (`isTemplate=true`) should not be activated directly — always clone first
- SOAP API required for `SalesDealAgentSettings` only (CLI returns 'Settings type is unknown'). `EinsteinGptSettings` and `EinsteinCopilotSettings` work with both CLI and SOAP.
- `BotDefinition` and `BotVersion` use **standard SOQL** — NOT `--use-tooling-api` (Tooling API returns "sObject type not supported"). `BotDefinition` has no `Label` or `Status` column; `BotVersion` exposes `Status`. `GenAiPromptTemplate` is not queryable via SOQL (Tooling or standard) — inspect it via the Metadata API / retrieve.
- All `sf ... --json` commands piped to jq should include `2>/dev/null` for clean parsing
