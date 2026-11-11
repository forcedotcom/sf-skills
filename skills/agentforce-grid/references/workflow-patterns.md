# Workflow Patterns and User Interaction Models

Detailed specifications for how users interact with Agentforce Grid through Claude Code. The interaction model treats grids as manipulable blocks — users describe intent in natural language, and the skill translates that into orchestrated API calls.

---

## 1. Natural Language Grid Building

### Design Principle

Users should never think in JSON or API calls. They describe what they want as if talking to a colleague: "Build me a grid that does X." The skill decomposes the request into a plan, confirms it, and executes step-by-step.

### Conversation Flow: The Three-Phase Pattern

Every grid-building interaction follows three phases:

**Phase 1: Understand and Plan**
Parse the user's intent. Identify the column pipeline. Surface any ambiguities.

**Phase 2: Confirm and Resolve**
Present the plan as a visual table. Ask for missing information (agent IDs, model preferences, filter criteria). Let the user adjust before any API call.

**Phase 3: Execute and Report**
Create resources sequentially (workbook, worksheet, columns, data, trigger). Report progress. Show the final grid structure.

### Example A: Agent Testing Grid

```
USER: Create a grid that tests my Sales Agent with 50 utterances and
      evaluates coherence + topic routing

SKILL THINKING:
  - Need: AgentTest pipeline with evaluations
  - Missing: agent ID, agent version, utterance source, expected topics
  - Column pipeline: Text (utterances) -> Text (expected topics) ->
    AgentTest (run agent) -> Evaluation (COHERENCE) -> Evaluation (TOPIC_ASSERTION)

SKILL RESPONSE:
  I'll build a Sales Agent testing grid with this structure:

  | #  | Column            | Type       | Purpose                    |
  |----|-------------------|------------|----------------------------|
  | 1  | Test Utterances   | Text       | Your 50 test inputs        |
  | 2  | Expected Topics   | Text       | Ground truth topic names   |
  | 3  | Agent Output      | AgentTest  | Run your Sales Agent       |
  | 4  | Coherence         | Evaluation | Assess logical flow (auto) |
  | 5  | Topic Routing     | Evaluation | Verify correct topic (auto)|

  Before I create this, I need:
  1. Your agent ID and version — run `sf agent list` or I can call
     get_agents to find it. Which agent name should I look for?
  2. Do you already have utterances, or should I create empty rows
     for you to fill?
  3. Any context variables your agent requires?

USER: The agent is called "Sales Assistant". I have utterances in a CSV
      at /tmp/sales-tests.csv. No context variables needed.

SKILL EXECUTES:
  1. get_agents() → find "Sales Assistant" → extract agentId + versionId
  2. create_workbook_with_worksheet({workbookName: "Sales Agent Test Suite", worksheetName: "Sales Assistant Tests"})
  3. import_csv or create Text columns + paste_data from CSV
  4. add_column → Text column "Expected Topics"
  5. add_column → AgentTest column referencing utterances
  6. add_column → Evaluation COHERENCE on agent output
  7. add_column → Evaluation TOPIC_ASSERTION on agent output, referencing expected topics
  8. trigger_row_execution → process all rows

SKILL RESPONSE:
  Grid created and processing:

  Workbook: "Sales Agent Test Suite" (1W4xx...)
  Worksheet: "Sales Assistant Tests" (1W1xx...)

  | Column           | ID        | Status      |
  |------------------|-----------|-------------|
  | Test Utterances  | 1W5xx...  | Complete    |
  | Expected Topics  | 1W5xx...  | New (empty) |
  | Agent Output     | 1W5xx...  | InProgress  |
  | Coherence        | 1W5xx...  | New         |
  | Topic Routing    | 1W5xx...  | New         |

  50 rows loaded from CSV. Agent processing started — evaluations
  will auto-run as agent responses complete.

  Next steps:
  - Fill in "Expected Topics" column with your ground truth
  - Use `/grid-status` to check progress
  - Once complete, use `/grid-results` to see evaluation scores
```

### Example B: Data Enrichment Pipeline

```
USER: Build an enrichment pipeline: query tech accounts, generate
      summaries, classify sentiment

SKILL THINKING:
  - Need: Object (accounts) -> AI (summaries) -> AI (sentiment classification)
  - Missing: specific fields to query, filter details, model preference
  - The sentiment column should use SINGLE_SELECT

SKILL RESPONSE:
  Here's the enrichment pipeline I'll build:

  | #  | Column          | Type   | Purpose                           |
  |----|-----------------|--------|-----------------------------------|
  | 1  | Tech Accounts   | Object | Query Account where Industry = Technology |
  | 2  | Summary         | AI     | Generate company summary from Name, Industry, Description |
  | 3  | Sentiment       | AI     | Classify as Positive/Negative/Neutral |

  A few questions:
  1. Which Account fields matter most? I'd default to Name, Industry,
     Description, AnnualRevenue, Website. Add or remove any?
  2. For the summary — how long? (1 sentence, 2-3 sentences, paragraph)
  3. What model? Default is GPT 4 Omni. Options include Claude Sonnet 4.5,
     Gemini 2.5 Pro, GPT 5, etc.
  4. How many accounts max? (Default: 50)

USER: Default fields are fine. 2-3 sentences. Use Claude Sonnet 4.5. 100 accounts.

SKILL EXECUTES:
  1. create_workbook_with_worksheet({workbookName: "Account Enrichment", worksheetName: "Tech Account Enrichment"})
  2. add_column → Object column (Account, Industry In ["Technology"],
     fields: Id, Name, Industry, Description, AnnualRevenue, Website,
     numberOfRows: 100, WHOLE_COLUMN)
  3. Wait for Object column to populate (or proceed — autoUpdate handles it)
  4. add_column → AI column "Summary" (EACH_ROW, instruction referencing
     {$1}..{$5}, model: sfdc_ai__DefaultBedrockAnthropicClaude45Sonnet,
     PLAIN_TEXT)
  5. add_column → AI column "Sentiment" (EACH_ROW, instruction:
     "Classify sentiment of: {$1}", referencing Summary column,
     SINGLE_SELECT with Positive/Negative/Neutral)
```

### Example C: A/B Model Comparison

```
USER: Set up A/B testing: compare GPT-4o vs Claude on customer email generation

SKILL THINKING:
  - Need: Same input → two AI columns with different models → evaluations on both
  - This is a side-by-side comparison pattern
  - Need a source of customer data or test inputs

SKILL RESPONSE:
  I'll build a side-by-side model comparison grid:

  | #  | Column              | Type       | Purpose                     |
  |----|---------------------|------------|-----------------------------|
  | 1  | Customer Name       | Text       | Input data                  |
  | 2  | Customer Issue      | Text       | Input data                  |
  | 3  | Email (GPT-4o)      | AI         | GPT 4 Omni generation       |
  | 4  | Email (Claude)      | AI         | Claude Sonnet 4.5 generation|
  | 5  | Coherence (GPT-4o)  | Evaluation | Quality score for GPT       |
  | 6  | Coherence (Claude)  | Evaluation | Quality score for Claude    |
  | 7  | Conciseness (GPT-4o)| Evaluation | Brevity score for GPT       |
  | 8  | Conciseness (Claude)| Evaluation | Brevity score for Claude    |

  Both AI columns use the same prompt but different models.
  Where should the customer data come from?
  a) I'll create empty rows — you paste data in
  b) Query from Salesforce Cases/Contacts
  c) You have a CSV

USER: Query from open Cases — use Subject and Description

SKILL EXECUTES:
  1. create_workbook_with_worksheet({workbookName: "Model Comparison", worksheetName: "GPT vs Claude"})
  2. add_column → Object column: Case, filters: [Status In ["New","Open"]],
     fields: [Subject, Description, ContactId], WHOLE_COLUMN
  3. add_column → AI column "Email (GPT-4o)": model sfdc_ai__DefaultGPT4Omni,
     instruction referencing Case.Subject {$1} and Case.Description {$2}
  4. add_column → AI column "Email (Claude)": model
     sfdc_ai__DefaultBedrockAnthropicClaude45Sonnet, SAME instruction
     referencing same columns
  5. add_column → Evaluation COHERENCE on "Email (GPT-4o)"
  6. add_column → Evaluation COHERENCE on "Email (Claude)"
  7. add_column → Evaluation CONCISENESS on "Email (GPT-4o)"
  8. add_column → Evaluation CONCISENESS on "Email (Claude)"
  9. poll_worksheet_status to monitor execution
```

### Translation Rules: Natural Language to API Calls

| User Says | Skill Understands | API Pattern |
|-----------|-------------------|-------------|
| "test my agent" | AgentTest pipeline | Text + AgentTest + Evaluation columns |
| "query accounts/contacts/leads" | Object column | Object with WHOLE_COLUMN |
| "generate/write/draft" | AI column | AI with mode: "llm", PLAIN_TEXT |
| "classify/categorize" | AI column with SINGLE_SELECT | AI with SINGLE_SELECT response |
| "evaluate/score/check quality" | Evaluation columns | Evaluation with appropriate type |
| "compare X vs Y" | Side-by-side AI columns | Same prompt, different modelConfig |
| "enrich" | Object + AI pipeline | Object (WHOLE_COLUMN) then AI (EACH_ROW) |
| "run this flow/apex" | InvocableAction column | InvocableAction + Reference extraction |
| "extract the topic/action/field" | Reference column | Reference with JSON path |
| "compute/calculate" | Formula column | Formula with expression |

---

## 2. Iterative Grid Refinement

### Design Principle

Grids are living documents. Users should be able to modify them conversationally, the same way you'd say "add a column" or "change that filter" to a colleague sitting next to you.

### Pre-Requisite: Grid Context

Before any modification, the skill must establish context. If the user says "add a column to my grid," the skill needs the worksheet ID. The conversation flow:

```
SKILL: Which grid are you working with? I can:
  a) List your workbooks — get_workbooks
  b) Use a specific worksheet ID if you have one
  c) Use the grid we just created (if in same session)
```

Once context is established (worksheet ID known), store it for the session.

### Workflow 2A: Adding Columns to Existing Grids

```
USER: Add a conciseness evaluation to the agent test grid we just built

SKILL THINKING:
  - Have worksheet ID from session context
  - Need to: get worksheet data to find the agent output column ID
  - Then add Evaluation column with CONCISENESS type

SKILL EXECUTES:
  1. get_worksheet_data({worksheetId: "..."}) → find "Agent Output" column, get its ID
  2. add_column → Evaluation column:
     {evaluationType: "CONCISENESS", inputColumnReference: {agent output col}}
  3. Column auto-processes existing rows

SKILL RESPONSE:
  Added "Conciseness" evaluation column (1W5xx...) targeting "Agent Output".
  Auto-evaluating existing 50 rows now.
```

### Workflow 2B: Changing Evaluation Criteria

```
USER: Change the coherence evaluation to use custom LLM evaluation instead.
      I want it to check if the response follows our brand voice guidelines.

SKILL THINKING:
  - Need to update existing evaluation column
  - Switch from COHERENCE to CUSTOM_LLM_EVALUATION
  - Need a prompt template for brand voice, or create an inline evaluation
  - CUSTOM_LLM_EVALUATION requires a referenceColumnReference

SKILL RESPONSE:
  To switch to a custom LLM evaluation for brand voice, I need:
  1. Do you have a prompt template for brand voice evaluation?
     (If not, I can help you create evaluation criteria in a Text column)
  2. What does "brand voice" mean specifically? (e.g., professional but
     warm, no jargon, always includes next steps)

USER: No template. Brand voice = professional, empathetic, always suggests
      a next action, never uses "unfortunately"

SKILL EXECUTES:
  1. add_column → Text column "Brand Voice Criteria" with static value
  2. edit_column({columnId: "{coherence-col-id}", config: "..."}) → update to
     CUSTOM_LLM_EVALUATION with referenceColumnReference pointing to criteria column
  3. edit_column triggers reprocessing automatically
```

### Workflow 2C: Adjusting Object Column Filters

```
USER: The accounts grid is only showing Technology companies. Add Finance
      and Healthcare too.

SKILL EXECUTES:
  1. get_worksheet_data({worksheetId: "..."}) → find Object column, read current config
  2. edit_column({columnId: "{object-col-id}", config: "..."}) → update filters:
     Industry In ["Technology", "Finance", "Healthcare"]
  3. edit_column triggers reprocessing automatically

SKILL RESPONSE:
  Updated the Accounts filter to include Technology, Finance, and
  Healthcare. Reprocessing — this will refresh the data with the
  expanded criteria. Downstream AI and Evaluation columns will
  automatically reprocess for new rows.
```

### Workflow 2D: Re-running with Different Models

```
USER: The Claude results look better. Switch the GPT column to use
      Claude too and rerun.

SKILL EXECUTES:
  1. get_worksheet_data({worksheetId: "..."}) → find "Email (GPT-4o)" column
  2. edit_column({columnId: "...", config: "..."}) → update modelConfig to
     sfdc_ai__DefaultBedrockAnthropicClaude45Sonnet, rename to "Email (Claude v2)"
  3. edit_column triggers reprocessing automatically

SKILL RESPONSE:
  Switched "Email (GPT-4o)" to Claude Sonnet 4.5 and renamed to
  "Email (Claude v2)". Reprocessing all 50 rows. Evaluation columns
  will auto-update once generation completes.
```

### Workflow 2E: Adding Rows to Existing Grids

```
USER: Add 20 more test cases to the agent grid

SKILL EXECUTES:
  1. add_rows({worksheetId: "...", numberOfRows: 20})
  2. Return row IDs

SKILL RESPONSE:
  Added 20 empty rows (total now 70). The new rows have empty
  utterances — fill them in and the AgentTest + Evaluation columns
  will auto-process.

  To paste data: provide your utterances and I'll use the paste endpoint.
  Or update cells individually.
```

---

## 3. Data Import/Export Workflows

### Workflow 3A: CSV Import

**Path 1: Direct CSV Import (API endpoint)**

```
USER: Import my test cases from /tmp/agent-tests.csv

SKILL THINKING:
  - The MCP server has import_csv tool
  - Needs documentId (the CSV must be uploaded to Salesforce as a
    ContentDocument first) and includeHeaders flag
  - Alternative: parse CSV locally, use paste_data tool

SKILL RESPONSE:
  Two options for importing your CSV:

  a) **API CSV Import** — Upload the CSV to Salesforce first (as a
     ContentDocument), then I call the import-csv endpoint. This
     creates Text columns automatically from CSV headers.

  b) **Paste Import** — I read the CSV locally, create Text columns
     matching headers, add rows, and paste data via the matrix endpoint.
     More control over column naming and no Salesforce upload needed.

  Which approach? (For Claude Code, option b is usually smoother)

USER: Option b

SKILL EXECUTES:
  1. Read CSV file locally → parse headers and rows
  2. add_column → Text columns matching each CSV header
  3. add_rows({worksheetId: "...", numberOfRows: 50})
  4. get_worksheet_data({worksheetId: "..."}) → get column IDs and row IDs
  5. paste_data({worksheetId: "...", startColumnId: "first-col",
     startRowId: "first-row", matrix: "[[{...}], ...]"})

SKILL RESPONSE:
  Imported 50 rows x 3 columns from agent-tests.csv:
  - "Utterance" (1W5xx...) — 50 values loaded
  - "Expected Response" (1W5xx...) — 50 values loaded
  - "Expected Topic" (1W5xx...) — 50 values loaded

  Ready to add processing columns. Want me to set up the agent test pipeline?
```

**Path 2: Paste from Description**

```
USER: Here are my test utterances:
  - "How do I reset my password?"
  - "What's my account balance?"
  - "I want to cancel my subscription"
  - "Transfer me to a human"
  - "What are your business hours?"

SKILL EXECUTES:
  1. Parse the 5 utterances from the message
  2. Ensure Text column exists (or add_column → create one)
  3. add_rows({worksheetId: "...", numberOfRows: 5})
  4. get_worksheet_data({worksheetId: "..."}) → get row IDs
  5. paste_data → single-column matrix

SKILL RESPONSE:
  Loaded 5 test utterances into the "Test Utterances" column.
  Rows 1-5 populated. Processing columns will auto-run.
```

### Workflow 3B: Export Results

```
USER: Export the evaluation results to CSV

SKILL THINKING:
  - get_worksheet_data → get all cell data
  - Format as CSV locally
  - No native export endpoint — must reconstruct from cell data

SKILL EXECUTES:
  1. get_worksheet_data → full worksheet data
  2. Parse columnData: map column IDs to names, row IDs to row numbers
  3. Build CSV: header row from column names, data rows from displayContent
  4. Write to local file

SKILL RESPONSE:
  Exported to /tmp/sales-agent-results.csv

  Summary:
  - 50 rows x 5 columns
  - Coherence scores: avg 4.2/5, min 2.8, max 5.0
  - Topic routing accuracy: 92% (46/50 correct)
  - 4 failed rows (agent timeout) — see rows 12, 23, 37, 41
```

### Workflow 3C: Generate Report from Evaluation Data

```
USER: Give me a summary report of the evaluation results

SKILL EXECUTES:
  1. get_worksheet_data → all cell data
  2. Parse evaluation columns → extract scores/pass-fail
  3. Compute aggregates locally

SKILL RESPONSE:
  ## Sales Agent Evaluation Report

  **Grid:** Sales Agent Test Suite > Sales Assistant Tests
  **Date:** 2026-03-06
  **Rows:** 50 test cases

  ### Evaluation Summary

  | Metric              | Result      | Details              |
  |---------------------|-------------|----------------------|
  | Coherence (avg)     | 4.2 / 5.0   | Range: 2.8 - 5.0    |
  | Topic Routing       | 92% pass    | 46/50 correct        |
  | Response Match      | 78% pass    | 39/50 matched        |
  | Latency             | 100% pass   | All under threshold  |

  ### Worst Performers (Bottom 5 by Coherence)
  | Row | Utterance                        | Score | Topic   |
  |-----|----------------------------------|-------|---------|
  | 12  | "complex multi-part question..." | 2.8   | Wrong   |
  | 23  | "edge case scenario..."          | 3.0   | Correct |
  | 37  | "ambiguous request..."           | 3.1   | Wrong   |
  | 8   | "slang/informal input..."        | 3.2   | Correct |
  | 41  | "very long utterance..."         | 3.3   | Wrong   |

  ### Recommendations
  - 3 of bottom 5 also had wrong topic routing — investigate topic
    classification for complex/ambiguous inputs
  - Row 12 (complex multi-part) suggests agent struggles with
    compound questions — consider adding topic for multi-intent
```

---

## 4. Monitoring and Observability Workflows

### Workflow 4A: Status Check — "How's my grid doing?"

```
USER: How's my grid doing?

SKILL EXECUTES:
  1. get_worksheet_data → check cell statuses
  2. Count by status per column: Complete, InProgress, Failed, New

SKILL RESPONSE:
  ## Grid Status: Sales Assistant Tests

  | Column           | Complete | InProgress | Failed | New  |
  |------------------|----------|------------|--------|------|
  | Test Utterances  | 50       | 0          | 0      | 0    |
  | Expected Topics  | 50       | 0          | 0      | 0    |
  | Agent Output     | 43       | 5          | 2      | 0    |
  | Coherence        | 43       | 0          | 0      | 7    |
  | Topic Routing    | 43       | 0          | 0      | 7    |

  Overall: 86% complete. 5 agent calls still running, 2 failed.
  Evaluations are pending on the 7 incomplete agent rows.

  Estimated completion: ~2 minutes (based on current processing rate).
```

### Workflow 4B: Debugging Failures — "Why did row 5 fail?"

```
USER: Why did row 12 fail?

SKILL EXECUTES:
  1. get_worksheet_data → find row 12 cells
  2. Check each column's cell for row 12
  3. Look at status and statusMessage for Failed cells
  4. Look at fullContent for error details

SKILL RESPONSE:
  Row 12 failure analysis:

  | Column          | Status   | Detail                              |
  |-----------------|----------|-------------------------------------|
  | Test Utterances | Complete | "I need to reset my password and    |
  |                 |          |  also check my balance and also..." |
  | Agent Output    | Failed   | Error: "Agent response timeout.     |
  |                 |          |  Execution exceeded 120s limit."    |
  | Coherence       | Skipped  | Skipped (no agent output)           |
  | Topic Routing   | Skipped  | Skipped (no agent output)           |

  **Root cause:** The utterance is very long and multi-part (148 words).
  The agent likely entered a complex reasoning loop and timed out.

  **Suggested fixes:**
  1. Simplify the utterance — split into separate test cases
  2. Reprocess just this row: reprocess_column({columnId: "{agent-col-id}"})
  3. If this is a real user scenario, the agent itself may need
     optimization for compound queries
```

### Workflow 4C: Analysis — "Show me the worst-performing test cases"

```
USER: Show me the worst-performing test cases

SKILL EXECUTES:
  1. get_worksheet_data → all evaluation cell data
  2. Parse evaluation scores from displayContent
  3. Sort by score ascending, take bottom N
  4. Cross-reference with input utterances

SKILL RESPONSE:
  ## Bottom 10 Test Cases by Evaluation Score

  | Row | Utterance (truncated)          | Coherence | Topic  | Match |
  |-----|--------------------------------|-----------|--------|-------|
  | 12  | "reset password and check b..."| Failed    | --     | --    |
  | 37  | "what if my payment was rej..."| 2.1       | FAIL   | FAIL  |
  | 23  | "can you do a thing for me"    | 2.8       | FAIL   | FAIL  |
  | 41  | "URGENT: need help NOW!!!"     | 3.0       | PASS   | FAIL  |
  | 8   | "yo whats my bal"              | 3.2       | PASS   | FAIL  |
  | 15  | "I was told by your agent t..."| 3.3       | FAIL   | PASS  |
  | 29  | ""                             | 3.4       | FAIL   | --    |
  | 33  | "repeat: transfer me"          | 3.5       | PASS   | FAIL  |
  | 44  | "hola necesito ayuda"          | 3.5       | FAIL   | FAIL  |
  | 19  | "what is the meaning of life"  | 3.6       | FAIL   | PASS  |

  **Patterns detected:**
  - Informal/slang inputs score lower (rows 8, 41)
  - Ambiguous inputs cause topic routing failures (rows 23, 19)
  - Non-English input not handled (row 44)
  - Empty input causes failure (row 29)
  - Complex multi-part questions timeout (row 12)
```

### Workflow 4D: Polling Pattern for Long-Running Grids

For grids with many rows or expensive operations (agent calls, LLM evaluations), the skill should implement polling:

```
SKILL (internal polling logic):

  Poll Strategy:
  1. After triggering execution, wait 10 seconds
  2. get_worksheet_data → count statuses
  3. If any InProgress: report progress, wait 15 seconds, poll again
  4. If all Complete/Failed: report final results
  5. Max poll attempts: 20 (5 minutes total)
  6. If still running after max: report current state, suggest user
     check back with /grid-status

  Progress Reporting (during long operations):
  "Processing: 23/50 complete (46%). 27 still running..."
  "Processing: 41/50 complete (82%). 7 still running, 2 failed..."
  "Complete: 48/50 succeeded, 2 failed. Generating report..."
```

**Important:** The API does not provide webhooks or push notifications. All monitoring is poll-based. Use `poll_worksheet_status` for automated polling with built-in intervals, or `get_worksheet_summary` for one-time status checks. Manual `get_worksheet_data` polling is also supported but requires managing frequency to avoid rate limits.

### Workflow 4E: Stale Detection and Auto-Reprocess

```
USER: I updated some utterances. Why aren't the evaluations updating?

SKILL EXECUTES:
  1. get_worksheet_data → check for Stale status cells
  2. Identify which columns need reprocessing

SKILL RESPONSE:
  Found 5 rows with stale cells — the agent output and evaluations
  haven't re-run since you changed the utterances.

  | Rows  | Stale Columns                          |
  |-------|----------------------------------------|
  | 3,7,12,28,45 | Agent Output, Coherence, Topic Routing |

  Want me to reprocess? This will re-run the agent and evaluations
  for these 5 rows.

USER: Yes

SKILL EXECUTES:
  1. trigger_row_execution
     → {"rowIds": ["row-3", "row-7", "row-12", "row-28", "row-45"]}
```

---

## 5. CI/CD Integration Patterns

### Design Principle

Grids become automated quality gates. An agent's evaluation scores must meet thresholds before deployment. The skill helps users set up grids that can be triggered programmatically and produce machine-readable results.

### Workflow 5A: Evaluation as a Deployment Gate

```
USER: I want to run grid evaluations as part of our deployment pipeline.
      How should I set that up?

SKILL RESPONSE:
  Here's the recommended CI/CD integration pattern:

  ## Architecture

  ```
  CI Pipeline
    |
    v
  1. sf deploy (agent metadata)
    |
    v
  2. Claude Code: /grid-run {worksheet-id}
    |
    v
  3. Poll for completion
    |
    v
  4. Claude Code: /grid-results {worksheet-id} --format json
    |
    v
  5. Assert: coherence_avg >= 4.0
     Assert: topic_accuracy >= 90%
     Assert: failed_rows == 0
    |
    v
  6. Pass → continue deploy / Fail → block + report
  ```

  ## Script Template (bash)

  ```bash
  #!/bin/bash
  # Run after agent deployment

  WORKSHEET_ID="1W1xx0000004xxxx"
  BASE_URL="/services/data/v66.0/public/grid"

  # Step 1: Reprocess the agent column to test with latest agent version
  AGENT_COL_ID="1W5xx0000004xxxx"
  sf api request "$BASE_URL/columns/$AGENT_COL_ID/reprocess" --method POST

  # Step 2: Poll until complete
  while true; do
    STATUS=$(sf api request "$BASE_URL/worksheets/$WORKSHEET_ID/data" \
      | jq '[.columnData[][].status] | group_by(.) | map({(.[0]): length}) | add')
    PENDING=$(echo $STATUS | jq '.InProgress // 0')
    if [ "$PENDING" -eq 0 ]; then break; fi
    sleep 15
  done

  # Step 3: Extract evaluation scores
  # (parse from worksheet data response)

  # Step 4: Assert thresholds
  ```

  Want me to create a reusable test grid for your agent that you can
  trigger from CI?
```

### Workflow 5B: Version Comparison

```
USER: I just deployed a new version of my Sales Agent. Compare it
      against the previous version's results.

SKILL THINKING:
  - Strategy: Create a new worksheet in same workbook
  - Copy the same utterances from the existing test sheet
  - Run against the new agent version
  - Compare scores side-by-side

SKILL EXECUTES:
  1. get_workbooks → find the agent test workbook
  2. get_worksheet_data({worksheetId: "{old-id}"}) → extract utterances + expected values
  3. create_worksheet → new worksheet "Sales Assistant v2.1 Tests"
  4. Create same column structure but with new agent version
  5. Paste same utterances
  6. Trigger execution
  7. When complete: compare results

SKILL RESPONSE:
  ## Version Comparison: Sales Assistant v2.0 vs v2.1

  | Metric              | v2.0        | v2.1        | Delta    |
  |---------------------|-------------|-------------|----------|
  | Coherence (avg)     | 4.2 / 5.0   | 4.5 / 5.0   | +0.3     |
  | Topic Routing       | 92% (46/50) | 96% (48/50) | +4%      |
  | Response Match      | 78% (39/50) | 82% (41/50) | +4%      |
  | Latency Pass Rate   | 100%        | 98% (49/50) | -2%      |
  | Failures            | 2           | 1           | -1       |

  **Regression detected:** Latency — row 37 now exceeds threshold
  (was 1.8s, now 2.3s). Investigate if new topic logic adds latency.

  **Improvements:** Topic routing fixed for rows 23, 37 (previously
  wrong, now correct). Coherence improved across the board.
```

### Workflow 5C: Regression Detection

The skill should flag any metric that degrades between versions:

```
SKILL (automated regression analysis):

  Regression Rules:
  1. Any evaluation average that drops > 0.2 points: WARNING
  2. Any evaluation average that drops > 0.5 points: FAILURE
  3. Any previously-passing row that now fails: FLAG
  4. New failures in previously-stable test cases: CRITICAL
  5. Latency increase > 20%: WARNING

  Output format (machine-readable for CI):
  {
    "status": "WARNING",
    "regressions": [
      {
        "metric": "latency_pass_rate",
        "previous": 1.0,
        "current": 0.98,
        "delta": -0.02,
        "severity": "WARNING",
        "affected_rows": [37]
      }
    ],
    "improvements": [
      {
        "metric": "coherence_avg",
        "previous": 4.2,
        "current": 4.5,
        "delta": 0.3
      }
    ]
  }
```

### Workflow 5D: Connection to Agent Refinery Loop

```
  The Grid-Refinery Feedback Loop:

  1. GRID (Evaluate)
     - Run test suite against current agent
     - Identify failure patterns

  2. REFINERY (Improve)
     - Use failure analysis to refine agent topics
     - Update instructions, actions, guardrails
     - Deploy new agent version

  3. GRID (Re-Evaluate)
     - Run same test suite against updated agent
     - Compare: did failures resolve?
     - Did anything regress?

  4. Repeat until quality gates pass

  The skill's role: automate steps 1 and 3, surface insights
  that inform step 2.
```

---

## 6. Multi-Grid Orchestration

### Workflow 6A: Related Worksheets in One Workbook

```
USER: I need a complete test suite: one sheet for happy path tests,
      one for edge cases, one for adversarial inputs.

SKILL EXECUTES:
  1. create_workbook({name: "Sales Agent Complete Test Suite"})
  2. create_worksheet → "Happy Path Tests" (workbookId: ...)
  3. create_worksheet → "Edge Case Tests" (workbookId: ...)
  4. create_worksheet → "Adversarial Tests" (workbookId: ...)
  5. For each: create identical column structure (Text utterances →
     AgentTest → Evaluations)
  6. Populate each with appropriate test cases

SKILL RESPONSE:
  Created test suite with 3 worksheets:

  **Workbook:** Sales Agent Complete Test Suite (1W4xx...)

  | Worksheet            | ID       | Rows | Purpose              |
  |----------------------|----------|------|----------------------|
  | Happy Path Tests     | 1W1xx... | 30   | Standard scenarios   |
  | Edge Case Tests      | 1W1xx... | 20   | Boundary conditions  |
  | Adversarial Tests    | 1W1xx... | 15   | Malicious/weird input|

  All 65 test cases queued for processing. Use `/grid-status` with
  any worksheet ID to check progress, or I can report on all three.
```

### Workflow 6B: Passing Data Between Grids

The API does not natively support cross-worksheet references. The skill bridges this gap:

```
USER: Use the accounts from my enrichment grid as context for
      agent testing in a different worksheet.

SKILL THINKING:
  - Can't reference across worksheets in the API
  - Strategy: extract data from worksheet A, paste into worksheet B
  - This is a manual data pipeline the skill orchestrates

SKILL EXECUTES:
  1. get_worksheet_data({worksheetId: "{enrichment-id}"}) → extract Account Names,
     Summaries from the enrichment grid
  2. In agent test worksheet: create Text column "Account Context"
  3. Paste the enrichment data into the agent test worksheet
  4. Configure Agent column to use "Account Context" as a
     context variable

SKILL RESPONSE:
  Copied 50 account summaries from "Account Enrichment" into
  "Agent Test" worksheet as context. The Agent column now receives
  each account summary as the AccountContext variable.
```

### Workflow 6C: Aggregate Results Across Worksheets

```
USER: Give me a combined report across all three test worksheets

SKILL EXECUTES:
  1. get_workbooks/{id} → list all worksheets
  2. For each worksheet: get_worksheet_data
  3. Parse evaluation results from each
  4. Aggregate

SKILL RESPONSE:
  ## Combined Test Suite Report

  | Worksheet         | Rows | Coherence | Topic  | Match  | Failures |
  |-------------------|------|-----------|--------|--------|----------|
  | Happy Path        | 30   | 4.6 avg   | 97%    | 90%    | 0        |
  | Edge Cases        | 20   | 3.8 avg   | 80%    | 65%    | 2        |
  | Adversarial       | 15   | 3.2 avg   | 60%    | 40%    | 5        |
  | **Overall**       | **65** | **4.0 avg** | **83%** | **70%** | **7** |

  The agent handles happy path well but struggles with adversarial
  inputs. Key weakness: topic routing under adversarial conditions
  (60% accuracy).
```

---

## 7. Slash Commands

### Command Reference

| Command | Description | Arguments |
|---------|-------------|-----------|
| `/grid-new` | Create new grid from description | `<description>` |
| `/grid-status` | Show current grid state | `[worksheet-id]` (optional if in session) |
| `/grid-run` | Execute/reprocess grid | `[worksheet-id] [--rows <ids>] [--column <id>]` |
| `/grid-results` | Show evaluation results | `[worksheet-id] [--format table\|json\|csv]` |
| `/grid-add` | Add column to existing grid | `<column-description>` |
| `/grid-debug` | Investigate failures | `[row-number] [--column <name>]` |
| `/grid-compare` | Compare two worksheets | `<worksheet-id-1> <worksheet-id-2>` |
| `/grid-export` | Export grid data | `[worksheet-id] [--format csv\|json] [--path <file>]` |
| `/grid-list` | List workbooks and worksheets | |
| `/grid-models` | List available LLM models | |

### `/grid-new` — Create New Grid from Description

```
Usage: /grid-new <natural language description>

Examples:
  /grid-new Test my Support Agent with 50 utterances, evaluate coherence and topic routing
  /grid-new Enrich tech accounts with AI summaries and sentiment classification
  /grid-new Compare GPT-4o vs Claude on email drafting for open Cases
  /grid-new Run my Create_Case flow with 20 test inputs and extract CaseId

Behavior:
  1. Parse the description into a column pipeline plan
  2. Present the plan as a table for confirmation
  3. Ask for any missing information (agent IDs, model preferences, etc.)
  4. On confirmation: create workbook, worksheet, columns, data
  5. Trigger processing
  6. Report grid structure with IDs
```

### `/grid-status` — Show Current Grid State

```
Usage: /grid-status [worksheet-id]

If worksheet-id omitted: uses the worksheet from current session context,
or lists workbooks and asks user to pick.

Output:
  - Per-column status breakdown (Complete/InProgress/Failed/New counts)
  - Overall completion percentage
  - Estimated time remaining (if InProgress rows exist)
  - List of failed rows (if any)

Examples:
  /grid-status
  /grid-status 1W1xx0000004xxxx
```

### `/grid-run` — Execute/Reprocess

```
Usage: /grid-run [options]

Options:
  --all                 Reprocess entire grid (all columns)
  --column <name-or-id> Reprocess specific column
  --rows <id1,id2,...>  Process specific rows only
  --failed              Reprocess only failed rows
  --stale               Reprocess only stale rows

Examples:
  /grid-run                          # Trigger all pending rows
  /grid-run --failed                 # Retry failures
  /grid-run --column "Agent Output"  # Reprocess agent column
  /grid-run --rows row1,row2,row3    # Process specific rows

API calls:
  --all / --column → reprocess_column
  --rows → trigger_row_execution {rowIds: [...]}
  --failed → GET data, find Failed rows, then trigger-row-execution
  --stale → GET data, find Stale rows, then trigger-row-execution
```

### `/grid-results` — Show Evaluation Results

```
Usage: /grid-results [worksheet-id] [options]

Options:
  --format table|json|csv   Output format (default: table)
  --sort <column> asc|desc  Sort by evaluation column
  --top <n>                 Show top N results
  --bottom <n>              Show bottom N results
  --failed-only             Show only failed evaluations
  --summary                 Show aggregate summary only

Examples:
  /grid-results                           # Full results table
  /grid-results --summary                 # Just averages and pass rates
  /grid-results --bottom 10               # Worst 10 performers
  /grid-results --format json             # Machine-readable output
  /grid-results --failed-only --sort coherence asc

API calls:
  1. get_worksheet_data
  2. Parse evaluation columns
  3. Format per options
```

### `/grid-add` — Add Column to Existing Grid

```
Usage: /grid-add <column description>

Examples:
  /grid-add evaluation for conciseness
  /grid-add AI column that classifies urgency as High/Medium/Low
  /grid-add Reference column extracting topicName from Agent Output
  /grid-add Formula: CONCATENATE first name and last name

Behavior:
  1. Identify target worksheet (from session or ask)
  2. Parse column description → determine type and config
  3. GET worksheet to find existing columns (for references)
  4. Confirm plan with user
  5. POST column
  6. Report result
```

### `/grid-debug` — Investigate Failures

```
Usage: /grid-debug [row-number] [--column <name>]

Examples:
  /grid-debug 12                       # Full row 12 analysis
  /grid-debug --column "Agent Output"  # All failures in that column
  /grid-debug                          # Summary of all failures

Behavior:
  1. get_worksheet_data
  2. Find relevant cells by row number or column
  3. Extract status, statusMessage, fullContent for failed cells
  4. Present diagnosis with suggested fixes
```

### `/grid-compare` — Compare Two Worksheets

```
Usage: /grid-compare <worksheet-id-1> <worksheet-id-2>

Examples:
  /grid-compare 1W1xx001 1W1xx002      # Compare v1 vs v2 results

Behavior:
  1. GET data from both worksheets
  2. Match rows by utterance text (or row order)
  3. Compare evaluation scores column by column
  4. Flag regressions and improvements
  5. Output comparison table + delta analysis
```

### `/grid-export` — Export Grid Data

```
Usage: /grid-export [options]

Options:
  --format csv|json     Output format (default: csv)
  --path <file-path>    Write to file (default: /tmp/grid-export-{timestamp}.csv)
  --columns <names>     Export only specific columns

Examples:
  /grid-export --format csv --path /tmp/results.csv
  /grid-export --format json
  /grid-export --columns "Utterance,Agent Output,Coherence"
```

### `/grid-list` — List Workbooks and Worksheets

```
Usage: /grid-list

Behavior:
  1. get_workbooks
  2. For each workbook: show worksheets with basic info

Output:
  Workbooks:
  1. Sales Agent Test Suite (1W4xx...)
     - Sales Assistant Tests (1W1xx...) — 50 rows, 5 columns
     - Sales Assistant v2.1 Tests (1W1xx...) — 50 rows, 5 columns
  2. Account Enrichment (1W4xx...)
     - Tech Account Enrichment (1W1xx...) — 100 rows, 3 columns
```

### `/grid-models` — List Available Models

```
Usage: /grid-models

Behavior:
  1. get_llm_models
  2. Format as table with name, label, max tokens

Output:
  | Model ID                                    | Label              | Max Tokens |
  |---------------------------------------------|--------------------|------------|
  | sfdc_ai__DefaultGPT4Omni                    | GPT 4 Omni         | 16384      |
  | sfdc_ai__DefaultGPT5                        | GPT 5              | 128000     |
  | sfdc_ai__DefaultBedrockAnthropicClaude45Sonnet | Claude Sonnet 4.5 | 8192      |
  | sfdc_ai__DefaultVertexAIGemini25Flash001    | Gemini 2.5 Flash   | 65536      |
  | ...                                         |                    |            |
```

---

## 8. Conversation State Management

### Session Context

The skill should maintain context within a session to avoid repetitive questions:

```
Session State (maintained across turns):
  - active_workbook_id: "1W4xx..." (set after create or select)
  - active_worksheet_id: "1W1xx..." (set after create or select)
  - column_map: {name -> id} (refreshed after column operations)
  - row_ids: [...] (refreshed after row operations)
  - last_agent_id: "0Xxxx..." (reused for same-agent operations)
  - last_model: "sfdc_ai__DefaultGPT4Omni" (reused for defaults)
```

### Disambiguation Pattern

When context is ambiguous, ask — don't guess:

```
USER: Add an evaluation column

SKILL: Add an evaluation to which grid?
  1. Sales Assistant Tests (1W1xx...) — has Agent Output column
  2. Tech Account Enrichment (1W1xx...) — has AI Summary column

  And which evaluation type?
  - Quality: COHERENCE, CONCISENESS, FACTUALITY, COMPLETENESS,
    INSTRUCTION_FOLLOWING
  - Comparison: RESPONSE_MATCH, TOPIC_ASSERTION, ACTION_ASSERTION,
    BOT_RESPONSE_RATING
  - Performance: LATENCY_ASSERTION
  - Custom: EXPRESSION_EVAL, CUSTOM_LLM_EVALUATION
```

### Error Recovery Pattern

When API calls fail, the skill should diagnose and suggest fixes:

```
API Error: 400 BAD_REQUEST
  "config.config.mode is required for AI column type"

SKILL RESPONSE:
  The AI column creation failed — I missed a required field in the
  config. Fixing and retrying...

  [Retries with mode: "llm" added]

  Fixed. Column "Summary" created successfully.
```

```
API Error: 404 NOT_FOUND
  "Agent with ID 0Xxxx not found"

SKILL RESPONSE:
  That agent ID doesn't exist. Let me look up your available agents.
  [get_agents]

  Found these agents:
  1. Sales Assistant (0Xxxx001) — Active, v3
  2. Support Bot (0Xxxx002) — Active, v1
  3. Onboarding Agent (0Xxxx003) — Draft

  Which one should I use?
```
