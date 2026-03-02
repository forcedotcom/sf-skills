---
name: agent-script-skill
description: "Use this skill when working with Salesforce Agent Script — the scripting language for authoring Agentforce agents using the Atlas Reasoning Engine. Triggers include: creating, modifying, or comprehending Agent Script agents; working with AiAuthoringBundle files or .agent files; designing topic graphs or flow control; producing or updating an Agent Spec; validating Agent Script or diagnosing compilation errors; previewing agents or debugging behavioral issues; deploying, publishing, activating, or deactivating agents; deleting or renaming agents; authoring AiEvaluationDefinition test specs or running agent tests. This skill teaches Agent Script from scratch — AI models have zero prior training data on this language. Do NOT use for Apex development, Flow building, Prompt Template authoring, Experience Cloud configuration, or general Salesforce CLI tasks unrelated to Agent Script."
---

# Agent Script Skill

## What This Skill Is For

Agent Script is Salesforce's scripting language for authoring next-generation AI agents that run on the Atlas Reasoning Engine. Introduced in 2025, it has zero training data in any AI model.

**⚠️CRITICAL:** Agent Script is NOT AppleScript, JavaScript, Python, or any other language. Do NOT confuse Agent Script syntax or semantics with any other language you have been trained on.

An Agent Script agent is defined by `AiAuthoringBundle` metadata — a directory containing a `.agent` file (topics, actions, instructions, flow control, config) and `bundle-meta.xml` file. The agent processes utterances by routing through topics, each with instructions and actions backed by Apex, Flows, or Prompt Templates.

## How to Use This Skill

This file identifies the user's task and directs you to reference files. All detailed knowledge lives in reference files. Identify intent from task descriptions below, read indicated reference files, then start work.

**CLI Convention**: All `sf` commands use `--json` as the FIRST flag for machine-readable output. See [CLI for Agents](references/salesforce-cli-for-agents.md) for exact syntax.

## Common Patterns

These patterns are referenced across multiple task domains below:

### Backing Logic Scan

When designing or modifying agents with new actions:
1. Ask user if you should scan for existing backing logic
2. If approved, read `sfdx-project.json` to identify package directories
3. Search each package: `classes/` for `@InvocableMethod`, `flows/` for `AutoLaunchedFlow`, `promptTemplates/` for templates
4. Mark matches as `EXISTS`, unmatched as `NEEDS STUB`

### Validation Pattern

1. **Compile**: `sf agent validate authoring-bundle --json --api-name <Developer_Name>`
   - If fails, read [Validation & Debugging](references/agent-validation-and-debugging.md), fix, re-validate
2. **Behavior**: `sf agent preview start --json --authoring-bundle <Developer_Name>` then `sf agent preview send --json --authoring-bundle <Developer_Name> --session-id <ID> -u "<message>"`
   - Do NOT use bare `sf agent preview` (interactive REPL)
   - **Once published**: Use `--api-name <Developer_Name>` instead of `--authoring-bundle` for more accurate results

### Stub and Deploy Pattern

For each action marked NEEDS STUB:
1. Generate: `sf generate apex class --name <ClassName> --output-dir <PACKAGE_DIR>/main/default/classes`
2. Implement `@InvocableMethod` pattern from Design & Agent Spec reference
3. Deploy: `sf project deploy start --json --metadata ApexClass:<ClassName>`

---

## Task Domains

Follow Required Steps verbatim, in order. Do not substitute your own plan.

### Create an Agent

User wants to build a new agent, typically describing purpose/topics/actions in plain language.

#### Required Steps

1. **Design** — Read [Design & Agent Spec](references/agent-design-and-spec-creation.md). Draft Agent Spec. Apply **Backing Logic Scan** pattern. **Save Agent Spec as file** before requesting user approval. Do not write Agent Script until approved.
2. **Generate**: `sf agent generate authoring-bundle --json --no-spec --name "<Label>" --api-name <Developer_Name>`
3. **Write code** — Read [Core Language](references/agent-script-core-language.md). Edit `.agent` file. Do not create files manually.
4. **Validate** — Apply **Validation Pattern** (compile + behavior)
5. **Stub and Deploy** — Apply **Stub and Deploy Pattern**
6. **Publish**: `sf agent publish authoring-bundle --json --api-name <Developer_Name>`
7. **Activate**: `sf agent activate --json --api-name <Developer_Name>`

#### References

- [CLI for Agents](references/salesforce-cli-for-agents.md)
- [Core Language](references/agent-script-core-language.md) — execution model, syntax, anti-patterns
- [Design & Agent Spec](references/agent-design-and-spec-creation.md) — topic graph, Agent Spec, backing logic
- [Topic Map Diagrams](references/agent-topic-map-diagrams.md) — Mermaid conventions
- [Metadata & Lifecycle](references/agent-metadata-and-lifecycle.md) — Section 3 (directory structure)
- [Validation & Debugging](references/agent-validation-and-debugging.md) — validate, preview

---

### Comprehend an Existing Agent

User wants to understand an agent they didn't write or need to revisit.

#### Required Steps

1. **Locate** — Read `sfdx-project.json` for package directories. Find `AiAuthoringBundle` directory. Read `.agent` and `bundle-meta.xml`.
2. **Read code** — Read [Core Language](references/agent-script-core-language.md). Parse `.agent` file.
3. **Map backing logic** — Locate implementations (Apex/Flow/Prompt Template). Note input/output contracts.
4. **Reverse-engineer Agent Spec** — Read [Design & Agent Spec](references/agent-design-and-spec-creation.md). Produce and save Agent Spec file.
5. **Topic Map** — Read [Topic Map Diagrams](references/agent-topic-map-diagrams.md). Generate Mermaid flowchart.
6. **Annotate** — Ask if user wants source annotations. If yes, add inline comments.
7. **Present** — Share Agent Spec, Topic Map, annotated source. Flag anti-patterns from Core Language reference.

#### References

- [Core Language](references/agent-script-core-language.md) — syntax, execution model, anti-patterns
- [Design & Agent Spec](references/agent-design-and-spec-creation.md) — Agent Spec structure
- [Topic Map Diagrams](references/agent-topic-map-diagrams.md) — Mermaid conventions
- [Metadata & Lifecycle](references/agent-metadata-and-lifecycle.md) — directory conventions

---

### Modify an Existing Agent

User wants to add/remove/change topics, actions, instructions, or flow control.

#### Required Steps

1. **Comprehend** — If no Agent Spec exists, follow "Comprehend an Existing Agent" steps first.
2. **Update Agent Spec** — Read [Design & Agent Spec](references/agent-design-and-spec-creation.md). Modify Agent Spec for intended changes. For new actions, apply **Backing Logic Scan** pattern. **Save updated Agent Spec** before requesting user approval. Do not write Agent Script until approved.
3. **Edit code** — Read [Core Language](references/agent-script-core-language.md). Edit `.agent` file.
4. **Validate** — Apply **Validation Pattern**
5. **Stub and Deploy** — If new actions, apply **Stub and Deploy Pattern**
6. **Publish**: `sf agent publish authoring-bundle --json --api-name <Developer_Name>`
7. **Activate** (if was active): `sf agent activate --json --api-name <Developer_Name>`

#### References

- [CLI for Agents](references/salesforce-cli-for-agents.md)
- [Core Language](references/agent-script-core-language.md) — syntax, anti-patterns
- [Design & Agent Spec](references/agent-design-and-spec-creation.md) — Agent Spec updates, backing logic
- [Validation & Debugging](references/agent-validation-and-debugging.md) — validate, preview

---

### Diagnose Compilation Errors

User has Agent Script that won't compile.

#### Required Steps

1. **Reproduce**: `sf agent validate authoring-bundle --json --api-name <Developer_Name>`
2. **Classify** — Read [Validation & Debugging](references/agent-validation-and-debugging.md) for error taxonomy. Map errors to root causes.
3. **Locate fault** — Read [Core Language](references/agent-script-core-language.md). Find offending lines.
4. **Fix** — Apply targeted fixes. Check Anti-Patterns section to avoid introducing bad patterns.
5. **Re-validate** — Repeat steps 2–5 until passes.
6. **Explain** — Tell user what was wrong, what changed, root cause in terms of execution model.

#### References

- [Core Language](references/agent-script-core-language.md) — syntax, anti-patterns
- [Validation & Debugging](references/agent-validation-and-debugging.md) — error taxonomy

---

### Diagnose Behavioral Issues

Agent compiles but doesn't behave as expected (e.g., wrong topic routing, actions not called).

#### Required Steps

1. **Baseline** — Read Agent Spec. If none exists, reverse-engineer one (Comprehend steps).
2. **Hypotheses** — Read [Core Language](references/agent-script-core-language.md) for execution model. List candidate root causes: topic routing, gating, action availability, instructions, variable state, transition timing.
3. **Reproduce** — Read [Validation & Debugging](references/agent-validation-and-debugging.md). Start preview, send test messages.
4. **Analyze traces** — Examine trace output: topic selected, actions available, LLM reasoning, divergence from Agent Spec.
5. **Root cause** — Match trace evidence to hypothesis. Consult Anti-Patterns (Core Language) and Gating Patterns ([Design & Agent Spec](references/agent-design-and-spec-creation.md)).
6. **Fix** — Apply targeted fix. Update Agent Spec if flow control changed.
7. **Re-validate** — Apply **Validation Pattern**. Test changed paths and adjacent paths.
8. **Explain** — Tell user what happened, what changed, root cause in terms of execution model.

#### References

- [Core Language](references/agent-script-core-language.md) — execution model, anti-patterns
- [Design & Agent Spec](references/agent-design-and-spec-creation.md) — Agent Spec baseline, gating patterns
- [Validation & Debugging](references/agent-validation-and-debugging.md) — preview, trace analysis

---

### Deploy, Publish, and Activate

User wants to take working agent from local development to running state in org.

#### Required Steps

1. **Validate**: `sf agent validate authoring-bundle --json --api-name <Developer_Name>` — do not proceed if fails.
2. **Deploy** — Read [Metadata & Lifecycle](references/agent-metadata-and-lifecycle.md). Deploy `AiAuthoringBundle` and dependencies (Apex/Flow/Prompt Templates).
3. **Preview** — Read [Validation & Debugging](references/agent-validation-and-debugging.md). Test key conversation paths. **Do not publish until preview passes.**
4. **Publish**: `sf agent publish authoring-bundle --json --api-name <Developer_Name>` — **every publish creates permanent version number**
5. **Activate**: `sf agent activate --json --api-name <Developer_Name>`
6. **Verify** — Confirm agent is live and reachable (Experience Site, API, etc.)

#### References

- [CLI for Agents](references/salesforce-cli-for-agents.md)
- [Validation & Debugging](references/agent-validation-and-debugging.md) — validate, preview
- [Metadata & Lifecycle](references/agent-metadata-and-lifecycle.md) — deploy, dependencies

---

### Delete or Rename an Agent

User wants to remove or rename an agent.

#### Required Steps

1. **Understand state** — Read [Metadata & Lifecycle](references/agent-metadata-and-lifecycle.md) for versioning, delete/rename mechanics. Identify if published, version count, activation status.
2. **Deactivate** (if active): `sf agent deactivate --json --api-name <Developer_Name>`
3. **Execute** — Follow delete or rename mechanics from Metadata & Lifecycle reference.
4. **Clean up orphans** — Remove orphaned metadata (Bot, BotVersion, GenAiPlannerBundle, GenAiPlugin, GenAiFunction). See Metadata & Lifecycle reference.
5. **Validate** — Confirm operation completed. For rename, validate new bundle compiles and preview behavior.

#### References

- [CLI for Agents](references/salesforce-cli-for-agents.md)
- [Validation & Debugging](references/agent-validation-and-debugging.md) — validate, preview
- [Metadata & Lifecycle](references/agent-metadata-and-lifecycle.md) — delete, rename, orphan cleanup

---

### Test an Agent

User wants automated tests (`AiEvaluationDefinition` test specs in YAML).

#### Required Steps

1. **Coverage baseline** — Read Agent Spec. If none exists, reverse-engineer (Comprehend steps). Map every topic, action, flow control path.
2. **Design scenarios** — Read [Test Authoring](references/agent-test-authoring.md). For each coverage target, write scenarios: utterance, expected topic routing, expected action invocations, expected response. Include happy paths and edge cases.
3. **Write YAML** — Start from `assets/template-testSpec.yaml`. Follow Test Authoring reference. Save to `specs/<Agent_API_Name>-testSpec.yaml`.
4. **Create metadata** — Generate `AiEvaluationDefinition` from spec via CLI.
5. **Deploy test** — Deploy `AiEvaluationDefinition` to org.
6. **Run tests** — Execute test run via CLI. Capture results.
7. **Analyze** — Compare actual vs. expected. Identify issue source: agent code, backing logic, or test spec.
8. **Iterate** — Fix as needed, redeploy, re-run until coverage met.

#### References

- [CLI for Agents](references/salesforce-cli-for-agents.md) — test create, run, results
- [Core Language](references/agent-script-core-language.md) — agent structure for test design
- [Design & Agent Spec](references/agent-design-and-spec-creation.md) — Agent Spec as coverage baseline
- [Test Authoring](references/agent-test-authoring.md) — YAML format, expectations, metrics
- [assets/template-testSpec.yaml](assets/template-testSpec.yaml) — template

---

## The Agent Spec

The **Agent Spec** is the central artifact this skill produces and consumes. It's a structured design document representing agent purpose, topic graph, actions with backing logic, variables, gating logic, behavioral intent.

The Agent Spec evolves: sparse at creation (purpose, topics), filled during build (flowchart, backing logic, gating), reverse-engineered during comprehension, reference for diagnosis, coverage map for testing.

Always produce or update Agent Spec as first step of operations that change or analyze agents. It's the ground truth you work from and the artifact the developer reviews.

For structure and methodology, read [Design & Agent Spec](references/agent-design-and-spec-creation.md).

---

## Assets

Templates and examples in `assets/`:

- **`agent-spec-template.md`** — Template with all sections. Copy to `<AgentName>-AgentSpec.md`, fill during design. Save as file for proper rendering (Mermaid diagrams).
- **`template.agent`** — Universal agent template supporting both single-topic and multi-topic agents. Shows all major constructs with inline comments. For single-topic agents, keep only the 'main' topic and remove others. For multi-topic agents, add, remove, or rename topics as needed.
- **`template-testSpec.yaml`** — Test spec template with placeholders and field explanations. Copy to `specs/<Agent_API_Name>-testSpec.yaml`, customize.

---

## Important Constraints

- **Use only Salesforce CLI and Salesforce org.** No other skills, MCP servers, external tooling. All commands use `sf` (Salesforce CLI) with `--json` flag.
- **Only certain backing logic types are valid.** E.g., only invocable Apex (not arbitrary classes) can back actions. Consult Design & Agent Spec reference for valid types and stubbing.
- **`sf agent generate test-spec` is not for agentic use.** Interactive REPL-style for humans. Use `assets/template-testSpec.yaml` instead.
