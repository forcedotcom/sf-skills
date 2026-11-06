# Post-Conversion Enhancements Reference

Use this reference during orchestrator Step 4 after `/agentforce-generate` completes.

## Scope

Apply per generated Agent Script artifact (`.agent`) independently.

## Inputs

Required:

1. `agentscript_file`: path to one generated `.agent` file
2. `mode` (`online|offline`): the effective orchestrator run mode

Conditionally required:

3. `org_alias`: target org alias used to deploy, compile, commit, and look up the agent in steps 10–13. Required when `mode=online`; omit when `mode=offline`.

## Required Workflow

1. Read the full `.agent` file.
2. Enforce `start_agent` router behavior:
   - ensure the subagent marked `start_agent` contains explicit instructions that 
        - it is only a router and should route immediately to the correct downstream agent
        - it never responds directly to the user
   - if this instruction is missing, add it
3. Improve transition quality with meaningful `available when` conditions:
   - add or refine conditions between subagents wherever possible
   - conditions should be meaningful and correct for transition intent
   - conditions should reduce routing noise and improve next-step navigation in the final agent
4. Validate action data flow integrity:
   - ensure action inputs/outputs are correctly mapped through conversation variables or LLM inputs
   - where needed, persist required LLM-derived values via `setVariables`
   - ensure downstream actions can consume required values deterministically
5. Enforce numeric action I/O typing:
   - when an action input/output is numeric and flows between actions (e.g. rewards points
     feeding a merchandise action), use the publish-safe form: an object field with
     `complex_data_type_name: lightning__numberType`, not a bare `number`, so numeric typing
     survives publish across all orgs.
6. Validate escalation mapping:
   - ensure any escalation/transfer behavior (Einstein Bot `SystemMessage` `Transfer`, or any "hand off to a live agent/human") is implemented via the built-in `@utils.escalate` utility.
   - confirm escalation is NOT modeled as a standalone/new action: there must be no `Transfer_To_Agent`-style action and no action-inventory entry (including `NEEDS_STUB`/`NEEDS_CREATION`) representing the transfer.
   - if the escalation is present in bot and missing in spec, or was authored as an action instead of `@utils.escalate`, fix it: remove the erroneous action and invoke `@utils.escalate` in the appropriate escalation subagent (keeping any resolved transfer target as a variable/context, not an action signature).
7. Preserve intended functionality and behavioral coverage.
8. Write the optimized/enhanced content back to the same file path (in-place update).
9. Validate the resulting file:
   - remains readable and structurally coherent
   - is a valid Agent Script
10. When `mode=offline`, keep the updated local file only and do not deploy, compile against an org, or commit: skip to step 14. Steps 10–13 apply to `mode=online` only.
    Resolve `<Developer_Name>` as the `AiAuthoringBundle` directory name containing `agentscript_file` (it matches `config.developer_name` in the `.agent` file). Run every command from the run's SFDX project directory.
    If enhancements modified the Agent Script, deploy the updated authoring bundle:
    ```bash
    sf project deploy start --json --metadata AiAuthoringBundle:<Developer_Name> --target-org <org_alias>
    ```
11. Compile the authoring bundle:
    ```bash
    sf agent validate authoring-bundle --json --api-name <Developer_Name> --target-org <org_alias>
    ```
    - If compilation reports errors, fix them in the `.agent` file (preserving intended functionality), redeploy per step 10, and recompile until clean.
    - If compilation still fails after reasonable fix attempts, do NOT commit: set `commit_status=skipped`, mark the file `partial`, record the compile errors, and skip to step 14.
12. Commit the agent only after compilation succeeds. `sf agent publish authoring-bundle` commits the authoring bundle as a new agent version and creates its runtime metadata (`Bot`, `BotVersion`, `GenAiPlannerBundle`):
    ```bash
    sf agent publish authoring-bundle --json --api-name <Developer_Name> --target-org <org_alias>
    ```
    - Commit even when enhancements made no modifications — the generated agent must end the run as a committed version.
    - Do NOT activate the committed version (`sf agent activate` is out of scope for this run). Publishing leaves the version inactive.
    - If publish fails, follow the **agentforce-generate** skill's "Troubleshooting Publish Failures" checks (Agent Metadata and Lifecycle reference) — commonly an invalid `default_agent_user`, undeployed action implementations, or a stale `<target>` lock in `bundle-meta.xml` — fix the cause, and retry. If it still fails, set `commit_status=failed`, mark the file `partial`, and record the error.
    - Emit a structured audit record for every publish attempt, including each retry, whether it succeeds, is denied, or fails. Before the first attempt, resolve the actor once from the target org:
      ```bash
      sf org display --json --target-org <org_alias>
      ```
      Then, right after each `sf agent publish authoring-bundle` returns, append one JSON object (one line) to `publish-audit.jsonl` in the orchestrator working directory:
      ```json
      {"actor": "<result.username>", "actor_org_id": "<result.id>", "action": "agent.publish", "target": "AiAuthoringBundle:<Developer_Name>", "target_org": "<org_alias>", "timestamp": "<UTC ISO-8601 time the publish returned>", "outcome": "success|denied|failed", "detail": "<error name and message, or empty on success>"}
      ```
      - `outcome=denied`: the org rejected the caller's access, for example `INSUFFICIENT_ACCESS`, a missing permission, or an expired or unauthorized session.
      - `outcome=failed`: any other publish error.
      - Only append to the audit file; never rewrite or remove earlier records. Fill the record only from the command results. Do not include tokens, session IDs, or other credentials.
13. After a successful commit, fetch the agent ID and the committed version. The publish response reports neither, so query the runtime records:
    ```bash
    # Agent ID (BotDefinition Id, key prefix 0Xx)
    sf data query --json --target-org <org_alias> \
      --query "SELECT Id, DeveloperName FROM BotDefinition WHERE DeveloperName = '<Developer_Name>'"

    # Committed version: the newest BotVersion (expected Status = Inactive)
    sf data query --json --target-org <org_alias> \
      --query "SELECT Id, VersionNumber, Status FROM BotVersion WHERE BotDefinition.DeveloperName = '<Developer_Name>' ORDER BY VersionNumber DESC LIMIT 1"
    ```
    - Record `agent_id` from the `BotDefinition` `Id`, and `agent_version` from the `BotVersion` `VersionNumber`.
    - If either query returns no record, keep `commit_status=committed`, leave the missing value empty, and record the query result so the gap is visible in the run report.
14. As the final step, in both modes, give the user a summary for this agent. Run this step even when the file stopped early at step 10 or step 11.
    Color code the summary in the same format as the Start-of-Run Disclaimer in [SKILL.md](../SKILL.md): render it as Markdown (not inside a code block) in one blockquote, with an emoji-marked heading for each of the three sections below, in this order. Keep every emoji marker.
    - **`### 🔵 Converted`:** what was converted from the bot — subagents, actions, variables, and escalation and end-chat behavior.
    - **`### 🔴 Not converted`:** what was not converted, and why — because of the user's choices (for example, removed bot-only actions or resolved open questions) or because of the conversion logic (for example, unsupported step types, or actions other than Apex classes and flows). Name the dialog and step for each skipped item.
    - **`### ➡️ Next Steps`:** next steps for the user. Start each step with its emoji marker: 🟡 for configuration the user must complete, 🟢 for testing and verification. Keep the step order below.
      1. 🟡 *Queue escalation targets:* include this item only when the bot escalates to a queue. Tell the user to perform these tasks in order:
         1. Create a new custom field `EscalationQueueId` (API name `EscalationQueueId__c`) on the Messaging Session (`MessagingSession`) object.
         2. Create an Apex class that updates the `EscalationQueueId` field. Inputs: `MessagingSessionId` (from the `@MessagingSession.Id` linked variable) and `QueueId`. Output: Boolean (status).
         3. Create a flow that reads the `EscalationQueueId` value from the Messaging Session record matching the session ID, then routes to the queue with that ID. Inputs: `recordId` (the default input to omni routing flow, which contains the MessagingSession id).
         4. Set the flow as the route in the corresponding channel connection.
         5. Add the Apex class to the relevant subagent, and modify its instructions to first invoke the Apex action to store the queue ID. Then escalate (using `@utils.escalate`) to transfer the conversation to the queue.
      2. 🟢 Test the agent in preview mode in Agent Builder to verify its functionality and its conversational experience.
      3. 🟡 Verify the channels and the escalation target in each connection, and enable Adaptive Response Formats. Then test agent conversations in those channels (for example, Messaging for In-App and Web (MIAW) or WhatsApp).

## Output

- Enhanced Agent Script at the same input file location.
- Online mode: the agent committed to the org as a new, inactive version.
- Online mode: one audit record per publish attempt in `publish-audit.jsonl`.

## Capture Requirements

For each processed file, capture:

1. `agentscript_file`
2. status (`success` or `partial`)
3. short enhancement summary
4. `agentscript_modified` (`true|false`)
5. redeploy status (online mode only): `deployed`, `skipped`, or `failed`
6. compile status (online mode only): `success` or `failed`
7. commit status (online mode only): `committed`, `skipped` (compilation failed), or `failed` (publish failed)
8. `agent_id` (online mode only, when `commit_status=committed`): `BotDefinition` Id
9. `agent_version` (online mode only, when `commit_status=committed`): committed `BotVersion` `VersionNumber`
10. publish audit records (online mode only, when publish was attempted): the `publish-audit.jsonl` entries for this agent, with actor, action, target, timestamp, and outcome
11. user summary (step 14): converted items, skipped items with reasons, and next steps
