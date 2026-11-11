---
name: agentforce-grid
description: "Use for Agentforce Grid (AI Workbench) — the spreadsheet-like interface for AI operations in Salesforce. ALWAYS use this skill when the user wants to: test or evaluate an Agentforce agent with utterances; create workbooks, worksheets, or columns; enrich Salesforce records with AI-generated content; add AI columns (SINGLE_SELECT, PLAIN_TEXT), Formula columns, Object columns, Evaluation columns, or Reference columns; import CSV data; compare agent versions; debug column config errors; query SObjects or Data Cloud in a grid; run evaluations (coherence, topic assertion, response match); or use any mcp__grid-connect__ tools. Covers the Grid Connect API for all column CRUD, cell operations, agent testing pipelines, and batch processing. Skip for standalone Apex, Flows, dashboards, reports, validation rules, or Einstein Bots that don't involve Grid."
---

# Agentforce Grid Skill

Agentforce Grid (AI Workbench) is a spreadsheet-like interface for AI operations in Salesforce. Worksheets contain typed columns that query data, run agents, generate AI content, and evaluate outputs.

**Hierarchy:** Workbook > Worksheet > Columns > Rows > Cells

> **Note:** The MCP tool surface is being consolidated from ~65 tools to ~15. Tool names below reflect the current state. If a tool is not found, check `get_supported_types` or `get_column_types` for alternatives.

## Before You Act (Mandatory Checklist)

Run this checklist before creating or suggesting any column:

1. **Read current grid state** -- call `get_worksheet_data` to see all existing columns, their IDs, and cell data
2. **Check for duplicates** -- does a column with the same name or purpose already exist? If so, suggest editing it (`edit_ai_prompt`, `edit_column`) instead of creating a new one
3. **Verify all referenced column IDs exist** -- every `columnId` in `referenceAttributes`, `inputColumnReference`, or `referenceColumnReference` MUST come from the current grid state. NEVER hallucinate column IDs or reference columns that do not exist yet
4. **Confirm column type matches the task** -- use the decision table below
5. **Confirm response format matches the use case** -- SINGLE_SELECT for filtering/sorting, PLAIN_TEXT for free-form content
6. **Check dependency order** -- source columns must exist before processing columns that reference them
7. **Check available resources** -- call `get_prompt_templates` or `get_invocable_actions` before creating an AI column that could be handled by existing platform capabilities

## Column Types

| Type | `type` value | Use Case |
|------|-------------|----------|
| AI | `"AI"` | LLM text generation with custom prompts |
| Agent | `"Agent"` | Run agent conversations |
| AgentTest | `"AgentTest"` | Batch-test agent with utterances |
| Evaluation | `"Evaluation"` | Evaluate agent/prompt outputs (13 types) |
| Formula | `"Formula"` | Deterministic computed values |
| Object | `"Object"` | Query Salesforce SObjects |
| DataModelObject | `"DataModelObject"` | Query Data Cloud DMOs |
| PromptTemplate | `"PromptTemplate"` | Execute GenAI prompt templates |
| InvocableAction | `"InvocableAction"` | Execute Flows or Apex |
| Action | `"Action"` | Execute platform actions |
| Reference | `"Reference"` | Extract fields via JSON path |
| Text | `"Text"` | Static/editable text or CSV import |

**Casing:** Server is case-insensitive. PascalCase and UPPER_CASE both work. API returns vary by context.

For complete JSON configs: [Column Configs Reference](references/column-configs.md)

## Choosing the Right Column Type

| Need | Type | Format | Why |
|------|------|--------|-----|
| Categorize/filter/sort | AI | SINGLE_SELECT | Limited options enable filtering and scanning |
| Generate free-text (email, summary) | AI | PLAIN_TEXT | Open-ended content needs free-form output |
| Deterministic computation | Formula | N/A | No LLM needed, exact and reproducible |
| Extract field from JSON/Object | Reference | N/A | Zero LLM cost, exact extraction |
| Score/rate on a scale | AI | SINGLE_SELECT | e.g., High/Medium/Low for scannable output |
| Task already handled by a prompt template | PromptTemplate | N/A | Pre-built, tested, maintained by the org |
| Task already handled by a Flow | InvocableAction | N/A | Deterministic logic, no LLM cost |

**Key principle:** If output is used for filtering, sorting, or downstream comparison, use SINGLE_SELECT. Free-text defeats scanability. If a platform capability (prompt template, Flow, list view) already does the job, prefer it over AI.

## Role-Aware Suggestions

Before suggesting columns, understand the user's role and intent. Ask if unclear.

| Role | Common Needs | Pipeline Pattern |
|------|-------------|------------------|
| Sales Rep | Deal risk, competitive intel, account priority | Object(Opps) -> AI(risk, SINGLE_SELECT) |
| CSM | Customer health, check-in emails | Object(Accounts/Cases) -> AI(analysis) -> AI(email, PLAIN_TEXT) |
| RevOps | Pipeline quality, data hygiene flags | Object(Opps) -> AI(quality flag, SINGLE_SELECT: Clean/Minor Issues/Needs Fix) |
| Dev/QA | Agent testing, flow testing | Text(utterances) -> AgentTest -> Evaluation |
| Admin | Data enrichment, bulk updates | Object/ListView -> AI -> Action(RecordUpdate) |

A RevOps user needs data quality flags (SINGLE_SELECT), not outreach emails. A CSM needs customer-facing outputs, not pipeline metrics.

## Evaluation Types

| Type | Needs Reference Column | Supported Inputs |
|------|----------------------|------------------|
| COHERENCE | No | Agent, AgentTest, PromptTemplate |
| CONCISENESS | No | Agent, AgentTest, PromptTemplate |
| FACTUALITY | No | Agent, AgentTest, PromptTemplate |
| INSTRUCTION_FOLLOWING | No | Agent, AgentTest, PromptTemplate |
| COMPLETENESS | No | Agent, AgentTest, PromptTemplate |
| RESPONSE_MATCH | **Yes** | Agent, AgentTest |
| TOPIC_ASSERTION | **Yes** | Agent, AgentTest |
| ACTION_ASSERTION | **Yes** | Agent, AgentTest |
| LATENCY_ASSERTION | No | Agent, AgentTest |
| BOT_RESPONSE_RATING | **Yes** | Agent, AgentTest |
| EXPRESSION_EVAL | No | Agent, AgentTest |
| CUSTOM_LLM_EVALUATION | **Yes** | Agent, AgentTest |
| TASK_RESOLUTION | No | Agent, AgentTest (conversation-level) |

For complete evaluation guidance: [Evaluation Types Reference](references/evaluation-types.md)

## Dependency Rules

Column creation must follow the dependency DAG. A column CANNOT reference a column that does not yet exist or that depends on it.

1. **Source data** (Text, Object, DataModelObject) -- no dependencies
2. **Processing** (AI, Agent, AgentTest, PromptTemplate, InvocableAction) -- depend on source
3. **Extraction** (Reference) -- depends on processing columns
4. **Assessment** (Evaluation) -- depends on Agent/AgentTest/PromptTemplate
5. **Formula** -- any level, but must only reference existing columns

**Always create columns sequentially.** Each `add_column` returns the new column ID needed by subsequent columns. Parallel creation leads to missing IDs and unpredictable ordering.

## Leverage Existing Resources

Before creating an AI column, check if platform capabilities handle the task:

1. `get_prompt_templates` -- use PromptTemplate column for pre-built prompts
2. `get_invocable_actions` -- use InvocableAction column for deterministic logic
3. `get_list_views` -- use list view SOQL in Object column's advancedMode
4. Existing columns -- use Reference column to extract data already present

AI columns should be reserved for tasks requiring LLM reasoning.

## Critical Config Rules

**Nested config structure (REQUIRED for ALL column types):**
```json
{
  "name": "Column Name",
  "type": "AI",
  "config": {
    "type": "AI",
    "queryResponseFormat": {"type": "EACH_ROW"},
    "autoUpdate": true,
    "config": {
      "autoUpdate": true
    }
  }
}
```

Even Text columns need `type` inside config. An empty `config: {}` will fail.

**queryResponseFormat:** Use `EACH_ROW` when adding a column to a worksheet that already has data. Use `WHOLE_COLUMN` with `splitByType: "OBJECT_PER_ROW"` only when importing new records (Object/DataModelObject).

**modelConfig:** Use the model `name` for both `modelId` and `modelName`. Call `get_llm_models` to list available models. Default: `sfdc_ai__DefaultGPT4Omni`.

**AI columns:** Require `mode: "llm"`, `responseFormat` with `options` array (empty `[]` for PLAIN_TEXT).

**Evaluation columns:** Types requiring reference columns (RESPONSE_MATCH, TOPIC_ASSERTION, ACTION_ASSERTION, BOT_RESPONSE_RATING, CUSTOM_LLM_EVALUATION) must include `referenceColumnReference`.

For complete JSON configs for all 12 types: [Column Configs Reference](references/column-configs.md)

## Common Patterns

### Agent Testing Pipeline
```
Text(utterances) -> Text(expected) -> AgentTest -> Evaluation(RESPONSE_MATCH) -> Evaluation(COHERENCE)
```
**Quick path:** Use `setup_agent_test` for one-call creation of the full pipeline.

### Data Enrichment
```
Object(Accounts) -> AI(summary, PLAIN_TEXT) -> AI(sentiment, SINGLE_SELECT)
```

### Flow/Apex Testing
```
Text(inputs) -> InvocableAction(Flow) -> Reference(extract output field)
```

For complete step-by-step MCP tool call examples: [Use Case Patterns Reference](references/use-case-patterns.md)

## SF CLI Setup & Authentication

Before using the Grid API, authenticate to a Salesforce org using the SF CLI.

```bash
sf --version                    # Check if installed
sf org login web --alias my-org # Authenticate (add --instance-url for specific org)
sf org display --target-org my-org --json  # Get access token + instance URL
```

**Instance URL formats:** `https://sdbX.testX.pc-rnd.pc-aws.salesforce.com/` (internal), `https://mycompany.my.salesforce.com` (production), `https://mycompany--sandbox.sandbox.my.salesforce.com` (sandbox).

**SF CLI does NOT accept lightning domains.** If a user provides one (e.g., `orgfarm-xxx.test1.lightning.pc-rnd.force.com`), ask for the instance URL instead.

For full auth instructions: `sf org login web --help`

## MCP Tool Reference

All tools use prefix `mcp__grid-connect__`. Grouped by operation type.

### Orchestration (Start Here)

| Tool | What It Does |
|------|-------------|
| `apply_grid` | Create/update a full grid from YAML DSL -- most powerful orchestration tool |
| `setup_agent_test` | One-call agent test pipeline: workbook + worksheet + columns + evaluations |
| `create_workbook_with_worksheet` | Create workbook + worksheet in one call |
| `poll_worksheet_status` | Poll until processing completes |
| `get_worksheet_summary` | Compact status overview |
| `run_worksheet` | Execute worksheet with optional `runStrategy: "ColumnByColumn"` for sequential |

### Read State

| Tool | What It Does |
|------|-------------|
| `get_workbooks` | List all workbooks |
| `get_workbook` | Get workbook details |
| `get_worksheet` | Get worksheet metadata |
| `get_worksheet_data` | **Primary read tool** -- full data with all columns, rows, cells |
| `get_worksheet_data_generic` | Generic format variant |
| `get_column_data` | Get cell data for one column |

### Create & Modify

| Tool | What It Does |
|------|-------------|
| `create_workbook` / `create_worksheet` | Create resources |
| `add_column` | Add column (returns new column ID) |
| `edit_column` | Update config AND reprocess all cells |
| `save_column` | Update config WITHOUT reprocessing |
| `reprocess_column` / `reprocess` | Reprocess cells (column or worksheet) |
| `delete_column` / `delete_workbook` / `delete_worksheet` | Delete resources |
| `add_rows` / `delete_rows` | Manage rows |
| `update_cells` | Update specific cells (use `fullContent`, not `displayContent`) |
| `paste_data` | Paste data matrix into grid |
| `trigger_row_execution` | Run processing for specific rows or cells |
| `import_csv` | Import CSV to worksheet |

### Typed Mutations (Prefer Over Raw edit_column)

These auto-fetch current config, merge changes, and handle references correctly.

| Tool | What It Does |
|------|-------------|
| `edit_ai_prompt` | Edit AI column prompt, model, or response format |
| `edit_agent_config` | Edit Agent/AgentTest config |
| `edit_prompt_template` | Edit PromptTemplate column |
| `change_model` | Switch LLM model on AI or PromptTemplate column |
| `add_evaluation` | Add evaluation with auto-wired references |
| `update_filters` | Update Object/DMO query filters |

### Discovery

| Tool | What It Does |
|------|-------------|
| `get_agents` | List agents (use `includeDrafts` for unpublished) |
| `get_agent_variables` | Get agent context variables |
| `get_sobjects` / `get_sobject_fields_display` / `get_sobject_fields_filter` | SObject discovery |
| `get_dataspaces` / `get_data_model_objects` / `get_data_model_object_fields` | Data Cloud discovery |
| `get_llm_models` | List available LLM models |
| `get_evaluation_types` | List evaluation types available in the org |
| `get_column_types` / `get_supported_types` | List column types |
| `get_formula_functions` / `get_formula_operators` | Formula building helpers |
| `get_invocable_actions` / `describe_invocable_action` | Discover Flows/Apex |
| `get_prompt_templates` / `get_prompt_template` | Discover prompt templates |
| `get_list_views` / `get_list_view_soql` | List view SOQL |

### AI Generation

| Tool | What It Does |
|------|-------------|
| `create_column_from_utterance` | Create column from natural language description |
| `generate_soql` | Natural language to SOQL |
| `generate_json_path` | AI-assisted JSON path generation |
| `generate_test_columns` | Generate test column configs |
| `generate_ia_input` | Generate invocable action input payload |
| `get_url` | Generate Lightning Experience URLs |

## Tool Operation Distinctions

| Tool | Behavior | When to Use |
|------|----------|-------------|
| `edit_column` | Updates config AND reprocesses | Changing prompt, model, references |
| `save_column` | Updates config, NO reprocess | Renaming, display-only changes |
| `reprocess_column` | Reprocesses with current config | Source data changed, retrying failures |

## State Refresh

Call `get_worksheet_data` after any mutation (add_column, paste_data, trigger_row_execution) to get updated IDs and statuses. Use `poll_worksheet_status` for long-running operations.

## Error Patterns

| Situation | What to Do |
|-----------|-----------|
| Column creation returns error but column exists | Verify with `get_worksheet_data` -- column may have been created despite the error |
| Cell processing failures | Use `reprocess_column` or `trigger_row_execution` with failed row IDs |
| Duplicate column name | API rejects with `DuplicateColumnName` -- check existing columns first |
| Config validation error | Fix config per error message and retry |

## Known Limits

- 100 test suites per org, 20 runs per suite, 10 concurrent runs per org
- AI column batches: 25 rows/batch, 4 parallel threads for evaluations

## Reference Documentation

- **[Column Configs](references/column-configs.md)** -- Complete JSON for all 12 column types
- **[Evaluation Types](references/evaluation-types.md)** -- All 13 evaluation types with guidance
- **[API Endpoints](references/api-endpoints.md)** -- Complete endpoint docs with examples
- **[Use Case Patterns](references/use-case-patterns.md)** -- Common workflows with MCP tool call examples
- **[Workflow Patterns](references/workflow-patterns.md)** -- User interaction models, conversation examples, CI/CD patterns
