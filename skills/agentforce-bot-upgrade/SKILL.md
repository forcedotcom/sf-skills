---
name: agentforce-bot-upgrade
description: "Use this skill to Upgrade Einstein Bots into Agentforce agents end-to-end in a single pass, orchestrating per-bot Agent Spec generation, planner reconciliation across bots, agentforce-generate authoring, and post-conversion .agent enhancements. TRIGGER when: user asks to migrate, upgrade, or convert one or more Einstein Bots to Agentforce; runs a multi-bot bot-to-agent upgrade; needs Einstein Bot metadata turned into Agent Spec handoffs and generated .agent agents; convert bots to agents; upgrade my service bots; move bots to Agentforce. DO NOT TRIGGER when: user already has an approved Agent Spec and only wants direct .agent authoring, deploy, test, or observe flows; the request is unrelated to Einstein Bot migration."
argument-hint: "[--mode <online|offline>] [--org-alias <org-alias> --bots <bot1:v1,bot2:v2,...> | --offline-dir <offline-dir> [--bots <bot1,bot2,...>]] [--interactive <true|false>]"
metadata:
  version: "1.0"
  minApiVersion: "63.0"
  relatedSkills:
    - "agentforce-generate"
  cliTools:
    - tool: ["sf"]
      semver: ">=2.0.0"
---

# Einstein Bot Upgrade Orchestrator

## Purpose

Run a multi-bot upgrade-and-handoff cycle:

1. Parse and validate bot/version pairs from `--bots`
2. Follow [Generate Agent Spec Reference](references/generate-agent-spec.md) per bot-version pair (parallelizable)
3. Aggregation step that requires all generated Agent Specs
4. `/agentforce-generate` per Agent Spec (parallelizable)
5. Post-conversion enhancement pass per generated Agent Script (parallelizable)

## Inputs

Inputs:
- `--mode <online|offline>` is optional; default is `online` when omitted.
- If `mode=online`, required:
  - `--org-alias <org-alias>`
  - `--bots <bot1:v1,bot2:v2,...>`
- If `mode=offline`, required:
  - `--offline-dir <offline-dir>`
- `--interactive <true|false>` is optional; default is `true` when omitted.

If required inputs are missing, handle per the Missing Input Handling and Interactive Mode rules below.

## Interactive Mode

`--interactive` controls whether the skill pauses for user input during execution:

- `--interactive true` (default): resolve ambiguities, open questions, and approval gates by asking the user, as described in this skill and its references.
- `--interactive false`: run autonomously. Do NOT prompt the user at any decision point. For every open question, ambiguity, or approval gate, apply the documented recommended default/solution and record the auto-applied decision in the run artifacts (Agent Spec, open questions, extraction summary). The only hard stops permitted without prompting are inputs that are missing or contradictory with no safe recommended default — a missing mandatory launch input (`--org-alias`/`--bots` for online, `--offline-dir` for offline), no bots discovered, or the same bot given multiple versions. In those cases, report the issue and halt without prompting.

Propagate the effective `--interactive` value to the per-bot Generate Agent Spec workflow (Step 2), the planner workflow (Step 3), and the post-conversion enhancement pass (Step 5).

## Missing Input Handling

Resolve missing required launch inputs before Step 1:

1. **Online mode — `--org-alias` not provided.** Resolve this before attempting to list bots (listing requires a target org).
   - Interactive: list the available aliases of logged-in orgs and ask the user to select the target org. Use the SF CLI patterns in [SF CLI Bot Reference](references/sf-cli-bot-reference.md).
   - Non-interactive: halt with an explicit error naming the missing `--org-alias` input (do not prompt or list).
2. **Online mode — bot name and version (`--bots`) not available.**
   - Interactive: using `--org-alias` as the target org, list every bot and its versions in the org, then ask the user to select the bot/version entries they want to convert to agents. Use the `BotDefinition` and `BotVersion` query patterns in [SF CLI Bot Reference](references/sf-cli-bot-reference.md) — omit the name/version filters to enumerate all bots and versions — present the results, and build the `--bots` workload from the user's selection.
   - Non-interactive: halt with an explicit error naming the missing `--bots` input (do not prompt or list).
3. **Offline mode — `--offline-dir` not available.**
   - Interactive: ask the user to provide the `--offline-dir` path, then continue.
   - Non-interactive: fail with an explicit error naming the missing `--offline-dir` input (do not prompt).

## References

Use these reference files during execution:

1. [SF CLI Bot Reference](references/sf-cli-bot-reference.md)
2. [Generate Agent Spec Reference](references/generate-agent-spec.md)
3. [Planner Workflow Reference](references/planner-workflow-reference.md)
4. [Post-Conversion Enhancements Reference](references/post-conversion-enhancements-reference.md)
5. [Extraction Blueprint](references/extraction-blueprint.md)
6. [Input Contract](references/input-contract.md)
7. [Mapping Rules](references/mapping-rules.md)
8. [Handoff Output Format](references/handoff-output-format.md)
9. [Quality Checklist](references/quality-checklist.md)

## Execution Contract

### Step 1: Parse and Validate `--bots`

Execute Step 1 in this order:

1. Resolve mode:
   - If `--mode` omitted, use `online`.
2. Start fresh for this invocation:
   - do not discover, inspect, or reuse outputs from previously existing runs
   - treat this invocation as a clean execution context
   - only use artifacts produced during the current invocation flow
3. Build initial workload list:
   - `mode=online`: read `--bots` and split by comma.
   - `mode=offline`: scan `<offline-dir>` and collect immediate sub-directories as bot workload roots.
4. Validate input shape:
   - `mode=online`: each `--bots` token must match `<bot-name>:<version>`.
   - `mode=offline`: ensure at least one bot sub-directory exists; otherwise STOP (in interactive mode ask the user to clarify; in non-interactive mode halt with an explicit error per the Interactive Mode rule).
5. Normalize workload entries:
   - `mode=online`: build `{bot_name, bot_version}` entries.
   - `mode=offline`: build `{offline_bot_dir}` entries (Annotate inferred bot name and version when derivable from the sub-directory structure; if not derivable, leave the entry unnamed and continue).
6. Enforce one-version-per-bot rule (online mode):
   - If the same `bot_name` appears with multiple versions, STOP (in interactive mode ask the user to clarify; in non-interactive mode halt with an explicit error per the Interactive Mode rule).
7. Apply offline bot filter:
   - If `mode=offline` and `--bots` is provided, use `--bots` only as a filter over discovered sub-directories; do not treat it as required offline input.
8. Persist Step 1 output:
   - Save and carry forward a validated workload list for Step 2 parallel execution.

### Step 2: Run Einstein Bot Upgrade (Per Bot-Version)

Execute the agent spec generation workflow from [Generate Agent Spec Reference](references/generate-agent-spec.md) per bot-version combination:
- `--mode <online|offline>` (default `online` if omitted)
- mode-specific required inputs:
  - online -> `--org-alias`, `--bot`, `--bot-version`
  - offline -> `--offline-dir`
- `--interactive <true|false>` (pass through the effective orchestrator value; default `true`)

Parallelization rule:
- In `mode=online`, execute invocations in parallel because each bot-version pair is independent.
- In `mode=offline`, execute the [Generate Agent Spec Reference](references/generate-agent-spec.md) workflow in parallel over every bot sub-directory discovered in Step 1.
  - Pass `--mode offline` and `--offline-dir <bot-subdirectory-path>` per invocation.
Ensure each invocation (online/offline) uses isolated working directories to avoid cross-run file collisions.

Hard rules:
- Do not skip this step.

### Step 3: Aggregation + Planner Step (Conditional)

After all upgrade invocations complete:

1. Always build a consolidated list of `{bot_name, bot_version, run_project_dir, agent_spec_path}`.
2. Always build list of failed/incomplete upgrade runs (if any).
3. Always build an initial ready-for-authoring list containing only valid Agent Spec entries.
   - Each entry must include: `{bot_name, bot_version, run_project_dir, agent_spec_path, handoff_json_path, open_questions_path}`.
4. If total bot workload count is greater than 1:
   - Execute planner workflow from [Planner Workflow Reference](references/planner-workflow-reference.md) using:
     - all ready-for-authoring `agent_spec_path` values as `spec_paths`
     - orchestrator working directory as `working_dir`
     - the associated per-spec artifacts from each ready-for-authoring entry: `handoff_json_path` (handoff JSON) and `open_questions_path` (open questions)
   - Require output file at `<orchestrator working directory>/bot-upgrade-planner-output.json`.
   - Read `bot-upgrade-planner-output.json` and apply:
     - if `specs_changed=true`: replace ready-for-authoring entries using planner fields (`updated_spec_path`, `run_project_dir`, `handoff_json_path`, `open_questions_path`)
     - if `specs_changed=false`: keep original ready-for-authoring list unchanged
5. If total bot workload count is 1:
   - Skip planner workflow entirely.
   - Keep original ready-for-authoring list unchanged.

Planner output expectations:
1. boolean `specs_changed`
2. `updated_specs` array with entries:
   - `original_spec_path`
   - `updated_spec_path`
   - `run_project_dir`
   - `handoff_json_path`
   - `open_questions_path`
3. `updated_specs` must be empty when `specs_changed=false`

### Step 4: Invoke Agentforce-Generate (Per Agent Spec)

For each entry in final ready-for-authoring list (post Step 3 planner reconciliation):

0. Add this recommendation to the generated invocation context before calling `/agentforce-generate`:
   - Do **not activate** Agent Script versions in this orchestrated run.
   - Draft iteration is required: generating `.agent`, validating, deploying, and preview testing are allowed.
   - Activate should be deferred unless the user explicitly asks for release.
1. Resolve effective `run_project_dir` from the final ready-for-authoring entry.
2. Read `<run_project_dir>/agentforce-generate-invocation-prompt.md` fully.
3. If Step 3 produced planner-updated spec paths/artifacts, apply path substitutions in the invocation context so spec/handoff/open-questions references point to updated files.
   - If planner also changed `run_project_dir`, use that updated `run_project_dir` for resolving prompt/output-contract paths.
4. Keep all non-path instructions unchanged from the original generated prompt.
5. Invoke `/agentforce-generate` with this resolved invocation context.
6. Read `<run_project_dir>/agentforce-generate-output-contract.md` and capture outputs exactly as specified.

Parallelization rule:
- Invoke `/agentforce-generate` in parallel across Agent Specs because each run is independent.

Output-contract capture rules:

1. Treat the output contract as authoritative for required fields/artifacts.
2. If any contract field is missing, mark status as partial and list missing fields explicitly.
3. Return captured outputs with deterministic keys matching the contract names.
4. Preserve output file paths and status of each required artifact.
5. If expected prompt/contract files are missing for an entry, mark that entry `partial`, record missing paths, and continue processing other entries.

### Step 5: Post-Conversion Agent Script Enhancements (Per Generated Agent Script)

After Step 4 completes, for each generated `.agent` artifact:

1. Resolve the generated `.agent` file path from captured `/agentforce-generate` outputs.
2. Execute post-conversion enhancement workflow from [Post-Conversion Enhancements Reference](references/post-conversion-enhancements-reference.md) with:
   - `agentscript_file=<generated-agent-file-path>`
   - `mode=<online|offline>` (the effective orchestrator run mode resolved in Step 1)
   - online mode only: `org_alias=<org-alias>` (required so the enhanced Agent Script can be redeployed)
3. Require in-place enhancement:
   - optimized/enhanced output must be written to the same `.agent` file location.
4. Capture per-file enhancement status and any partial failures.

Parallelization rule:
- Execute post-conversion enhancement workflow in parallel across generated `.agent` files because each file enhancement is independent.

### Step 6: Consolidate Run Report and Conclude

After Step 5 completes for every bot in the workload:

1. Write a single consolidated, human-readable run report as a non-empty Markdown file in the orchestrator working directory. Per bot, the report must state: the effective run mode, whether the planner ran (`executed` or `skipped`), the generated Agent Spec path and generated `.agent` path, the action inventory (including any `NEEDS_STUB` items), and — when `--interactive=false` — the auto-applied decisions.
2. Treat the run report as the FINAL artifact: write it only after all other artifacts (Agent Spec(s), handoff JSON, open questions, any planner output, and generated `.agent` file(s)) are already written.

## Deliverable

Return:
1. parsed bot/version list
2. per-bot upgrade execution status
3. aggregation output (full Agent Spec list + final ready-for-authoring subset)
4. planner workflow status (`executed` or `skipped`) and `bot-upgrade-planner-output.json` path when executed
5. per-spec `/agentforce-generate` execution status
6. generated handoff artifact paths per bot/spec (including planner-updated artifacts when applicable)
7. captured `/agentforce-generate` outputs per output contract
8. per-agent post-conversion enhancement status (including enhanced `.agent` file paths)
9. path to the consolidated run report written in Step 6
