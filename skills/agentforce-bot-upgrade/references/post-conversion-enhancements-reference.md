# Post-Conversion Enhancements Reference

Use this reference during orchestrator Step 5 after `/agentforce-generate` completes.

## Scope

Apply per generated Agent Script artifact (`.agent`) independently.

## Inputs

Required:

1. `agentscript_file`: path to one generated `.agent` file
2. `mode` (`online|offline`): the effective orchestrator run mode

Conditionally required:

3. `org_alias`: target org alias used to redeploy in Step 9. Required when `mode=online`; omit when `mode=offline`.

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
10. If enhancements modified the Agent Script:
   - when `mode=online`, deploy/publish the updated Agent Script to the org again using the provided `org_alias`
   - do not activate as part of this step
   - when `mode=offline`, skip deploy and keep the updated local file only

## Output

- Enhanced Agent Script at the same input file location.

## Capture Requirements

For each processed file, capture:

1. `agentscript_file`
2. status (`success` or `partial`)
3. short enhancement summary
4. `agentscript_modified` (`true|false`)
5. redeploy status (online mode only): `deployed`, `skipped`, or `failed`
