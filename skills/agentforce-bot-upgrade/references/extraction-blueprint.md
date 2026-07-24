# Extraction Blueprint

## Goal

Extract only migration-relevant behavior from Einstein Bot and discard transport noise.

## Required Extractions

### 1) Dialog Graph

**Input files:**

Paths below are shown relative to the bots root directory. For org-backed retrieval this root is the SFDX default metadata directory `force-app/main/default/` (so the full path is `force-app/main/default/bots/<BotName>/…`, as retrieved in [SF CLI Bot Reference](sf-cli-bot-reference.md) section 3). For offline input this root is the provided `--offline-dir` (e.g. `bots/`).

- `bots/<BotName>/<BotName>.bot-meta.xml` (bot-level metadata)
- `bots/<BotName>/<version>.botVersion-meta.xml` (dialog + step graph source of truth)

**Build the graph with this process:**

1. Parse every `<botDialogs>` block in `<version>.botVersion-meta.xml` as one node.
2. For each node, capture:
   - `developerName` (node id)
   - `label`
   - `mlIntent` (if present)
   - `dialogGroup` / grouping metadata if present
3. Treat each `<botSteps>` entry inside a dialog as a step in execution order.
4. While scanning each step, also detect action invocations and variable mappings from bot steps:
   - invocation/action step types (for example `Invocation`)
   - action identifier/name and invocation type (`apex`, `flow`, `standardInvocableAction`, etc.)
   - variables read by the action (bot variables passed as invocation inputs)
   - variables updated by the action (bot variables set from invocation outputs)
   - escalation actions from system messages:
     - if a dialog contains `conversationSystemMessage` of type `Transfer`, add an action entry with `action_type: "escalate"`
     - determine escalation target type (`queue`, `flow`, `bot`, or `skill`) by reading `systemMessageMappings` under that `conversationSystemMessage` and resolving referenced variables against declarations in `<conversationVariables>`
     - store both the resolved `target_type` and mapped target identifier/value on the action record
   - persist this as `invoked_actions` on the dialog node and as action-level records in `action_inventory`
5. While scanning each step, detect transition-producing step types:
   - `Navigation` with `<botNavigationLinks>`
   - `Group` containing nested `Navigation`
   - `Wait` type steps, which define intent-driven routing points (intent redirect behavior)
6. For every discovered transition, add one directed edge:
   - `source_dialog` -> `targetBotDialog`
   - `type` (`redirect`, `call`, `intent_redirect`)
7. Capture conditions from enclosing step/group when present:
   - `leftOperandName`
   - `operatorType`
   - `rightOperandValue`
   - store as a normalized condition expression on the edge
8. Mark graph role hints:
   - probable entry dialogs (for example `Welcome`, `Main_Menu`, or system entry mapping)
   - terminal dialogs (for example paths ending in `SystemMessage` + `EndChat`, with no outbound navigation)

**Required output for dialog graph extraction:**

```json
{
  "nodes": [
    {
      "dialog": "Main_Menu",
      "label": "Main Menu",
      "intent": "Main_Menu",
      "invoked_actions": [
        {
          "action_name": "Airline_Get_User_Details",
          "action_type": "flow",
          "variables_read": ["user_email"],
          "variables_written": ["airline_user", "is_success"]
        }
      ]
    }
  ],
  "edges": [
    {
      "source": "Main_Menu",
      "target": "Bookings_Menu",
      "type": "redirect",
      "condition": null
    }
  ]
}
```

**Quality checks:**

- Every `targetBotDialog` in edges must resolve to an existing dialog node.
- Keep `Call` and `Redirect` distinct (do not merge semantics).
- Preserve multiple outgoing edges from the same step when configured.

### 2) Intent Layer

- Intent name/developer name
- Intent description
- Linked dialogs
- Intent examples/utterances (if available)

**Intent summarization workflow:**

1. For each dialog node in the dialog graph, read its `mlIntent` value (if present).
2. Treat that `mlIntent` as the lookup key for intent metadata in `MlDomain` with the same name.
3. From the matched intent metadata, extract:
   - `developerName`
   - `label` / `description` (if present)
   - `mlIntentUtterances` (training utterances)
4. Generate a concise intent summary (2-3 sentences) per unique intent:
   - sentence 1: user goal the intent represents
   - sentence 2: typical phrasing style inferred from `mlIntentUtterances`
   - sentence 3 (optional): routing nuance or disambiguation hint if overlapping with other intents
5. If an `mlIntent` is referenced by a dialog but no matching `MlDomain` intent is found:
   - flag the intent as unresolved
   - add it to `open_questions`
   - still generate a provisional summary from dialog label/description with `confidence: low`

### 3) Variable and Entity Layer

**Input files:**

- `bots/<BotName>/<BotName>.bot-meta.xml` (context variables, slot/entity metadata)
- `bots/<BotName>/<version>.botVersion-meta.xml` (conversation variable usage through steps)

**Variable extraction and typing rules:**

1. Extract context variables from `bot-meta.xml` (`<contextVariables>` entries).
2. Mark every context variable as:
   - `variable_type: linked`
   - `data_type`: map from bot metadata `dataType`
   - `source`: derive from context mappings (`SObjectType` + `fieldName`) when present
3. Extract conversation variables directly from `botVersion-meta.xml` `<conversationVariables>` entries (authoritative source for declared conversation variables).
4. Mark every conversation variable as:
   - `variable_type: mutable`
   - `data_type`: read directly from the variable's declared data type in `<conversationVariables>`

**Required output shape (variables):**

```json
{
  "variables": [
    {
      "name": "ContactId",
      "data_type": "Id",
      "variable_type": "linked",
      "source": "MessagingEndUser.ContactId"
    },
    {
      "name": "Complaint_Id",
      "data_type": "Text",
      "variable_type": "mutable"
    }
  ]
}
```

### 4) Action/Invocation Layer

- Action name and invocation type (`apex`, `flow`, etc.)
- Inputs, outputs, and variable mappings
- Also extract knowledge-backed action signals from `botVersion-meta.xml`:
  1. If `knowledgeActionEnabled` is `true`:
     - add an action entry with `action_type: "knowledge"`
     - include `knowledgeActionEnabled: true`
  2. If `knowledgeFallbackEnabled` is `true`:
     - add an action entry with `action_type: "knowledge"`
     - include `knowledgeFallbackEnabled: true`
- When both fields are `true`, capture both flags (either on one combined knowledge action record or two explicit knowledge action records), but ensure both booleans are present in extracted output.

**Offline mode signature generation (required):**

When input mode is offline (`.bot-meta.xml` + `.botVersion-meta.xml` provided, no org fetch):

1. Generate action signatures from bot metadata mappings only (do not block on missing Apex/Flow source code).
2. For each invocation mapping:
   - extract action parameter names from invocation input/output mapping keys
   - resolve mapped bot variable names from mapping values
   - infer parameter types from mapped variable declarations in `<conversationVariables>` / `<contextVariables>` when available
3. If type cannot be inferred, use a conservative placeholder type (`Text` or `Object`) and flag in notes/open questions.
4. Keep unresolved/partial signatures as non-blocking and continue extraction.

**Signature construction rules:**

1. Do not copy bot variable names as action parameter names unless metadata explicitly uses the same name.
2. Preserve both layers in output:
   - contract layer: `input_name` / `output_name`, `type`
   - mapping layer: `mapped_variable`, `variable_type` (`mutable` or `linked`)
3. For each signature entry, capture direction explicitly:
   - `direction: input` for values read by the action
   - `direction: output` for values written by the action
4. If one action is invoked multiple times with different mappings, keep one action signature and record per-call mapping context separately (for example `call_context`).

### 5) Dialog Clusters and Categorization

After extracting actions and dialog/action mappings, categorize bot functionality into dialog clusters.

1. Classify actions into groups using these priority criteria (highest priority first):
   - actions working on the same underlying entity SHOULD be grouped together
   - actions writing/updating the same variable SHOULD be grouped together
   - actions reading the same input variable CAN be grouped together
   - actions invoked by dialogs in the same dialog group CAN be grouped together
   - actions with similar intent CAN be grouped together
2. Keep group size between:
   - minimum: 1 action
   - maximum: 4 actions
   If a group exceeds 4 actions, split it while preserving higher-priority criteria.
3. An action may belong to multiple groups when criteria requires an overlap.
4. Assign dialogs to groups based on associated actions:
   - for each grouped action, trace back dialogs that invoke it
   - include those dialogs in the corresponding dialog cluster
   - maintain an `action_dialog_mapping` for each group (`action -> [dialogs]`)
5. Generate a short functional description (2-3 sentences) per group using grouped actions and associated dialogs.

## Extraction Output Shape

Build an intermediate extraction summary used by mapping:

```json
{
  "run_identity": {},
  "dialog_graph": {
    "nodes": [],
    "edges": []
  },
  "intent_catalog": {},
  "variables": {},
  "action_inventory": {},
  "dialog_clusters": {},
  "unmapped_items": {}
}
```

## Persist Extraction Output

Write the extraction summary to a JSON file before starting mapping.

- Output filename: `extraction-summary.json`
- Output location: same working/output directory used for the current bot/version handoff artifacts
- The file content must preserve the extraction output shape defined above
- If extraction is rerun, overwrite this file with the latest extraction snapshot

`action_inventory` should include any extracted knowledge action entries with explicit `knowledgeActionEnabled` and/or `knowledgeFallbackEnabled` boolean flags when present in bot version metadata.

## Extraction Principles

- Favor explicit configured behavior over assumptions.
- Preserve branch conditions where available.
