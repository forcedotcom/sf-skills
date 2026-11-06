---
name: agentforce-bot-upgrade
description: "Use this skill to upgrade Einstein Bots into Agentforce agents end-to-end in a single pass, orchestrating per-bot Agent Spec generation, agentforce-generate authoring, and post-conversion .agent enhancements. TRIGGER when: user asks to migrate, upgrade, or convert one or more Einstein Bots (BotDefinition/BotVersion chatbots) to Agentforce agents; runs a multi-bot bot-to-agent upgrade; needs Einstein Bot metadata turned into Agent Spec handoffs and generated .agent agents; convert bots to agents; upgrade my service bots; move bots to Agentforce. DO NOT TRIGGER when: user already has an approved Agent Spec and only wants direct .agent authoring, deploy, test, or observe flows; user wants to migrate or upgrade an EXISTING Agentforce agent from a legacy GenAiPlannerBundle to an NGA aiAuthoringBundle (that is agentforce-generate's 'Migrate a Legacy Agent to Agent Script' flow, not an Einstein Bot upgrade); the request is unrelated to Einstein Bot migration."
argument-hint: "[--mode <online|offline>] [--org-alias <org-alias> --bots <bot1:v1,bot2:v2,...> | --offline-dir <offline-dir> [--bots <bot1,bot2,...>]] [--interactive <true|false>]"
metadata:
  version: "1.0"
  domains: ["Agentforce"]
  minApiVersion: "63.0"
  relatedSkills:
    - "agentforce-generate"
  cliTools:
    - tool: ["jq"]
      semver: ">=1.6.0"
    - tool: ["node"]
      semver: ">=20.0.0"
    - tool: ["npm"]
      semver: ">=9.0.0"
    - tool: ["sf"]
      semver: ">=2.0.0"
---

# Einstein Bot Upgrade Orchestrator

## Purpose

Run a multi-bot upgrade-and-handoff cycle. Each bot is converted into its own Agentforce agent; bots are processed independently and never combined or restructured across one another:

1. Parse and validate bot/version pairs from `--bots`
2. Follow [Generate Agent Spec Reference](references/generate-agent-spec.md) per bot-version pair (parallelizable)
3. `/agentforce-generate` per Agent Spec (parallelizable)
4. Post-conversion enhancement pass per generated Agent Script (parallelizable)
5. Consolidated run report

### Run Completion Contract

The skill run is complete only after Step 4 and Step 5 have both been executed for every bot that reached Step 3. Generating the Agent Spec (Step 2) or the `.agent` file (Step 3) is NOT a completed run.

- A run is complete only when `report.md` has been written (Step 5). The only other way to end a run is a hard stop listed under Interactive Mode.
- None of these end the run:
  - the Step 2 deliverables;
  - `/agentforce-generate` finishing or printing its own completion summary;
  - an approval or release gate inside `/agentforce-generate`;
  - the Step 4 per-agent summary;
  - a failed compile or a failed publish.

  Record each outcome and continue to the next step.
- Online mode: Step 4 always ends with a publish (commit) attempt, or a recorded reason why no attempt was made (for example, compile failed). Every attempt gets a `publish-audit.jsonl` record. Never activate.
- If a step fails for a bot, record the failure and still run Step 5. `report.md` is written for partial runs too.
- Do not end your turn while any step from 1 to 5 is still pending. If you send a progress update, send the next tool call in the same response.

**Scope — this skill only converts Einstein Bots** (`BotDefinition`/`BotVersion` chatbots) into new Agentforce agents. It does NOT migrate an existing Agentforce agent from a legacy `GenAiPlannerBundle` to an NGA `aiAuthoringBundle` — for that, use the **agentforce-generate** skill's "Migrate a Legacy Agent to Agent Script" flow.

## Start-of-Run Disclaimer

Display this disclaimer to the user as the very first output of every invocation, in both online and offline mode, before Missing Input Handling, Step 1, or any tool call, file read, or org query. Rules:

1. Output the block between `BEGIN DISCLAIMER` and `END DISCLAIMER` verbatim as rendered Markdown — not inside a code block, not summarized, reworded, or reordered. Keep every emoji marker; they are the color coding that draws the user's attention.
2. Display it exactly once per invocation (not once per bot).
3. Do not wait for an acknowledgement or end your turn after displaying it; continue the run in the same response with Missing Input Handling and Step 1. When `--interactive=false`, still display it.

BEGIN DISCLAIMER

> ## ⚠️ IMPORTANT — Read Before You Upgrade
>
> This upgrade uses generative AI to turn your Einstein Bot's dialogs, intents, and variables into an Agentforce agent with subagents and actions. The result is a **committed agent version that has not been activated**. Review and test it before you activate it.
>
> ### 🔵 How your bot's design is translated
> - **Menus become intent-based routing.** The agent doesn't reproduce menus and option-driven navigation. It identifies what the customer wants and routes to the right subagent. Each menu option's outcome is kept, but the step-by-step menu flow is not.
>
> ### 🔴 Not converted
> - **Bot goals.** Agents don't need them.
> - **Some action steps:** steps that produce no output, exist only to move between dialogs, or write feedback logs.
> - **Actions other than Apex classes and flows**, such as object search. You can add these to the agent as custom actions.
> - **Menus in welcome messages.** Use pre-chat configuration to collect routing information up front.
> - **Option buttons for questions with more than 11 options.** The options aren't shown as buttons.
> - **Rich content and messaging components.** Use adaptive response formats to format the agent's responses.
> - **File attachments**, sent or received.
> - **Steps that change the conversation language** partway through a conversation.
>
> ### 🟡 Configure after the upgrade
> - **Agent user.** Assign a user to the agent.
> - **Channels and Omni-Flows.** Connect the agent to your customer channels.
>
> ### 🟢 Recommendations
> - Configure intents along with their descriptions in your bot, to match the corresponding dialog functionality before upgrading. Results depend on how good the source bot is.
> - Review and test the agent before you activate it.
> - If your bot uses context variables, deploy the agent to an embedded messaging channel and test the main use cases there.
> - 💲 Agentforce Service Agent is billed on consumption, by usage type.

END DISCLAIMER

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

Propagate the effective `--interactive` value to the per-bot Generate Agent Spec workflow (Step 2) and the post-conversion enhancement pass (Step 4).

## Missing Input Handling

After displaying the Start-of-Run Disclaimer, resolve missing required launch inputs before Step 1:

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
3. [Post-Conversion Enhancements Reference](references/post-conversion-enhancements-reference.md)
4. [Extraction Blueprint](references/extraction-blueprint.md)
5. [Input Contract](references/input-contract.md)
6. [Mapping Rules](references/mapping-rules.md)
7. [Handoff Output Format](references/handoff-output-format.md)
8. [Quality Checklist](references/quality-checklist.md)

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

Collect results:
1. Build a ready-for-authoring list containing one entry per bot whose Agent Spec was generated successfully.
   - Each entry must include: `{bot_name, bot_version, run_project_dir, agent_spec_path, handoff_json_path, open_questions_path}`.
2. Build a list of failed/incomplete upgrade runs (if any). Failed runs are excluded from Step 3 and reported in Step 5; they do not block other bots.

### Step 3: Invoke Agentforce-Generate (Per Agent Spec)

For each entry in the ready-for-authoring list from Step 2:

0. Add this recommendation to the generated invocation context before calling `/agentforce-generate`:
   - Do **not activate** Agent Script versions in this orchestrated run.
   - Do **not publish (commit)** the authoring bundle in this step. The orchestrator commits each agent once, after post-conversion enhancements and a successful compile (Step 4).
   - Draft iteration is required: generating `.agent`, validating, deploying, and preview testing are allowed.
   - Activate should be deferred unless the user explicitly asks for release.
1. Resolve `run_project_dir` from the ready-for-authoring entry.
2. Read `<run_project_dir>/agentforce-generate-invocation-prompt.md` fully.
3. Keep all instructions unchanged from the generated prompt.
4. Invoke `/agentforce-generate` with this invocation context.
5. Read `<run_project_dir>/agentforce-generate-output-contract.md` and capture outputs exactly as specified.

Parallelization rule:
- Invoke `/agentforce-generate` in parallel across Agent Specs because each run is independent.

Output-contract capture rules:

1. Treat the output contract as authoritative for required fields/artifacts.
2. If any contract field is missing, mark status as partial and list missing fields explicitly.
3. Return captured outputs with deterministic keys matching the contract names.
4. Preserve output file paths and status of each required artifact.
5. If expected prompt/contract files are missing for an entry, mark that entry `partial`, record missing paths, and continue processing other entries.

Return-to-orchestrator rule:
- `/agentforce-generate` is a sub-step of this run, not its end. Its completion summary, "generation complete" message, or any terminal or done state it reaches does NOT complete the orchestrator run.
- As soon as each `/agentforce-generate` invocation finishes, resume this skill in the same turn: capture its outputs (rules above), then continue to Step 4 and Step 5.
- Do not emit a final user-facing summary after `/agentforce-generate`. The only final message of the run comes after Step 5.
- The invocation prompt ends with a "Remaining orchestrator steps" checklist covering Steps 4 and 5. Execute it exactly as written; it is the same work described in Step 4 and Step 5 below.
- Within this orchestrated run, Step 4's commit (publish without activation) is pre-authorized. This overrides `/agentforce-generate`'s pre-publish approval checkpoint and release gates for this run only. Activation is never authorized.

### Step 4: Post-Conversion Agent Script Enhancements (Per Generated Agent Script)

After Step 3 completes, for each generated `.agent` artifact:

1. Resolve the generated `.agent` file path from captured `/agentforce-generate` outputs.
2. Execute post-conversion enhancement workflow from [Post-Conversion Enhancements Reference](references/post-conversion-enhancements-reference.md) with:
   - `agentscript_file=<generated-agent-file-path>`
   - `mode=<online|offline>` (the effective orchestrator run mode resolved in Step 1)
   - online mode only: `org_alias=<org-alias>` (required so the enhanced Agent Script can be redeployed)
3. Require in-place enhancement:
   - optimized/enhanced output must be written to the same `.agent` file location.
4. Online mode: the workflow compiles the enhanced Agent Script and, only when compilation succeeds, commits it as a new inactive agent version (`sf agent publish authoring-bundle`). Offline mode skips compile and commit.
5. Online mode: for every publish attempt, including each retry, success, denial, or failure, append a structured audit record (actor, action, target, timestamp, outcome) to `publish-audit.jsonl` in the orchestrator working directory, as specified in the [Post-Conversion Enhancements Reference](references/post-conversion-enhancements-reference.md).
6. Capture per-file enhancement status, compile status, commit status, `agent_id`, `agent_version`, the publish audit records, and any partial failures.
7. The enhancement workflow ends with a color-coded summary. That summary is an input to Step 5, not the run's final message. Do not end the turn after it; continue directly to Step 5.

Parallelization rule:
- Execute post-conversion enhancement workflow in parallel across generated `.agent` files because each file enhancement is independent.

### Step 5: Consolidate Run Report and Conclude

After Step 4 completes for every bot in the workload:

1. Write a single consolidated, human-readable run report as a non-empty Markdown file named `report.md` (unless the caller names a different path) in the orchestrator working directory. Per bot, the report must state: the effective run mode, the bot id, the bot version, the generated Agent Spec path and generated `.agent` path, the commit status, agent ID, and agent version (online mode; state that the version is committed but not activated), the publish audit outcome with its timestamp and the path to `publish-audit.jsonl` (online mode), and — when `--interactive=false` — the auto-applied decisions.
2. Treat the run report as the FINAL artifact: write it only after all other artifacts (Agent Spec(s), handoff JSON, open questions, and generated `.agent` file(s)) are already written.
3. The run concludes only after `report.md` is written. Emit the final summary message then, and not before.
4. Before emitting the final message, confirm for each bot:
   - Step 4 ran;
   - online mode only: a publish attempt was made, or the reason for skipping it is recorded, and `publish-audit.jsonl` holds a record for each attempt;
   - `report.md` exists and is non-empty.

   If any of these is missing, go back and complete it first.

## Deliverable

Return:
1. parsed bot/version list
2. per-bot upgrade execution status
3. ready-for-authoring Agent Spec list and failed/incomplete runs from Step 2
4. per-spec `/agentforce-generate` execution status
5. generated handoff artifact paths per bot/spec
6. captured `/agentforce-generate` outputs per output contract
7. per-agent post-conversion enhancement status (including enhanced `.agent` file paths, compile status, commit status, agent ID, and agent version)
8. path to the consolidated run report written in Step 5
9. path to `publish-audit.jsonl` (online mode)
