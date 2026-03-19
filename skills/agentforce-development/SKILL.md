---
name: agentforce-development
description: "Use this skill when working with Salesforce Agent Script — the scripting language for authoring Agentforce agents using the Atlas Reasoning Engine. Triggers include: creating, modifying, or comprehending Agent Script agents; working with AiAuthoringBundle files or .agent files; designing topic graphs or flow control; producing or updating an Agent Spec; validating Agent Script or diagnosing compilation errors; previewing agents or debugging behavioral issues; deploying, publishing, activating, or deactivating agents; deleting or renaming agents; authoring AiEvaluationDefinition test specs or running agent tests. This skill teaches Agent Script from scratch — AI models have zero prior training data on this language. Do NOT use for Apex development, Flow building, Prompt Template authoring, Experience Cloud configuration, or general Salesforce CLI tasks unrelated to Agent Script."
license: Apache-2.0
compatibility: "Requires Agentforce license, API v66.0+, Einstein Agent User"
metadata:
  version: "0.4.8"
  last_updated: "2026-03-17"
---

# Agent Script Skill

## What This Skill Is For

Agent Script is Salesforce's scripting language for authoring next-generation AI agents on the Atlas Reasoning Engine. Introduced in 2025 with zero training data in any AI model. Everything needed to write, modify, diagnose, or deploy Agent Script agents is in this skill's reference files.

**⚠️CRITICAL:** Agent Script is NOT AppleScript, JavaScript, Python, or any other
language. Do NOT confuse Agent Script syntax or semantics with any other
language you have been trained on.

Agent Script agents are defined by `AiAuthoringBundle` metadata — a directory with a `.agent` file containing Agent Script source that describes topics, actions, instructions, flow control, and configuration; and a `bundle-meta.xml` file containing bundle metadata. Agents process utterances by routing through topics, each with instructions and actions backed by Apex, Flows, Prompt Templates, and other types of backing logic.

This skill covers the full Agent Script lifecycle: designing agents,
writing Agent Script code, validating and debugging, deploying and
publishing, and testing.

## How to Use This Skill

This file maps user intent to task domains and relevant reference files in `references/`. Detailed knowledge includes syntax rules, design patterns, CLI commands, debugging workflows, and more.

Identify user intent from task descriptions. ALWAYS read indicated reference files BEFORE starting work.

## Rules That Always Apply

1. **Always `--json`.** ALWAYS include `--json` on EVERY `sf` CLI command.

2. **Diagnose before you fix.** When validating/debugging agent behavior,
   ALWAYS `--use-live-actions` to preview authoring bundles. Send utterances
   then read resulting session traces to ground your understanding of the
   agent's behavior. Trace files reveal topic selection, action I/O, and
   LLM reasoning. DO NOT modify `.agent` files or backing logic without
   this grounding. See [Validation & Debugging](references/agent-validation-and-debugging.md)
   for trace file locations and diagnostic patterns.

3. **Spec approval is a hard gate.** Never proceed past Agent Spec
   creation without explicit user approval.

## Task Domains

Every task domain below has **Required Steps**. Follow verbatim, in order. Do not substitute your own plan or skip steps.

### Create an Agent

User wants to build new agent from scratch. ALWAYS use Agent Script. Work with User to understand the agent's purpose, topics, and actions using plain language without Salesforce-specific terminology.

#### Required Steps

Read [CLI for Agents](references/salesforce-cli-for-agents.md) for exact command syntax.

1. **Design** — Read [Design & Agent Spec](references/agent-design-and-spec-creation.md) to draft an Agent Spec. Always ask if you should scan for existing backing logic. Unless instructed otherwise, scan by reading `sfdx-project.json` to identify package directories, then search each for `@InvocableMethod` in `classes/`, `AutoLaunchedFlow` in `flows/`, and template metadata in `promptTemplates/`. Mark matches `EXISTS`; unmatched actions `NEEDS STUB`. **Always save Agent Spec as file.**
2. **STOP for user approval of Agent Spec.** Present to user. Ask for approval or feedback. **Do not proceed** without approval. Once approved, proceed without stopping unless a step fails.
3. **Validate environment prerequisites** — Read [Design & Agent Spec](references/agent-design-and-spec-creation.md), Section 3 (Environment Prerequisites). Based on agent type from design, validate org environment:
   - **Employee agent**: Confirm config block does NOT include `default_agent_user`. Remove if present.
   - **Service agent**: Query org for Einstein Agent User. If one exists, confirm username with user. If none, guide user through creation. See [CLI for Agents](references/salesforce-cli-for-agents.md), Section 12 for creation steps and [Agent User Setup](references/agent-user-setup.md) for required permissions.
   **Do not proceed to code generation until environment is validated.**
4. **Generate authoring bundle** —
   `sf agent generate authoring-bundle --json --no-spec --name "<Label>" --api-name <Developer_Name>`
5. **Write code** — Read [Core Language](references/agent-script-core-language.md) for syntax, block structure, and anti-patterns. Edit generated `.agent` file using reference files and templates. Do not create `.agent` or `bundle-meta.xml` files manually.
6. **Validate compilation** —
   `sf agent validate authoring-bundle --json --api-name <Developer_Name>`
   If validation fails, read [Validation & Debugging](references/agent-validation-and-debugging.md) to diagnose and fix, then re-validate. ALWAYS fix syntax and structural errors before generating backing logic.
7. **Generate backing logic** — For each action marked NEEDS STUB:
   `sf template generate apex class --name <ClassName> --output-dir <PACKAGE_DIR>/main/default/classes`
   Replace class body with invocable pattern from [Design & Agent Spec](references/agent-design-and-spec-creation.md). ALWAYS deploy:
   `sf project deploy start --json --metadata ApexClass:<ClassName>`
   ALWAYS fix deploy errors BEFORE generating and deploying next stub.
8. **Validate behavior** — Read [Validation & Debugging](references/agent-validation-and-debugging.md) for preview workflow and session trace analysis.
   `sf agent preview start --json --use-live-actions --authoring-bundle <Developer_Name>`
   If actions query data, ground test utterances with:
   `sf data query --json -q "SELECT <Relevant_Fields> FROM <SObject> LIMIT 100"`
   Send test utterances with:
   `sf agent preview send --json --authoring-bundle <Developer_Name> --session-id <ID> -u "<message>"`
   Confirm topic routing, gating, and action invocations match Agent Spec. If behavior diverges, switch to **Diagnose Behavioral Issues** workflow. Return AFTER correcting issues.
9. **Publish** — **DO NOT proceed until step 8 passes.** Publish validates metadata structure, not agent behavior. ALWAYS validate behavior before publishing. Every publish creates permanent version number.
   `sf agent publish authoring-bundle --json --api-name <Developer_Name>`
   If publish fails, follow troubleshooting checklist in [Metadata & Lifecycle](references/agent-metadata-and-lifecycle.md), Section 5 before retrying.
10. **Activate** — Makes new version available to users.
    `sf agent activate --json --api-name <Developer_Name>`
11. **Verify published agent** — Preview user-facing behavior AFTER activation with
    `sf agent preview start --json --api-name <Developer_Name>`
    Use `--api-name`, not `--authoring-bundle`.
12. **Configure end-user access** — ONLY for employee agents. Read [Agent Access Guide](references/agent-access-guide.md) to configure perms and assign access.

#### Reference Files

1. [CLI for Agents](references/salesforce-cli-for-agents.md) — exact
   command syntax for generate, validate, deploy, publish, activate;
   Section 12 for Einstein Agent User creation
2. [Core Language](references/agent-script-core-language.md) — execution
   model, syntax, block structure, anti-patterns
3. [Design & Agent Spec](references/agent-design-and-spec-creation.md) —
   topic graph design, flow control patterns, Agent Spec production,
   backing logic analysis; Section 3 for environment prerequisites
4. [Topic Map Diagrams](references/agent-topic-map-diagrams.md) —
   Mermaid diagram conventions for visualizing the agent's topic graph
5. [Agent User Setup & Permissions](references/agent-user-setup.md) —
   permission set assignment, object permissions, cross-topic validation
6. [Metadata & Lifecycle](references/agent-metadata-and-lifecycle.md) —
   directory structure, bundle metadata; publish troubleshooting
7. [Validation & Debugging](references/agent-validation-and-debugging.md) —
   validate the agent compiles, preview to confirm behavior
8. [Agent Access Guide](references/agent-access-guide.md) — end-user
   access permissions, visibility troubleshooting
9. [Known Issues](references/known-issues.md) — only load when errors
   persist after code fixes

### Comprehend an Existing Agent

User wants to understand Agent Script agent they didn't write or need to revisit. May point to `AiAuthoringBundle` directory or ask "what does this agent do?" or "I need to fix this agent but I don't understand how it works.".

#### Required Steps

1. **Locate agent** — Read `sfdx-project.json` to identify package directories. Find `AiAuthoringBundle` directory within them. Read `.agent` file and `bundle-meta.xml`.
2. **Read code** — Read [Core Language](references/agent-script-core-language.md) for syntax and execution model BEFORE parsing `.agent` file.
3. **Map backing logic** — For each action with `target`, locate backing implementation (Apex class, Flow, Prompt Template) in project. Note input/output contracts.
4. **Reverse-engineer Agent Spec** — Read [Design & Agent Spec](references/agent-design-and-spec-creation.md) for Agent Spec structure. Produce Agent Spec from code and save as file.
5. **Produce Topic Map diagram** — Read [Topic Map Diagrams](references/agent-topic-map-diagrams.md) for Mermaid conventions. Generate flowchart of topic graph showing transitions, gates, and action associations.
6. **Annotate source** — Ask if user wants Agent Script source annotated with explanations. If requested, add inline comments to `.agent` file explaining flow control decisions, gating rationale, and topic relationships.
7. **Present to user** — Share Agent Spec, Topic Map, and annotated source if produced. Check Anti-Patterns section in Core Language reference and flag any matches found in code.

#### Reference Files

1. [Core Language](references/agent-script-core-language.md) — syntax,
   execution model, anti-patterns
2. [Design & Agent Spec](references/agent-design-and-spec-creation.md) —
   Agent Spec structure, flow control pattern recognition
3. [Topic Map Diagrams](references/agent-topic-map-diagrams.md) —
   Mermaid conventions for topic graph visualization
4. [Metadata & Lifecycle](references/agent-metadata-and-lifecycle.md) —
   directory conventions, bundle metadata
5. [Known Issues](references/known-issues.md) — only load when code
   contains unexplained workaround patterns

### Modify an Existing Agent

User wants to add, remove, or change topics, actions, instructions, or flow control on existing agent. May describe change in plain language ("add a billing topic") or reference specific Agent Script constructs.

#### Required Steps

Read [CLI for Agents](references/salesforce-cli-for-agents.md) for exact command syntax.

1. **Comprehend** — If no Agent Spec exists, reverse-engineer first by following "Comprehend an Existing Agent" workflow above.
2. **Update Agent Spec** — Read [Design & Agent Spec](references/agent-design-and-spec-creation.md) for flow control patterns and backing logic analysis. Modify Agent Spec to reflect intended changes. For new actions, always ask if you should scan for existing backing logic. Unless instructed otherwise, scan by reading `sfdx-project.json` to identify package directories, then search each for `@InvocableMethod` in `classes/`, `AutoLaunchedFlow` in `flows/`, and template metadata in `promptTemplates/`. Mark matches `EXISTS`; unmatched actions `NEEDS STUB`. **Always save updated Agent Spec as file.**
3. **STOP for user approval of updated Agent Spec.** Present to user. Ask for approval or feedback. **Do not proceed** without approval. Once approved, proceed without stopping unless a step fails.
4. **Edit code** — Read [Core Language](references/agent-script-core-language.md) for syntax and anti-patterns. Edit `.agent` file to implement approved changes.
5. **Validate compilation** —
   `sf agent validate authoring-bundle --json --api-name <Developer_Name>`
   If validation fails, read [Validation & Debugging](references/agent-validation-and-debugging.md) to diagnose and fix, then re-validate.
6. **Generate new backing logic** — For each new action marked NEEDS STUB:
   `sf template generate apex class --name <ClassName> --output-dir <PACKAGE_DIR>/main/default/classes`
   Replace class body with invocable pattern from [Design & Agent Spec](references/agent-design-and-spec-creation.md). ALWAYS deploy:
   `sf project deploy start --json --metadata ApexClass:<ClassName>`
   ALWAYS fix deploy errors BEFORE generating and deploying next stub. Skip if no new actions added.
7. **Validate behavior** — Read [Validation & Debugging](references/agent-validation-and-debugging.md) for preview workflow and session trace analysis.
   `sf agent preview start --json --use-live-actions --authoring-bundle <Developer_Name>`
   If actions query data, ground test utterances with:
   `sf data query --json -q "SELECT <Relevant_Fields> FROM <SObject> LIMIT 100"`
   Send test utterances with:
   `sf agent preview send --json --authoring-bundle <Developer_Name> --session-id <ID> -u "<message>"`
   Test changed paths first, then adjacent paths to catch regressions in existing behavior.
8. **Publish** — **DO NOT proceed until step 7 passes.** Publish validates metadata structure, not agent behavior. ALWAYS validate behavior before publishing. Every publish creates permanent version number.
   `sf agent publish authoring-bundle --json --api-name <Developer_Name>`
   If publish fails, follow troubleshooting checklist in [Metadata & Lifecycle](references/agent-metadata-and-lifecycle.md), Section 5 before retrying.
9. **Activate** — Makes new version available to users.
   `sf agent activate --json --api-name <Developer_Name>`
10. **Verify published agent** — Preview user-facing behavior AFTER activation with
    `sf agent preview start --json --api-name <Developer_Name>`
    Use `--api-name`, not `--authoring-bundle`.

#### Reference Files

1. [CLI for Agents](references/salesforce-cli-for-agents.md) — exact
   command syntax for validate, deploy, preview, publish, activate
2. [Core Language](references/agent-script-core-language.md) — syntax,
   anti-patterns
3. [Design & Agent Spec](references/agent-design-and-spec-creation.md) —
   Agent Spec updates, backing logic analysis
4. [Validation & Debugging](references/agent-validation-and-debugging.md) —
   compilation diagnosis, preview workflow, session trace analysis
5. [Known Issues](references/known-issues.md) — only load when errors
   persist after code fixes

### Diagnose Compilation Errors

User has Agent Script that won't compile. Errors surface from `sf agent validate` or `sf agent preview start`, or User describes symptoms like "I'm getting a validation error."

#### Required Steps

Read [CLI for Agents](references/salesforce-cli-for-agents.md) for exact command syntax.

1. **Reproduce error** — Run
   `sf agent validate authoring-bundle --json --api-name <Developer_Name>`
   to capture basic compile errors. If no errors, run
   `sf agent preview start --json --use-live-actions --authoring-bundle <Developer_Name>`
   to capture complex compile errors. If user provides specific error output, ALWAYS reproduce to confirm.
2. **Classify error** — Read [Validation & Debugging](references/agent-validation-and-debugging.md) for error taxonomy. Map each error message to root cause category.
3. **Locate fault** — Read [Core Language](references/agent-script-core-language.md) to understand correct syntax. Find specific line(s) in `.agent` file that cause each error.
4. **Fix code** — Apply targeted fixes. Check Anti-Patterns section in Core Language reference to ensure you're not introducing known bad pattern.
5. **Re-validate** — Run
   `sf agent validate authoring-bundle --json --api-name <Developer_Name>`
   then run
   `sf agent preview start --json --use-live-actions --authoring-bundle <Developer_Name>`
   Repeat steps 2–5 if errors persist.
6. **Explain fix** — Tell user what was wrong and what you changed. Explain root cause in terms of *Core Language* agent execution model.

#### Reference Files

1. [Core Language](references/agent-script-core-language.md) — syntax,
   block structure, anti-patterns
2. [Validation & Debugging](references/agent-validation-and-debugging.md) —
   error taxonomy, error-to-root-cause mapping
3. [Known Issues](references/known-issues.md) — only load when error
   doesn't match user code; may be a platform bug
4. [Production Gotchas](references/production-gotchas.md) — only load
   when error involves reserved keywords or lifecycle hook syntax

### Diagnose Behavioral Issues

Agent compiles, preview can start and `--use-live-actions`, but agent does not behave as expected. User describes symptoms like "the agent keeps going to the wrong topic" or "the action isn't being called." Fundamentally different from `validate` or `preview start` errors — code is valid but behavior is wrong.

#### Required Steps

Read [CLI for Agents](references/salesforce-cli-for-agents.md) for exact command syntax.

1. **Establish baseline** — Read Agent Spec. If no Agent Spec exists, follow *Comprehend an Existing Agent* workflow to reverse-engineer one, then continue.
2. **Form hypotheses** — Read [Core Language](references/agent-script-core-language.md) for execution model. Based on user's description, list candidate root causes. Think through: topic routing, gating conditions, action availability, instruction clarity, variable state, and transition timing.
3. **Reproduce in preview** — Read [Validation & Debugging](references/agent-validation-and-debugging.md) for preview workflow and session trace analysis. Start preview session:
   `sf agent preview start --json --use-live-actions --authoring-bundle <Developer_Name>`
   then send test messages covering EACH topic with `sf agent preview send`. One message is not enough — confirm behavior per topic before proceeding.
4. **Analyze session traces** — Examine trace output to confirm topic selection, action availability/execution, LLM reasoning, and where behavior diverges from Agent Spec. Do NOT skip this step — preview output alone is insufficient for diagnosis.
5. **Identify root cause** — Match trace evidence to hypotheses. Consult *Core Language reference and Gating Patterns* in [Design & Agent Spec](references/agent-design-and-spec-creation.md) reference to confirm absence of anti-patterns.
6. **Fix code** — Apply targeted fix. If fix involves flow control changes, update Agent Spec to match.
7. **Re-validate and re-preview** — Repeat steps 3–6 until behavior matches Agent Spec or you confirm a platform limitation. Run `validate authoring-bundle`, then `preview start --use-live-actions` to verify fix using same utterances. Then test adjacent paths that might be affected by your changes.
8. **Explain fix** — Tell user what was wrong and what you changed. Explain root cause in terms of *Core Language* agent execution model.

#### Reference Files

1. [Core Language](references/agent-script-core-language.md) — execution
   model, anti-patterns
2. [Design & Agent Spec](references/agent-design-and-spec-creation.md) —
   Agent Spec as behavioral baseline, gating patterns
3. [Validation & Debugging](references/agent-validation-and-debugging.md) —
   preview workflow, session trace analysis
4. [Known Issues](references/known-issues.md) — only load when behavior
   is wrong but code logic is correct

### Deploy, Publish, and Activate

User wants to take working agent from local development to running state in Salesforce org. Involves deploying `AiAuthoringBundle` and its dependencies, publishing to commit version, then activating to make it live.

#### Required Steps

Read [CLI for Agents](references/salesforce-cli-for-agents.md) for exact command syntax.

1. **Validate compilation** —
   `sf agent validate authoring-bundle --json --api-name <Developer_Name>`
   Do not proceed if validation fails.
2. **Deploy bundle and dependencies** — Read [Metadata & Lifecycle](references/agent-metadata-and-lifecycle.md) for dependency management and deploy commands. Deploy `AiAuthoringBundle` and all backing logic (Apex classes, Flows, Prompt Templates) and dependencies to org.
3. **Live preview** — Read [Validation & Debugging](references/agent-validation-and-debugging.md) for preview workflow and session trace analysis.
   `sf agent preview start --json --use-live-actions --authoring-bundle <Developer_Name>`
   then send test utterances with:
   `sf agent preview send --json --authoring-bundle <Developer_Name> --session-id <ID> -u "<message>"`
   Test key conversation paths to validate agent behavior when backed by live actions. **Do not proceed to Publish until preview passes.**
4. **Publish** — **Publish validates metadata structure, not agent behavior.** ALWAYS validate behavior with live preview BEFORE publishing. DO NOT publish as part of a dev/test inner loop. ONLY publish as the FINAL step prior to activating the agent and surfacing it to end users.
   `sf agent publish authoring-bundle --json --api-name <Developer_Name>`
   If publish fails, follow *Troubleshooting Publish Failures* in [Metadata & Lifecycle](references/agent-metadata-and-lifecycle.md) before retrying.
5. **Activate** — Makes new version available to users.
   `sf agent activate --json --api-name <Developer_Name>`
6. **Verify published agent** — Preview user-facing behavior AFTER activation with
    `sf agent preview start --json --api-name <Developer_Name>`
    Use `--api-name`, not `--authoring-bundle`.
7. **Configure end-user access** — ONLY for employee agents. Read [Agent Access Guide](references/agent-access-guide.md) to configure perms and assign access.

#### Reference Files

1. [CLI for Agents](references/salesforce-cli-for-agents.md) — exact
   command syntax for deploy, publish, activate, deactivate
2. [Validation & Debugging](references/agent-validation-and-debugging.md) —
   compilation validation, preview workflow
3. [Metadata & Lifecycle](references/agent-metadata-and-lifecycle.md) —
   dependency management, deploy commands; publish troubleshooting
4. [Agent Access Guide](references/agent-access-guide.md) — end-user
   access permissions, visibility troubleshooting
5. [Known Issues](references/known-issues.md) — only load when deploy
   hangs, publish fails, or activate fails unexpectedly

### Diagnose Production Issues

User's agent is published and active but experiencing issues not caught during preview. Includes credit overconsumption, token or size limit failures, loop guardrail interruptions, reserved keyword runtime errors, VS Code sync failures, or unexpected behavioral differences between preview and production.

#### Required Steps

Read [CLI for Agents](references/salesforce-cli-for-agents.md) for exact command syntax.

1. **Classify issue** — Determine whether this is billing/cost concern, runtime limit, naming conflict, tooling issue, or behavioral difference between preview and production.
2. **Check known production gotchas** — Read [Production Gotchas](references/production-gotchas.md) for credit consumption, token limits, loop guardrails, reserved keywords, lifecycle hooks, and VS Code workarounds.
3. **Compare preview vs production behavior** — If issue is behavioral, preview published agent with
   `sf agent preview start --json --api-name <Developer_Name>`
   (not `--authoring-bundle`). Compare against live-actions authoring bundle preview `--authoring-bundle <Developer_Name> --use-live-actions` to isolate preview-vs-production differences.
4. **Check known issues** — Read [Known Issues](references/known-issues.md) for platform bugs that may explain production-only failures.
5. **Fix and republish** — Apply fixes, validate, re-preview, publish, activate, verify. Follow Deploy, Publish, and Activate steps.
6. **Explain diagnosis** — Tell user what was happening and what you changed. Explain root cause.

#### Reference Files

1. [Production Gotchas](references/production-gotchas.md) — credit
   consumption, token limits, loop guardrails, reserved keywords,
   lifecycle hooks, VS Code workarounds
2. [CLI for Agents](references/salesforce-cli-for-agents.md) — command
   syntax for preview, publish, activate
3. [Validation & Debugging](references/agent-validation-and-debugging.md) —
   preview workflow, session trace analysis
4. [Known Issues](references/known-issues.md) — only load when issue may
   be a platform bug

### Delete or Rename an Agent

User wants to remove agent or change its name. Maintenance tasks complicated by `AiAuthoringBundle` versioning and published version dependencies.

#### Required Steps

Read [CLI for Agents](references/salesforce-cli-for-agents.md) for exact command syntax.

1. **Understand current state** — Read [Metadata & Lifecycle](references/agent-metadata-and-lifecycle.md) for versioning, delete mechanics, and rename mechanics. Identify whether agent has been published, how many versions exist, and whether it's currently active.
2. **Deactivate if active** —
   `sf agent deactivate --json --api-name <Developer_Name>`
   Active agent cannot be deleted or renamed.
3. **Execute operation** — For delete: follow delete mechanics in Metadata & Lifecycle reference. For rename: follow rename mechanics in same reference.
4. **Clean up orphans** — Check for and remove orphaned metadata: Bot, BotVersion, GenAiPlannerBundle, GenAiPlugin, GenAiFunction. Metadata & Lifecycle reference details what to look for.
5. **Validate** — Confirm operation completed cleanly. For rename, validate new bundle compiles and preview to confirm behavior.

#### Reference Files

1. [CLI for Agents](references/salesforce-cli-for-agents.md) — exact
   command syntax for delete, deactivate, retrieve
2. [Validation & Debugging](references/agent-validation-and-debugging.md) —
   compilation validation, preview workflow
3. [Metadata & Lifecycle](references/agent-metadata-and-lifecycle.md) —
   delete mechanics, rename mechanics, orphan cleanup

### Test an Agent

User wants to create automated tests for Agent Script agent. Involves writing `AiEvaluationDefinition` test specs in YAML format that define test scenarios, expected behaviors, and quality metrics.

#### Required Steps

Read [CLI for Agents](references/salesforce-cli-for-agents.md) for exact command syntax.

1. **Establish coverage baseline** — Read Agent Spec. If no Agent Spec exists, reverse-engineer first by following Comprehend steps. Map every topic, action, and flow control path to identify what needs test coverage.
2. **Design test scenarios** — For test design methodology, expectations, metrics, test spec YAML format, and templates, use **agentforce-testing** skill. That skill owns all testing content. For each coverage target, write one or more test scenarios: user utterance, expected topic routing, expected action invocations, and expected agent response. Include both happy paths and edge cases.
3. **Write test spec YAML** — Use template and reference files from **agentforce-testing** skill. Save to `specs/<Agent_API_Name>-testSpec.yaml` in SFDX project.
4. **Create test metadata** — Generate `AiEvaluationDefinition` from test spec using CLI.
5. **Deploy test** — Deploy `AiEvaluationDefinition` to org.
6. **Run tests** — Execute test run using CLI. Capture results.
7. **Analyze results** — Compare actual outcomes against expectations. For failures, identify whether issue is in agent code, backing logic, or test spec itself.
8. **Iterate** — Fix agent code or test spec as needed, redeploy, and re-run until coverage targets are met.

#### Reference Files

1. [CLI for Agents](references/salesforce-cli-for-agents.md) — exact
   command syntax for test create, test run, test results
2. [Core Language](references/agent-script-core-language.md) — agent
   structure for designing meaningful tests
3. [Design & Agent Spec](references/agent-design-and-spec-creation.md) —
   Agent Spec as test coverage baseline
4. **agentforce-testing** skill — test spec YAML format, expectations,
   metrics, test design methodology, and test spec template

## The Agent Spec

**Agent Spec** is the central artifact this skill produces and consumes. A structured design document representing agent's purpose, topic graph, actions with backing logic, variables, gating logic, and behavioral intent.

Agent Specs evolve with the agent. Sparse during agent creation (purpose, topics, directional notes). Fleshed out during agent build (flowchart, backing logic mapped, gating documented). Reverse-engineered when comprehending existing agents. Critical for advanced troubleshooting, providing reference to compare expected vs. actual behavior. During testing, test coverage maps against it.

Always produce or update Agent Spec as first step of any operation that changes or analyzes agent. It is consistent grounding to work from, and a durable artifact a developer can review.

Read [Design & Agent Spec](references/agent-design-and-spec-creation.md) for Agent Spec structure and production methodology.

## Assets

The `assets/` directory contains templates and examples. Read when you need a starting point or a concrete reference for artifacts and source files.

- **`assets/agent-spec-template.md`** — Agent Spec template with all sections and placeholder content. Copy to `<AgentName>-AgentSpec.md` in project directory, then fill in during design. Save Agent Spec as file — significant design artifact that benefits from proper rendering, especially Mermaid Topic Map diagram.

- **`assets/local-info-agent-annotated.agent`** — Complete annotated example based on Local Info Agent, showing all major Agent Script constructs in context with inline comments explaining why each construct is used. Read when you need concrete reference for how concepts compose into working agent, or as fallback when focused examples in reference files aren't sufficient.

- **`assets/template-single-topic.agent`** — Minimal agent with one topic. Copy and modify for simple agents.

- **`assets/template-multi-topic.agent`** — Minimal agent with multiple topics and transitions. Copy and modify for complex agents.

- **`assets/invocable-apex-template.cls`** — Reference for invocable Apex
  classes. Copy and modify when complex Apex backing logic is desired.

## Important Constraints

- **Use only Salesforce CLI and Salesforce org.** Do not reference or depend on other skills, MCP servers, or external tooling. All commands use `sf` (Salesforce CLI).

- **Only certain backing logic types are valid for actions.** For example, only invocable Apex (not arbitrary Apex classes) can back action. Similar constraints may apply to Flows and Prompt Templates. When wiring actions to backing logic, consult Design & Agent Spec reference file for valid types and stubbing methodology.

- **`sf agent generate test-spec` is not for agentic use.** It is interactive, REPL-style command designed for humans. When creating test specs, start from boilerplate template in assets instead.

## Common Issues Quick Reference

**`Internal Error, try again later` during publish:**
Invalid or missing `default_agent_user`. Re-run query from [Design & Agent Spec](references/agent-design-and-spec-creation.md), Section 3. Do not invent username.

**`Unable to access Salesforce Agent APIs...` during preview:**
`default_agent_user` lacks permissions. See [Agent User Setup & Permissions](references/agent-user-setup.md). Do NOT publish as fix — `--use-live-actions` does not require published agent.

**Permission error referencing different username than configured:**
Same fix as above — error references org's default running user, but root cause is Einstein Agent User permissions.

**Agent fails with permission error even though current topic's actions work:**
Planner validates ALL actions across ALL topics at startup. One missing permission fails entire agent.

**Apex action returns empty results in live preview but works in simulated:**
`WITH USER_MODE` + missing object permissions = silent failure (0 rows, no error). See [Agent User Setup & Permissions](references/agent-user-setup.md), Section 6.2.
