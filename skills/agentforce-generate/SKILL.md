---
name: agentforce-generate
description: "Build, modify, optimize, debug, and deploy agents with Agentforce Agent Script. TRIGGER when: user creates, modifies, optimizes, or asks about .agent files or aiAuthoringBundle metadata; changes agent behavior, responses, or conversation logic; designs agent actions, tools, subagents, or flow control; writes or reviews an Agent Spec; wants to optimize, improve, or refactor an agent; previews, debugs, deploys, publishes, or tests agents; uses Agent Script CLI commands (sf agent generate/preview/publish/test); registers/creates/lists/updates/deletes MCP servers, whitelists/approves MCP tools, fetches MCP assets, or configures MCP authentication (sf agent mcp). DO NOT TRIGGER when: Apex development, Flow building, Prompt Template authoring, Experience Cloud configuration, or general Salesforce CLI tasks unrelated to Agent Script."
metadata:
  version: "0.11"
  minApiVersion: "66.0"
  relatedSkills:
    - "agentforce-observe"
    - "agentforce-test"
    - "automation-flow-generate"
    - "integration-connectivity-generate"
    - "platform-apex-generate"
    - "platform-metadata-deploy"
  cliTools:
    - tool: ["curl"]
      semver: ">=7.0.0"
    - tool: ["jq"]
      semver: ">=1.6.0"
    - tool: ["npm"]
      semver: ">=9.0.0"
    - tool: ["python3"]
      semver: ">=3.10.0"
    - tool: ["sf"]
      semver: ">=2.139.6"
---

# Agent Script Skill

## What This Skill Is For

This skill is for developing Agentforce agents, primarily with Agent Script, Salesforce's scripting language for AI agents.

Org-backed workflows require an Agentforce license, API v66.0 or later, and an
Einstein Agent User. Static authoring and review can proceed without org access.

**CRITICAL:** Agent Script is NOT AppleScript, JavaScript, Python, or any other
language. Do NOT confuse Agent Script syntax or semantics with any other
language you have been trained on.

Agent Script agents are defined by `AiAuthoringBundle` metadata: a `.agent` file (agent behavior) plus `bundle-meta.xml` (bundle metadata). Actions can be implemented with invocable Apex, autolaunched Flows, Prompt Templates, and other supported types.

This skill covers the full Agent Script lifecycle: designing agents,
writing Agent Script code, validating and debugging, deploying and
publishing, and testing.

## How to Use This Skill

This file maps user intent to task domains and relevant reference files in `references/`. Treat this file as the execution router for end-to-end agent development, and use references for deep detail.

Identify user intent from task descriptions. Read only the reference explicitly
required by the active step or needed for the current decision. Every
**Reference Files** section is a lookup index, not a preload list; do not load
files for later or inapplicable steps.

## Rules That Always Apply

1. **Always `--json`.** ALWAYS include `--json` on EVERY `sf` CLI command. Do NOT pipe CLI output through `jq` or `2>/dev/null`. Read the full JSON response directly — LLMs parse JSON natively.

2. **Verify target org.** Before any org interaction, run `sf config get target-org --json` to confirm a target org is set. If none configured, ask the user to set one with `sf config set target-org <alias>`.

3. **Diagnose before you fix.** When validating/debugging agent behavior,
   ALWAYS `--use-live-actions` to preview authoring bundles. Send utterances
   then read resulting session traces to ground your understanding of the
   agent's behavior. Trace files reveal subagent selection, action I/O, and
   LLM reasoning. DO NOT modify `.agent` files or action implementations without
   this grounding. See [Validation & Debugging](references/agent-validation-and-debugging.md)
   for trace file locations and diagnostic patterns.

4. **Spec approval is a hard gate.** Never proceed past Agent Spec
   creation without explicit user approval.

5. **Don't stall.** After a step completes successfully, announce the
   next step and start it. Do not wait for the user to say "what's next"
   or "ok, continue." The only checkpoints that require explicit user
   approval are: (a) Agent Spec approval, (b) the pre-Publish CHECKPOINT,
   (c) any A/B branch the skill explicitly surfaces (e.g., Data Cloud
   not provisioned during ADL setup). Long-running async work like ADL
   indexing should run in the background while the skill continues with
   work that doesn't depend on the result.

6. **Draft-first lifecycle.** During normal authoring, stay in draft iteration:
   edit `.agent` + action implementations, validate, deploy, and preview as many
   times as needed. Do NOT publish/activate by default. Publish + activate are
   explicit release actions that require the user to confirm they are ready to
   commit the current draft to metadata and expose it to end users.

7. **Start with one execution block and no mutable state.** A focused agent puts
   reasoning and actions directly in `start_agent`. Add a subagent only for a
   real objective, instruction, action, authority, or escalation boundary. Add
   persistent state only for a named deterministic consumer and give it a
   complete lifecycle. Ordinary continuity stays in surviving history. Apply
   the concrete checks in [The Zen of AgentScript](references/zen-of-agentscript.md)
   and [Posture & Determinism](references/posture-and-determinism.md).

8. **Use supported control flow.** Use the canonical conditional forms and
   never generate a nested `if`, which Agentforce lint rejects. See
   [Conditional Control Flow Syntax](references/agent-script-core-language.md#conditional-control-flow-syntax),
   then run full bundle validation.

9. **Action implementation is a user decision.** During planning/spec work,
   default new actions to `NEEDS STUB` placeholders. Always ask the user whether
   they want to scan org/project for existing implementations and/or generate
   new Apex/Flow/Prompt implementations before taking either path.

10. **Give each reachable branch one next outcome.** Choose exactly one primary
    outcome: answer, ask, invoke an action, transition, refuse, or escalate.
    The compiler selects a subagent `system.instructions` override instead of
    the global value, and the current runtime assembles effective system and
    resolved reasoning text for the model. Keep authoring constructs out of
    model-facing text. See
    [Instruction Resolution](references/instruction-resolution.md).

11. **Use portable structural indentation.** Generate new `.agent` files with
    4 spaces per level. Preserve a consistently indented legacy file during a
    surgical edit, or normalize the whole file as a separate validated change.

## Task Domains

Every task domain below has **Required Steps**. Follow verbatim, in order. The default path is: design -> draft implementation loop -> validation/preview loop -> explicit user-approved release.

### Create an Agent

User wants to build new agent from scratch. ALWAYS use Agent Script. Work with User to understand the agent's purpose, subagents, and actions using plain language without Salesforce-specific terminology.

#### Required Steps

Before running an `sf` command, read only the applicable command section in
[CLI for Agents](references/salesforce-cli-for-agents.md). Do not preload the
CLI reference during design-only work.

1. **Design** — Read [Design & Agent Spec](references/agent-design-and-spec-creation.md) to draft an Agent Spec. Default all new actions to `NEEDS STUB` placeholders during planning. Ask the user which implementation path they want before implementation work:
   - Path A: Keep placeholders only (no implementation now)
   - Path B: Scan for existing actions to reuse
   - Path C: Generate new actions
   Only run scans (reading `sfdx-project.json`, searching `@InvocableMethod`, `AutoLaunchedFlow`, prompt templates, external service registrations, standard invocable actions, and custom objects) if the user explicitly chooses Path B or C.
   **If the agent's purpose involves answering from documents** (e.g., "answer customer questions from our product manual", "respond based on a policy guide", "FAQ from a PDF"), ask the user: *"Will this agent answer questions from a document corpus (PDF/DOCX/TXT)? If so, what file path?"* Capture the path in the Spec under a **"Knowledge Grounding"** section. Asking now — during requirements capture — is critical: ADL indexing takes minutes, so we want the file path captured pre-Spec-approval and provisioning kicked off as early as possible.
   **If the agent will handle voice/telephony** (e.g., "phone agent", "voice bot", "IVR replacement", "call center agent"), confirm it's a voice agent and capture a **"Voice Configuration"** section in the Spec. **Do not ask the user for a voice_id** — there is no reliable way to enumerate voice IDs and tuning values from the CLI. Always start with the platform default voice (`UgBBYS2sOqTuMpoF3BR0` — "Mark", en_US; `outbound_speed: 1`, `outbound_stability: 0.65`, `outbound_similarity: 0.75`) and tell the user they can customize the voice later in the Agent Builder UI (open the agent → **Connections → Voice**, click **Continue** to pick a different voice and tune speed/stability). See [Voice Modality Reference](references/voice-modality-reference.md) for the `modality voice:` block syntax and voice-specific authoring guidance.
   **Voice service agents are almost always knowledge-backed** (callers ask FAQ/policy/troubleshooting questions). When you detect a voice agent, proactively ask the Knowledge Grounding question above — do not wait for the user to mention documents. This pairing (voice + knowledge grounding) is the Project Codey "Steel Thread 2" shape, and grounding on an ADL/Salesforce Knowledge corpus is what keeps a voice agent from hallucinating spoken answers. If the user has a document corpus, capture the file path and provision the ADL as usual; the `assets/agents/voice-knowledge-grounded.agent` template shows the combined wiring.
   **Always save Agent Spec as file.**
2. **STOP for user approval of Agent Spec.** Present to user (including the Knowledge Grounding section if present). Ask for approval or feedback. **Do not proceed** without approval. Once approved, proceed without stopping unless a step fails.
3. **Validate environment prerequisites** — Read [Design & Agent Spec](references/agent-design-and-spec-creation.md), Section 3 (Environment Prerequisites). Based on agent type from design, validate org environment:
   - **Employee agent**: Confirm the file normally omits `access.default_agent_user`, `connection messaging:`, and MessagingSession linked variables. Remove them if present. **Exception:** If the agent has a `knowledge:` block (uses `AnswerQuestionsWithKnowledge`), `access.default_agent_user` IS required even for employee agents — the platform treats knowledge-grounded agents as requiring an Einstein Agent User context at runtime. Query for the agent user and include it. See [Examples](references/examples.md) for a complete employee agent example.
   - **Service agent**: Query org for Einstein Agent User. If one exists, confirm username with user. If none, guide user through creation. See [CLI for Agents](references/salesforce-cli-for-agents.md), Section 12 for creation steps and [Agent User Setup](references/agent-user-setup.md) for required permissions.
   **3b. Kick off ADL provisioning (only if the Spec has a Knowledge Grounding section).** Read [Data Library Reference](references/data-library-reference.md). Run the Step 0 preflight: `SELECT COUNT() FROM DataKnowledgeSpace` (DC provisioned check), then `sf agent adl list` (ADL service health check). If DC is not provisioned, present the A/B choice from that reference. If DC is provisioned but the ADL service returns `400 INTERNAL_ERROR`, surface the "DC up, ADL broken" path and skip grounding for this run. If both checks pass, run `sf agent adl create` (reference Step 1) to capture `libraryId`. Compute `rag_feature_config_id = "ARFPC_<libraryId>"` from the `libraryId` alone — that's enough to author the bundle. Then start the upload + indexing flow (reference Steps 2–6) **in the background** while authoring continues. Per Rule 5, do not block on async indexing; `retrieverId` is only needed for runtime queries (gated in Step 8). Also kick off the Data Cloud permset assignment for the agent user — see [Agent User Setup](references/agent-user-setup.md), Step 3b for the discovery-then-assign procedure, which now ends with Step 3b.5 pinned post-assignment verification (against the resolved running-user and Einstein Agent User IDs) so callers can treat "Step 3b passed" as an authoritative Data Cloud grounding gate without re-running inline SOQL.
   **Do not proceed to code generation until environment is validated** (ADL provisioning may continue running in background).
4. **Generate authoring bundle** —
   `sf agent generate authoring-bundle --json --no-spec --name "<Label>" --api-name <Developer_Name>`
5. **Write code** — Read [Core Language](references/agent-script-core-language.md) for syntax, block structure, and anti-patterns. Read [Instruction Resolution](references/instruction-resolution.md) for instruction patterns, recommended instruction order, and anti-patterns (especially Anti-Pattern 7: prose-based conditional logic). Edit generated `.agent` file using reference files and templates. Do not create `.agent` or `bundle-meta.xml` files manually. If Step 3b produced a `libraryId`, include the top-level `knowledge:` block and the `AnswerQuestionsWithKnowledge` action wiring per [Data Library Reference](references/data-library-reference.md), section "Wiring the ADL into Agent Script". The template at `assets/agents/knowledge-grounded.agent` is a copy-modify starting point. **If the Spec has a Voice Configuration section**, include the `modality voice:` block (using the default `voice_id` and tuning values) and `language:` block per [Voice Modality Reference](references/voice-modality-reference.md). Keep the standard `agent_type` (e.g. `AgentforceServiceAgent`) — do NOT set an `Atlas__VoiceAgent` template in the bundle; that is a runtime planner_type, not an authored field. Also add the `VoiceCallId: linked string` variable bound to `@VoiceCall.Id` and add `connection customer_web_client:` (ECv2 — the voice-capable surface) with `adaptive_response_allowed: True`. Keep the `modality voice:` block minimal (voice_id + speed/stability/similarity); advanced settings (filler-word detection, speak-up, endpointing) are optional — add only if the Spec calls for them. `connection messaging:` is additive — include it only if the agent escalates to a human (`@utils.escalate`). Write concise voice instructions with the high-value guards: read back critical data (IDs/amounts/dates) before acting, and never read out URLs/citations/visual formatting. Also add the spoken-delivery instruction rules from [Voice Modality Reference](references/voice-modality-reference.md) "Instructions for Voice Agents" — ack/filler phrases before slow actions, spoken-form numbers, ASR repair prompts, and empty-result fallbacks. When wiring actions into a voice agent, apply the voice-safe action rules in [actions-reference.md](references/actions-reference.md) "Voice-Safe Action Authoring" (plain-English descriptions, speakable parameter names, enums, lookup-step for internal IDs, voice-friendly error shapes) and check the actions against [voice-latency-heuristics.md](references/voice-latency-heuristics.md) — flag (don't silently rewrite) sync writes, bulky retrieval, and chained callouts on the live-call path. The template at `assets/agents/voice-service-agent.agent` is a copy-modify starting point. **If the Spec has both a Voice Configuration and a Knowledge Grounding section**, start from `assets/agents/voice-knowledge-grounded.agent` instead — it combines `modality voice:`, the voice wiring, and the `knowledge:` block + `AnswerQuestionsWithKnowledge` action with spoken-answer anti-hallucination guards.
6. **Validate compilation** —
   `sf agent validate authoring-bundle --json --api-name <Developer_Name>`
   If validation fails, read [Validation & Debugging](references/agent-validation-and-debugging.md) to diagnose and fix, then re-validate. ALWAYS fix syntax and structural errors before generating action implementations.
7. **Generate action implementations (explicit user-requested path only)** — Only run this step if the user explicitly asked to generate new implementations (Path C in Step 1). For each action marked NEEDS STUB:
   `sf template generate apex class --name <ClassName> --output-dir <PACKAGE_DIR>/main/default/classes`
   Replace class body with invocable pattern from [Design & Agent Spec](references/agent-design-and-spec-creation.md). ALWAYS deploy:
   `sf project deploy start --json --metadata ApexClass:<ClassName>`
   ALWAYS fix deploy errors BEFORE generating and deploying next stub.
8. **Validate behavior** — Read [Validation & Debugging](references/agent-validation-and-debugging.md) for preview workflow and session trace analysis.
   **If Step 3b provisioned an ADL**, before sending any grounded test utterances confirm the library is queryable: run `sf agent adl get -i $LIBRARY_ID` and check that `retrieverId` is present ([Data Library Reference](references/data-library-reference.md), Step 6). If still null, wait and re-poll — do not preview yet, the agent will return empty `knowledgeSummary` and the anti-hallucination guard will refuse on every utterance.
   `sf agent preview start --json --use-live-actions --authoring-bundle <Developer_Name>`
   If actions query data, ground test utterances with:
   `sf data query --json -q "SELECT <Relevant_Fields> FROM <SObject> LIMIT 100"`
   Send test utterances with:
   `sf agent preview send --json --authoring-bundle <Developer_Name> --session-id <ID> -u "<message>"`
   **Smoke testing requirements** (see [Validation & Debugging](references/agent-validation-and-debugging.md), Utterance Derivation):
   - Test ALL routing branches, not just the happy path. Multiple phrasings per branch.
   - Use realistic utterances — write what a human would actually type, not keywords.
   - After EVERY utterance, read the trace to confirm actions actually fired (`FunctionStep`). Do not trust the agent's text response alone — agents can claim they performed actions without calling them.
   - Evaluate against the Agent Spec like a human tester: check conversation flow, instruction adherence, unnecessary repetition, and response quality. If the spec says "confirm once" and the agent confirms twice, that's a bug — fix it.
   If behavior diverges from the Agent Spec, fix the `.agent` file and re-preview. For complex issues, switch to **Diagnose Behavioral Issues** workflow. Return AFTER correcting issues.
   **CHECKPOINT — Stay in draft iteration unless user explicitly asks to release.**
   **If user requests release, do NOT proceed to Publish unless ALL are true:**
   - `validate authoring-bundle` passes with zero errors
   - Live preview (`--use-live-actions`) tested with realistic utterances covering all routing branches
   - Traces confirm correct subagent routing, action invocation (`FunctionStep` present), and spec-compliant behavior
   - User explicitly approves deployment
   - **If the agent has a `knowledge:` block**: the Einstein Agent User has a Data Cloud permset/PSL assigned. Verify both:
     ```bash
     sf data query --json -q "SELECT PermissionSet.Name FROM PermissionSetAssignment WHERE Assignee.Username='<agent_user>'"
     sf data query --json -q "SELECT PermissionSetLicense.DeveloperName FROM PermissionSetLicenseAssign WHERE Assignee.Username='<agent_user>'"
     ```
     One of `GenieDataPlatformStarterPsl`, `GenieUserEnhancedSecurity`, `DataCloudUser`, or `DataCloudArchitect` must appear in the combined results. If none does, run [Agent User Setup, Step 3b](references/agent-user-setup.md) discovery-then-assign and re-verify before proceeding. If a Data Cloud permset is assigned but a smoke-test grounded query returns empty `knowledgeSummary`, the **Data Space scope** also needs to be granted on that permset — UI-only, see [Agent User Setup, Step 3b.4](references/agent-user-setup.md).
9. **Publish (explicit release step)** — Only after the user confirms they are ready to commit this draft to metadata. Publish validates metadata structure, not agent behavior. Every publish creates permanent version number.
   `sf agent publish authoring-bundle --json --api-name <Developer_Name>`
   If publish fails, follow troubleshooting checklist in [Metadata & Lifecycle](references/agent-metadata-and-lifecycle.md), Section 5 before retrying.
10. **Activate (explicit release step)** — Makes new version available to users after publish.
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
   subagent graph design, flow control patterns, Agent Spec production,
   action implementation analysis; Section 3 for environment prerequisites
4. [Subagent Map Diagrams](references/agent-subagent-map-diagrams.md) —
   Mermaid diagram conventions for visualizing the agent's subagent graph
5. [Posture & Determinism](references/posture-and-determinism.md) —
   default agentic posture, deterministic controls with cause
6. [Agent User Setup & Permissions](references/agent-user-setup.md) —
   permission set assignment, object permissions, cross-subagent validation
7. [Metadata & Lifecycle](references/agent-metadata-and-lifecycle.md) —
   directory structure, bundle metadata; publish troubleshooting
8. [Validation & Debugging](references/agent-validation-and-debugging.md) —
   validate the agent compiles, preview to confirm behavior
9. [Agent Access Guide](references/agent-access-guide.md) — end-user
   access permissions, visibility troubleshooting
10. [Known Issues](references/known-issues.md) — only load when errors
   persist after code fixes
11. [Patterns by Requirement](references/patterns-by-requirement.md) — scenario-to-pattern mapping for architecture and flow choices
12. [Architecture Patterns](references/architecture-patterns.md) — router-first mechanics, verification gates, workflow-local linear patterns
13. [Complex Data Types](references/complex-data-types.md) — type mapping decision tree
14. [Safety Review](references/safety-review-reference.md) — 7-category safety review
15. [Discover Reference](references/discover-reference.md) — target discovery CLI
16. [Scaffold Reference](references/scaffold-reference.md) — stub generation CLI
17. [Deploy Reference](references/deploy-reference.md) — deployment lifecycle, error recovery
18. [Data Library Reference](references/data-library-reference.md) — provision a SFDRIVE Agentforce Data Library and wire it into the `.agent` via the `knowledge:` block + `AnswerQuestionsWithKnowledge` action

### Comprehend an Existing Agent

User wants to understand Agent Script agent they didn't write or need to revisit. May point to `AiAuthoringBundle` directory or ask "what does this agent do?" or "I need to fix this agent but I don't understand how it works.".

#### Required Steps

1. **Locate agent** — Read `sfdx-project.json` to identify package directories. Find `AiAuthoringBundle` directory within them. Read `.agent` file and `bundle-meta.xml`.
2. **Read code** — Read [Core Language](references/agent-script-core-language.md) for syntax and execution model BEFORE parsing `.agent` file.
3. **Map action implementations** — For each action with `target`, locate implementation (Apex class, Flow, Prompt Template) in project. Note input/output contracts.
4. **Reverse-engineer Agent Spec** — Read [Design & Agent Spec](references/agent-design-and-spec-creation.md) for Agent Spec structure. Produce Agent Spec from code and save as file.
5. **Produce Subagent Map diagram** — Read [Subagent Map Diagrams](references/agent-subagent-map-diagrams.md) for Mermaid conventions. Generate flowchart of subagent graph showing transitions, gates, and action associations.
6. **Annotate source** — Ask if user wants Agent Script source annotated with explanations. If requested, add inline comments to `.agent` file explaining flow control decisions, gating rationale, and subagent relationships.
7. **Present to user** — Share Agent Spec, Subagent Map, and annotated source if produced. Check Anti-Patterns section in Core Language reference and flag any matches found in code.

#### Reference Files

1. [Core Language](references/agent-script-core-language.md) — syntax,
   execution model, anti-patterns
2. [Design & Agent Spec](references/agent-design-and-spec-creation.md) —
   Agent Spec structure, flow control pattern recognition
3. [Subagent Map Diagrams](references/agent-subagent-map-diagrams.md) —
   Mermaid conventions for subagent graph visualization
4. [Metadata & Lifecycle](references/agent-metadata-and-lifecycle.md) —
   directory conventions, bundle metadata
5. [Known Issues](references/known-issues.md) — only load when code
   contains unexplained workaround patterns

### Modify an Existing Agent

User wants to add, remove, or change subagents, actions, instructions, or flow control on existing agent. May describe change in plain language ("add a billing subagent") or reference specific Agent Script constructs.

#### Required Steps

Read [CLI for Agents](references/salesforce-cli-for-agents.md) for exact command syntax.

1. **Comprehend** — If no Agent Spec exists, reverse-engineer first by following "Comprehend an Existing Agent" workflow above.
2. **Update Agent Spec** — Read [Design & Agent Spec](references/agent-design-and-spec-creation.md) for flow control patterns and existing action analysis. Modify Agent Spec to reflect intended changes. Default new actions to `NEEDS STUB` placeholders. Ask the user which path they want:
   - Path A: Keep placeholders only
   - Path B: Scan for existing actions to reuse
   - Path C: Generate new actions
   Only run scans if the user explicitly chooses Path B or C.
   **If the modification involves adding, replacing, or removing knowledge grounding**, ask: *"Will this agent answer questions from a document corpus (PDF/DOCX/TXT)? If so, what file path?"* Capture the path in the updated Spec under a **"Knowledge Grounding"** section. Asking now — during Spec update — surfaces ADL changes for the user's approval and lets us kick off provisioning right after.
   **Always save updated Agent Spec as file.**
3. **STOP for user approval of updated Agent Spec.** Present to user (including the Knowledge Grounding section if present). Ask for approval or feedback. **Do not proceed** without approval. Once approved, proceed without stopping unless a step fails.
4. **Kick off ADL provisioning (only if the Spec has a Knowledge Grounding section).**
   - If the `.agent` already has a `knowledge:` block with a populated `rag_feature_config_id` AND the user is keeping the same library, reuse it. Skip provisioning. (No need to confirm `retrieverId` here — that gate moves to Step 8.)
   - If a new ADL is needed, follow the same flow as the create workflow: read [Data Library Reference](references/data-library-reference.md), run the Step 0 preflight (`sf agent adl list`), and (if DC is ready) run `sf agent adl create` (Step 1) to capture `libraryId`. Compute `rag_feature_config_id = "ARFPC_<libraryId>"` from `libraryId` alone — that's enough to author the bundle. Start the upload + indexing flow (reference Steps 2–6) **in the background** while you continue to Step 5 (Edit code). Per Rule 5, do not block on async indexing. Also kick off the Data Cloud permset assignment for the agent user — see [Agent User Setup](references/agent-user-setup.md), Step 3b, which now ends with Step 3b.5 pinned post-assignment verification (against the resolved running-user and Einstein Agent User IDs) so callers can treat "Step 3b passed" as an authoritative Data Cloud grounding gate without re-running inline SOQL.
   - If grounding is not part of the modification, skip this step.
5. **Edit code** — Read [Core Language](references/agent-script-core-language.md) for syntax and anti-patterns. Edit `.agent` file to implement approved changes. If Step 4 produced a `libraryId`, include or update the `knowledge:` block and the `AnswerQuestionsWithKnowledge` action per [Data Library Reference](references/data-library-reference.md).
6. **Validate compilation** —
   `sf agent validate authoring-bundle --json --api-name <Developer_Name>`
   If validation fails, read [Validation & Debugging](references/agent-validation-and-debugging.md) to diagnose and fix, then re-validate.
7. **Generate new action implementations (explicit user-requested path only)** — Only run this step if the user explicitly asked to generate new implementations (Path C in Step 2). For each new action marked NEEDS STUB:
   `sf template generate apex class --name <ClassName> --output-dir <PACKAGE_DIR>/main/default/classes`
   Replace class body with invocable pattern from [Design & Agent Spec](references/agent-design-and-spec-creation.md). ALWAYS deploy:
   `sf project deploy start --json --metadata ApexClass:<ClassName>`
   ALWAYS fix deploy errors BEFORE generating and deploying next stub. Skip if no new actions added.
8. **Validate behavior** — Read [Validation & Debugging](references/agent-validation-and-debugging.md) for preview workflow and session trace analysis.
   **If Step 4 provisioned a new ADL**, before sending any grounded test utterances confirm the library is queryable: run `sf agent adl get -i $LIBRARY_ID` and check that `retrieverId` is present ([Data Library Reference](references/data-library-reference.md), Step 6). If still null, wait and re-poll — do not preview yet, the agent will return empty `knowledgeSummary` and the anti-hallucination guard will refuse on every utterance.
   `sf agent preview start --json --use-live-actions --authoring-bundle <Developer_Name>`
   If actions query data, ground test utterances with:
   `sf data query --json -q "SELECT <Relevant_Fields> FROM <SObject> LIMIT 100"`
   Send test utterances with:
   `sf agent preview send --json --authoring-bundle <Developer_Name> --session-id <ID> -u "<message>"`
   **Smoke testing requirements** (see [Validation & Debugging](references/agent-validation-and-debugging.md), Utterance Derivation):
   - Test changed paths first, then adjacent paths to catch regressions.
   - Test ALL routing branches affected by the change. Multiple phrasings per branch.
   - Use realistic utterances — write what a human would actually type, not keywords.
   - After EVERY utterance, read the trace to confirm actions actually fired (`FunctionStep`). Do not trust the agent's text response alone.
   - Evaluate against the Agent Spec: conversation flow, instruction adherence, unnecessary repetition, response quality.
   If behavior diverges from the Agent Spec, fix the `.agent` file and re-preview. For complex issues, switch to **Diagnose Behavioral Issues** workflow.
   **CHECKPOINT — Stay in draft iteration unless user explicitly asks to release.**
   **If user requests release, do NOT proceed to Publish unless ALL are true:**
   - `validate authoring-bundle` passes with zero errors
   - Live preview (`--use-live-actions`) tested with realistic utterances covering all routing branches
   - Traces confirm correct subagent routing, action invocation (`FunctionStep` present), and spec-compliant behavior
   - User explicitly approves deployment
   - **If the agent has a `knowledge:` block**: the Einstein Agent User has a Data Cloud permset/PSL assigned. Verify both:
     ```bash
     sf data query --json -q "SELECT PermissionSet.Name FROM PermissionSetAssignment WHERE Assignee.Username='<agent_user>'"
     sf data query --json -q "SELECT PermissionSetLicense.DeveloperName FROM PermissionSetLicenseAssign WHERE Assignee.Username='<agent_user>'"
     ```
     One of `GenieDataPlatformStarterPsl`, `GenieUserEnhancedSecurity`, `DataCloudUser`, or `DataCloudArchitect` must appear in the combined results. If none does, run [Agent User Setup, Step 3b](references/agent-user-setup.md) discovery-then-assign and re-verify before proceeding. If a Data Cloud permset is assigned but a smoke-test grounded query returns empty `knowledgeSummary`, the **Data Space scope** also needs to be granted on that permset — UI-only, see [Agent User Setup, Step 3b.4](references/agent-user-setup.md).
9. **Publish (explicit release step)** — Only after the user confirms they are ready to commit this draft to metadata. Publish validates metadata structure, not agent behavior. Every publish creates permanent version number.
   `sf agent publish authoring-bundle --json --api-name <Developer_Name>`
   If publish fails, follow troubleshooting checklist in [Metadata & Lifecycle](references/agent-metadata-and-lifecycle.md), Section 5 before retrying.
10. **Activate (explicit release step)** — Makes new version available to users after publish.
    `sf agent activate --json --api-name <Developer_Name>`
11. **Verify published agent** — Preview user-facing behavior AFTER activation with
    `sf agent preview start --json --api-name <Developer_Name>`
    Use `--api-name`, not `--authoring-bundle`.

#### Reference Files

1. [CLI for Agents](references/salesforce-cli-for-agents.md) — exact
   command syntax for validate, deploy, preview, publish, activate
2. [Core Language](references/agent-script-core-language.md) — syntax,
   anti-patterns
3. [Design & Agent Spec](references/agent-design-and-spec-creation.md) —
   Agent Spec updates, action implementation analysis
4. [Validation & Debugging](references/agent-validation-and-debugging.md) —
   compilation diagnosis, preview workflow, session trace analysis
5. [Data Library Reference](references/data-library-reference.md) —
   provisioning and Agent Script wiring for ADL grounding
6. [Known Issues](references/known-issues.md) — only load when errors
   persist after code fixes

### Diagnose Compilation Errors

User has Agent Script that won't compile. Errors surface from `sf agent validate` or `sf agent preview start`, or User describes symptoms like "I'm getting a validation error."

#### Required Steps

Read [CLI for Agents](references/salesforce-cli-for-agents.md) for exact command syntax.

1. **Capture concrete errors first, then reproduce** — If the user already shared error output, extract and list the exact error messages first. Then run
   `sf agent validate authoring-bundle --json --api-name <Developer_Name>`
   to capture basic compile errors. If no errors, run
   `sf agent preview start --json --use-live-actions --authoring-bundle <Developer_Name>`
   to capture complex compile errors. If reproduction differs from user-provided errors, call out both and continue with the current reproducible errors.
2. **Classify error** — Read [Validation & Debugging](references/agent-validation-and-debugging.md) for error taxonomy. Map each exact error message to a root cause category.
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

Agent compiles, preview can start and `--use-live-actions`, but agent does not behave as expected. User describes symptoms like "the agent keeps going to the wrong subagent" or "the action isn't being called." Fundamentally different from `validate` or `preview start` errors — code is valid but behavior is wrong.

#### Required Steps

Read [CLI for Agents](references/salesforce-cli-for-agents.md) for exact command syntax.

1. **Establish baseline** — Read Agent Spec. If no Agent Spec exists, follow *Comprehend an Existing Agent* workflow to reverse-engineer one, then continue.
2. **Form hypotheses** — Read [Core Language](references/agent-script-core-language.md) for execution model. Based on user's description, list candidate root causes. Think through: subagent routing, gating conditions, action availability, instruction clarity, variable state, and transition timing.
3. **Reproduce in preview** — Read [Validation & Debugging](references/agent-validation-and-debugging.md) for preview workflow and session trace analysis. Start preview session:
   `sf agent preview start --json --use-live-actions --authoring-bundle <Developer_Name>`
   then send test messages covering EACH subagent with `sf agent preview send`. One message is not enough — confirm behavior per subagent before proceeding.
4. **Analyze session traces** — Examine trace output to confirm subagent selection, action availability/execution, LLM reasoning, and where behavior diverges from Agent Spec. Do NOT skip this step — preview output alone is insufficient for diagnosis.
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
2. **Deploy bundle and dependencies** — Read [Metadata & Lifecycle](references/agent-metadata-and-lifecycle.md) for dependency management and deploy commands. Deploy `AiAuthoringBundle` and all action implementations (Apex classes, Flows, Prompt Templates) and dependencies to org.
3. **Live preview** — Read [Validation & Debugging](references/agent-validation-and-debugging.md) for preview workflow and session trace analysis.
   `sf agent preview start --json --use-live-actions --authoring-bundle <Developer_Name>`
   then send test utterances with:
   `sf agent preview send --json --authoring-bundle <Developer_Name> --session-id <ID> -u "<message>"`
   Test key conversation paths to validate agent behavior when backed by live actions.
   **CHECKPOINT — Do NOT proceed to Publish unless ALL are true:**
   - `validate authoring-bundle` passes with zero errors
   - Live preview (`--use-live-actions`) tested with realistic utterances covering all routing branches
   - Traces confirm correct subagent routing, action invocation (`FunctionStep` present), and spec-compliant behavior
   - User explicitly approves deployment
4. **Publish (explicit release step)** — Publish validates metadata structure, not agent behavior. DO NOT publish as part of a dev/test inner loop. ONLY publish as the FINAL step after user confirmation to commit this draft and prior to activation.
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

1. **Establish coverage baseline** — Read Agent Spec. If no Agent Spec exists, reverse-engineer first by following Comprehend steps. Map every subagent, action, and flow control path to identify what needs test coverage.
2. **Design test scenarios** — For test design methodology, expectations, metrics, test spec YAML format, and templates, use **agentforce-test** skill. That skill owns all testing content. For each coverage target, write one or more test scenarios: user utterance, expected subagent routing, expected action invocations, and expected agent response. Include both happy paths and edge cases.
3. **Offer security coverage** — Security testing is part of the ADLC test flow, not a separate step. Treat OWASP LLM Top 10 resistance as a first-class coverage dimension alongside functional scenarios. **Confirm with the user before generating security test cases**, then use **agentforce-test** skill **Mode C1-author** to write a Testing Center security suite from the agent's own `.agent` file (method: `skills/agentforce-test/references/security-test-design.md`) that ships alongside the functional test spec. `C1-author` validates the spec locally with `sf agent test create --preview` and deploys nothing; deploying and running it (`C1-run`) is a separate decision the user makes in `/agentforce-test`, because `sf agent test run` has no simulated-action mode and executes the agent's real actions. Skip only if the user declines.
4. **Write test spec YAML** — Use template and reference files from **agentforce-test** skill. Save to `specs/<Agent_API_Name>-testSpec.yaml` in SFDX project.
5. **Create test metadata** — Generate `AiEvaluationDefinition` from test spec using CLI.
6. **Deploy test** — Deploy `AiEvaluationDefinition` to org.
7. **Run tests** — Execute test run using CLI. Capture results.
8. **Analyze results** — Compare actual outcomes against expectations. For failures, identify whether issue is in agent code, action implementations, or test spec itself.
9. **Iterate** — Fix agent code or test spec as needed, redeploy, and re-run until coverage targets are met.

#### Reference Files

1. [CLI for Agents](references/salesforce-cli-for-agents.md) — exact
   command syntax for test create, test run, test results
2. [Core Language](references/agent-script-core-language.md) — agent
   structure for designing meaningful tests
3. [Design & Agent Spec](references/agent-design-and-spec-creation.md) —
   Agent Spec as test coverage baseline
4. **agentforce-test** skill — test spec YAML format, expectations,
   metrics, test design methodology, and test spec template

### Optimize an Agent

User wants to improve an existing Agent Script agent by scanning for common optimization patterns and applying fixes. May say "optimize my agent", "improve my agent", "clean up this agent", "refactor agent", or mention the agent feels inefficient or has redundancies. Also appropriate to suggest proactively after complex editing sessions with many incremental changes.

#### Required Steps

1. **Read and analyze the agent file** — Read the current `.agent` file. Read [Core Language](references/agent-script-core-language.md) for syntax rules and valid constructs as validation reference during optimization.
2. **Scan for optimization patterns** — For EACH subagent, systematically apply patterns 1–4 (and Pattern 5 if the agent has a `modality voice:` block). Each pattern's reference file has the detection heuristics and detailed fix instructions — read the ones that apply:
   - **Pattern 1 — Wire action outputs to deterministic consumers.** [Data Flow](references/optimization-pattern-1-data-flow.md). Persist a producer output only when a later deterministic consumer needs that exact trusted value; do not replace `...` slot filling that legitimately draws from the current turn.
   - **Pattern 2 — Extract requirement-backed deterministic logic.** [Deterministic Logic](references/optimization-pattern-2-deterministic-logic.md). Extract only when the condition is machine-known and protects regulation, authorization, an irreversible consequence, ordering, exact data flow, or an observed trace failure. Leave unstructured judgment to the model.
   - **Pattern 3 — Fix variable/action reference syntax in instructions.** [Reference Syntax](references/optimization-pattern-3-reference-syntax.md). `{!@variables.X}` and `{!@actions.X}` instead of bare `@variables.X` / use-case phrasing.
   - **Pattern 4 — Repair promised human handoff.** [Human Handoff](references/optimization-pattern-4-escalation.md). Apply only when requirements specify live handoff; never add escalation as default boilerplate.
   - **Pattern 5 — Voice-readiness (voice agents only).** Instructional fixes are auto-apply candidates; voice-unsafe action authoring and latency issues are flag-only. See [Voice Modality Reference](references/voice-modality-reference.md) "Instructions for Voice Agents", [Actions Reference](references/actions-reference.md) "Voice-Safe Action Authoring", and [Voice Latency Heuristics](references/voice-latency-heuristics.md). **Never auto-change** escalation numbers/queues, SLA/pricing/legal wording, or PII handling — surface a suggested rewrite and require explicit approval.
3. **Report findings** — Present all findings as a concise `## Optimization Report` with per-improvement, actionable edit instructions (subagent + line, the variable/`set`/binding or logic-extraction change to make), then ask: *"Would you like me to apply these [N] improvements?"*
4. **STOP for user approval.** Do not apply changes without explicit approval.
5. **Apply improvements (if approved)** — Edit the `.agent` file directly for each approved improvement. Track successes and failures.
6. **Validate compilation** — `sf agent validate authoring-bundle --json --api-name <Developer_Name>`. If validation fails, fix introduced errors and re-validate.
7. **Report results** — Summarize which improvements were applied and which failed (with the reason).

#### Reference Files

- [Core Language](references/agent-script-core-language.md) — validation reference during optimization
- [Optimization Pattern 1–4](references/optimization-pattern-1-data-flow.md) — data flow, [deterministic logic](references/optimization-pattern-2-deterministic-logic.md), [reference syntax](references/optimization-pattern-3-reference-syntax.md), [human handoff](references/optimization-pattern-4-escalation.md) (detection heuristics + fix instructions per pattern)
- [Voice Modality Reference](references/voice-modality-reference.md) + [Voice Latency Heuristics](references/voice-latency-heuristics.md) + [Actions Reference](references/actions-reference.md) "Voice-Safe Action Authoring" — Pattern 5 voice-readiness
- [Validation & Debugging](references/agent-validation-and-debugging.md) — compilation validation after applying optimizations

### Manage MCP Servers

User wants to register, configure, or manage Model Context Protocol (MCP) servers in the Salesforce API Catalog so their assets (tools, prompts, resources) become available as agent actions. May say "register an MCP server", "create MCP server", "list MCP servers", "whitelist MCP tools", "approve tools", "fetch MCP assets", "update MCP server", "delete MCP server", or mention MCP authentication. Uses `sf agent mcp` CLI commands. This is distinct from general MCP development or MCP protocol design.

#### Required Steps

Read [MCP Server Management](references/mcp-management-reference.md) for exact command syntax, response structures, the interactive whitelisting flow, security best practices, error handling, and complete examples. In brief:

1. **Verify target org** — `sf config get target-org --json` (Rule 2). If none is set, ask the user to set one first.
2. **Identify the operation** and map it to a workflow in the reference (register, list, get details, fetch + whitelist assets, list assets, update, delete). Gather any missing required inputs; handle client secrets via **stdin piping, never on the command line**.
3. **Execute the `sf agent mcp` command** with `--json` (Rule 1). After create, read the server ID from `result.server.id` (not `result.id`). These commands are developer preview, so every response carries a `warnings` preview notice.
4. **Whitelist interactively** — display each asset's metadata and wait for explicit yes/no/skip per tool. `sf agent mcp asset replace` is a FULL replacement — send the complete desired state.
5. **Apply security review before activating** — flag destructive, broadly-scoped, or auth-requiring tools; warn on production orgs; require explicit confirmation for destructive operations and deletions.
6. **Confirm results** and clean up any temp allowlist files.

#### Reference Files

- [MCP Server Management](references/mcp-management-reference.md) — `sf agent mcp` command reference, response structures, interactive whitelisting flow, security best practices, error handling, and complete examples

## The Agent Spec

**Agent Spec** is the central artifact this skill produces and consumes. A structured design document representing agent purpose, user outcomes, subagent graph, actions and implementations, variables, subagent posture, deterministic controls (when needed), and behavioral intent.

Agent Specs evolve with the agent. Sparse during agent creation (purpose, use cases, planned placeholders). Fleshed out during agent build (flowchart, action implementations mapped, posture choices documented, deterministic controls added only where justified). Reverse-engineered when comprehending existing agents. Critical for advanced troubleshooting, providing reference to compare expected vs. actual behavior. During testing, test coverage maps against it.

Always produce or update Agent Spec as first step of any operation that changes or analyzes agent. It is consistent grounding to work from, and a durable artifact a developer can review.

Read [Design & Agent Spec](references/agent-design-and-spec-creation.md) for Agent Spec structure and production methodology.

## Assets

The `assets/` directory contains templates and examples. Read when you need a starting point or a concrete reference for artifacts and source files.

- **`assets/agent-spec-template.md`** — Agent Spec template with all sections and placeholder content. Copy to `<AgentName>-AgentSpec.md` in project directory, then fill in during design. Save Agent Spec as file — significant design artifact that benefits from proper rendering, especially Mermaid Subagent Map diagram.

- **`assets/agents/local-info-agent-annotated.agent`** — Complete annotated example based on Local Info Agent, showing all major Agent Script constructs in context with inline comments explaining why each construct is used. Read when you need concrete reference for how concepts compose into working agent, or as fallback when focused examples in reference files aren't sufficient.

- **`assets/agents/template-single-subagent.agent`** — Compatibility-named focused starter with one `start_agent` execution block and no router or subagent blocks.

- **`assets/agents/template-multi-subagent.agent`** — Minimal agent with multiple subagents and transitions. Copy and modify for complex agents.

- **`assets/invocable-apex-template.cls`** — Reference for invocable Apex
  classes. Copy and modify when complex Apex action implementations are desired.

## Important Constraints

- **Use only Salesforce CLI and Salesforce org.** Do not reference or depend on other skills, MCP servers, or external tooling. All commands use `sf` (Salesforce CLI).

- **Only certain implementation types are valid for actions.** For example, only invocable Apex (not arbitrary Apex classes) can back an action. Similar constraints may apply to Flows and Prompt Templates. When wiring actions to implementations, consult Design & Agent Spec reference file for valid types and stubbing methodology.

- **`sf agent generate test-spec` is not for agentic use.** It is interactive, REPL-style command designed for humans. When creating test specs, start from boilerplate template in assets instead.

## Common Issues Quick Reference

**`Internal Error, try again later` during publish:**
Server-side compile failure. The 500 doesn't tell you which check failed — walk all four causes in order before asking the user what's wrong. Do NOT stop at cause 1.

1. **Agent type mismatch on `access.default_agent_user`.** Employee agents normally omit `access.default_agent_user`; service agents MUST have it (and the user must hold an Einstein Agent license). See [Design & Agent Spec](references/agent-design-and-spec-creation.md), Section 3. Re-run the query — do not invent the username.
2. **Action definition missing `outputs:` block.** If any action has `target:` and `inputs:` but no `outputs:`, the server-side compiler can't generate return bindings. CLI `validate` and LSP both PASS — only publish fails. See [Known Issues](references/known-issues.md), Issue 15.
3. **Other structural drift in the `.agent` file.** Diff against a known-good bundle in the same org:
   `sf project retrieve start --metadata "AiAuthoringBundle:<known-working-agent>" --output-dir /tmp/diff-bundle --json`
   Compare keyword-by-keyword. Look for missing required-but-undocumented fields, block-ordering drift, or DSL keywords your bundle uses that aren't in the working one.
4. **Genuine transient backend error.** If 1–3 are clean and the response `requestId` differs across retries, wait 60 s and retry once.

**`Unable to access Salesforce Agent APIs...` during preview:**
`default_agent_user` lacks permissions. See [Agent User Setup & Permissions](references/agent-user-setup.md). Do NOT publish as fix — `--use-live-actions` does not require published agent.

**Permission error referencing different username than configured:**
Same fix as above — error references org's default running user, but root cause is Einstein Agent User permissions.

**Agent fails with permission error even though current subagent's actions work:**
Planner validates ALL actions across ALL subagents at startup. One missing permission fails entire agent.

**Apex action returns empty results in live preview but works in simulated:**
`WITH USER_MODE` + missing object permissions = silent failure (0 rows, no error). See [Agent User Setup & Permissions](references/agent-user-setup.md), Section 6.2.

**Agent published, ADL indexed (`retrieverId` populated), but every grounded question returns empty `knowledgeSummary` / "I don't have that information":**
The Einstein Agent User lacks Data Cloud access. Two things to check, in order:
1. **Permset/PSL not assigned.** Run the verification queries from [Agent User Setup, Step 3b.3](references/agent-user-setup.md). If no Data Cloud permset/PSL appears, run the discovery-then-assign procedure (priority: `GenieDataPlatformStarterPsl` PSL → `GenieUserEnhancedSecurity` PS → `DataCloudUser` PS → `DataCloudArchitect` PS).
2. **Data Space scope not granted on the permset.** Currently no API. Setup → Permission Sets → click the assigned permset → "Data Cloud Data Space Management" under Apps → Edit → add the ADL's data space (usually `default`) → Save. See [Agent User Setup, Step 3b.4](references/agent-user-setup.md).

## Quick Links (Deep Detail Lives in References)

- Syntax and execution model: [Core Language](references/agent-script-core-language.md)
- Agent design/spec process: [Design & Agent Spec](references/agent-design-and-spec-creation.md)
- Posture dial (agentic vs deterministic): [Posture & Determinism](references/posture-and-determinism.md)
- Concrete authoring invariants: [The Zen of AgentScript](references/zen-of-agentscript.md)
- Pattern selection by scenario: [Patterns by Requirement](references/patterns-by-requirement.md)
- Architecture mechanics and migration: [Architecture Patterns](references/architecture-patterns.md)
- Validation, preview, and traces: [Validation & Debugging](references/agent-validation-and-debugging.md)
- Deploy/publish/activate lifecycle: [Deploy Reference](references/deploy-reference.md)
- Metadata lifecycle and publish troubleshooting: [Metadata & Lifecycle](references/agent-metadata-and-lifecycle.md)
- ADL provisioning and wiring: [Data Library Reference](references/data-library-reference.md)
- Agent access and permissions: [Agent Access Guide](references/agent-access-guide.md), [Agent User Setup](references/agent-user-setup.md)
- Voice modality and telephony agents: [Voice Modality Reference](references/voice-modality-reference.md)
- Safety review framework: [Safety Review](references/safety-review-reference.md)
- Rubric and review scoring: [Scoring Rubric](references/scoring-rubric.md)
- Optimization patterns: [Pattern 1 — Data Flow](references/optimization-pattern-1-data-flow.md), [Pattern 2 — Deterministic Logic](references/optimization-pattern-2-deterministic-logic.md), [Pattern 3 — Reference Syntax](references/optimization-pattern-3-reference-syntax.md), [Pattern 4 — Escalation](references/optimization-pattern-4-escalation.md)
- MCP server registration and tool whitelisting: [MCP Server Management](references/mcp-management-reference.md)
