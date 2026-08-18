---
name: agentforce-generate
description: "Build, modify, audit, repair, optimize, debug, and deploy agents with Agentforce Agent Script. TRIGGER when: user creates, reviews, or changes .agent files or aiAuthoringBundle metadata; asks to fix AgentScript, audit an existing agent, run an AgentScript health check, common-pitfall review, or baseline-versus-candidate repair loop; changes a response, action, subagent, route, state flow, or Agent Spec; previews, debugs, deploys, publishes, or tests agents; uses sf agent generate/preview/publish/test; or manages Agentforce MCP servers, tools, assets, or authentication. DO NOT TRIGGER when: Apex, Flow, Prompt Template, Experience Cloud, or general Salesforce CLI work is unrelated to Agent Script; or the primary input is a production session or trace ID rather than an agent artifact."
metadata:
  version: "0.11"
  domains: ["Agentforce"]
  minApiVersion: "66.0"
  relatedSkills:
    - "agentforce-observe"
    - "agentforce-test"
    - "automation-flow-generate"
    - "integration-connectivity-generate"
    - "platform-apex-generate"
    - "platform-metadata-deploy"
  cliTools:
    - tool: ["corepack"]
      semver: ">=0.25.0"
    - tool: ["curl"]
      semver: ">=7.0.0"
    - tool: ["git"]
      semver: ">=2.0.0"
    - tool: ["jq"]
      semver: ">=1.6.0"
    - tool: ["node"]
      semver: ">=20.0.0"
    - tool: ["npm"]
      semver: ">=9.0.0"
    - tool: ["pnpm"]
      semver: ">=8.0.0"
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

Agent Script agents are defined by `AiAuthoringBundle` metadata: an
`<ApiName>.agent` file (agent behavior) plus a sibling
`<ApiName>.bundle-meta.xml` file (bundle metadata). The directory and both
filenames must use the same case-sensitive API name; a literal
`bundle-meta.xml` filename is not deployable. Actions can be implemented with
invocable Apex, autolaunched Flows, Prompt Templates, and other supported types.

This skill covers the full Agent Script lifecycle: designing agents,
writing Agent Script code, validating and debugging, deploying and
publishing, and testing.

## How to Use This Skill

This file maps user intent to task domains and relevant reference files in `references/`. Treat this file as the execution router for end-to-end agent development, and use references for deep detail.

Identify user intent from task descriptions. Read only the reference explicitly
required by the active step or needed for the current decision. Every
**Reference Files** section is a lookup index, not a preload list; do not load
files for later or inapplicable steps.

For a comprehensive health check, common-pitfall audit, or audit-fix-evaluate
loop over an existing agent, use the **Audit and Repair an Existing Agent**
task domain below as part of the same authoring lifecycle.

## Rules That Always Apply

1. **Always `--json`.** ALWAYS include `--json` on EVERY `sf` CLI command. Do NOT pipe CLI output through `jq` or `2>/dev/null`. Read the full JSON response directly — LLMs parse JSON natively.

2. **Verify target org.** Before any org interaction, run `sf config get target-org --json` to confirm a target org is set. If none configured, ask the user to set one with `sf config set target-org <alias>`.

3. **Diagnose in proportion to the change.** For syntax or local static defects,
   run the supported local parser/compiler first, then add target-org validation
   when available.
   For behavioral defects, preserve a baseline and use preview plus traces.
   For a Surface repair, freeze the exact accepted edit list, then inspect the
   final diff and revert every other hunk, including block-scalar or metadata
   normalization. In a smallest-change repair, keep optional cosmetic findings
   advisory unless the user explicitly includes cleanup in scope; valid syntax
   with no diagnostic or use-case consequence is not an extra repair.
   Simulation can establish routing and action selection; use
   `--use-live-actions` only with explicit approval, a verified non-production
   environment, and safe test data. Do not claim an external effect from
   simulation or response text. See
   [Validation & Debugging](references/agent-validation-and-debugging.md).

4. **Use a proportionate spec gate.** Obtain explicit Agent Spec approval for
   greenfield agents and Structural or Rewrite changes. A user-authorized,
   well-specified local repair does not require recreating or reapproving the
   entire spec; record the affected use case and preserve the existing design.
   When the user supplies a sufficiently detailed design and explicitly says it
   is already approved, treat that as the approved spec: do not recreate it or
   stop for another approval unless requirements are missing or materially change.

5. **Don't stall.** After a step completes successfully, announce the
   next step and start it. Do not wait for the user to say "what's next"
   or "ok, continue." Checkpoints that require explicit user approval include:
   (a) Agent Spec approval when required by Rule 4, (b) the pre-Publish
   CHECKPOINT, (c) destructive or consequential external operations, and (d)
   any A/B branch the skill explicitly surfaces (e.g., Data Cloud not
   provisioned during ADL setup). Long-running async work like ADL
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

12. **Do not let prompt formatting impersonate control flow.** Indentation,
    numbered steps, and words such as `Show`, `Ask`, `Call`, `Set`, or `STOP`
    inside `|` text are model instructions, not executable scope. Gate actions
    independently. Use one `|` per contiguous prompt block; repeated adjacent
    markers do not create stages or priority. Do not use
    `@utils.setVariables` to force a turn boundary or another reasoning
    iteration. Apply the checklist in
    [Common Control-Flow Pitfalls](references/common-control-flow-pitfalls.md).

13. **Choose who owns each decision.** Use runtime predicates when an exact
    machine-known fact has a consequence that must remain stable. Use model
    instructions when semantic intent, ambiguity, recovery, or
    situation-aware judgment makes flexibility more valuable. A model cannot
    read stored variable values unless prompt text injects them with
    `{!@variables.X}`; interpolation reveals a value but does not make the
    model's comparison deterministic. Apply the tradeoff test in
    [Posture & Determinism](references/posture-and-determinism.md).

14. **Compile AgentScript locally first, cheaply, and visibly.** For every
    authoring, repair, or audit task with an existing `.agent` file, attempt the
    bundled local index/compiler before org-side validation or a completion
    report. Run
    `node <skill-directory>/scripts/index-agent.mjs <agent-file>`. If the SDK
    cannot load, follow
    [AgentScript Compiler Setup](references/agentscript-toolchain.md), retry,
    and use its bounded npm/source fallback. Fix every severity-1 diagnostic
    and rerun until clean. Report the provider and exact version or commit.
    Org access does not replace this cheap local pass. If both local setup paths
    fail, continue with target-org validation or a bounded static review and
    state **compiler not used** with the cause; do not stall the task or imply
    that a suggested future command was validation. **Offline** or
    **non-interactive** mode does not waive this step: it prohibits network and
    org operations, not the bundled local compiler.

15. **Keep the authoring-bundle shape deployable.** Under
    `aiAuthoringBundles/<ApiName>/`, require exactly the matching pair
    `<ApiName>.agent` and `<ApiName>.bundle-meta.xml`. Do not shorten the
    metadata filename to `bundle-meta.xml`. Preserve scaffolded or retrieved
    metadata rather than rewriting its schema. A new CLI-scaffolded bundle
    normally uses `<bundleType>AGENT</bundleType>`; an existing descriptor can
    instead use the established `fullName`/`type`/`status` shape, with optional
    `label` and `description`. Do not create a partial hybrid or invent fields.
    Local compilation of the `.agent` file does not verify the metadata
    filename or XML, so check both before reporting validation success.

## Task Domains

Choose the domain that matches the user's current objective. Read its named
references before acting; the links are load instructions, not an optional
bibliography. Follow only the applicable workflow and preserve any satisfied
prerequisites. The normal lifecycle is design -> draft -> validate/preview ->
explicitly approved release.

### Create an Agent

Use for a new agent or authoring bundle.

1. Read [Design & Agent Spec](references/agent-design-and-spec-creation.md),
   then use an already-approved, sufficiently detailed supplied design as the
   build contract without regenerating or reapproving it. Otherwise capture the
   requirements in a saved Agent Spec and obtain explicit approval. Keep new
   action implementations as `NEEDS STUB` until the user chooses whether to
   reuse implementations, generate them, or leave placeholders.
2. Read the applicable sections of [CLI for Agents](references/salesforce-cli-for-agents.md)
   and validate the target-org prerequisites before org work. For document
   grounding, read [Data Library](references/data-library-reference.md). For a
   voice agent, read [Voice Modality](references/voice-modality-reference.md)
   and [Voice Latency](references/voice-latency-heuristics.md).
3. Generate the authoring bundle with Salesforce CLI. Edit the scaffolded
   `<ApiName>.agent` and preserve the matching `<ApiName>.bundle-meta.xml`.
   Read [Core Language](references/agent-script-core-language.md),
   [Instruction Resolution](references/instruction-resolution.md), and the
   applicable templates before writing.
4. Run the local compiler required by Rule 14. When an authenticated target org
   is available, also validate the authoring bundle in the org. Fix blocking
   diagnostics before implementing or deploying action dependencies.
5. Generate action implementations only when the user selected that path.
   Validate and deploy one dependency at a time.
6. Preview the draft and inspect traces using
   [Validation & Debugging](references/agent-validation-and-debugging.md).
   Cover realistic happy, adjacent, recovery, and cancellation paths.
7. Stay in the draft loop. Publish and activate only after the release gates in
   **Deploy, Publish, and Activate** pass and the user explicitly approves.

### Comprehend an Existing Agent

Use when the user wants to understand an existing bundle.

1. Locate the package and matching authoring-bundle files.
2. Read [Core Language](references/agent-script-core-language.md), then map the
   subagent graph, deterministic blocks, model instructions, actions, variables,
   and action implementations.
3. Read [Design & Agent Spec](references/agent-design-and-spec-creation.md) and
   reverse-engineer a saved Agent Spec. Use
   [Subagent Map Diagrams](references/agent-subagent-map-diagrams.md) for the
   graph. Annotate source only when the user requests it.
4. Flag supported anti-patterns, distinguishing observed behavior from static
   inference. Load [Known Issues](references/known-issues.md) only for an
   otherwise unexplained workaround.

### Audit and Repair an Existing Agent

Use for “fix my AgentScript,” health checks, common-pitfall reviews, and
baseline-versus-candidate repair loops.

1. Read [Audit and Repair](references/agent-audit-and-repair.md), then follow its
   linked scope/path-review and repair/report workflow in order.
2. Use the [Diagnostic Catalog](references/agent-audit-diagnostic-catalog.md)
   and its focused diagnostic references only for categories present in the
   artifact. Use [Common Control-Flow Pitfalls](references/common-control-flow-pitfalls.md)
   and its focused references for suspected prompt/control-flow defects.
3. Freeze accepted Surface edits before changing the artifact. For Structural
   or Rewrite work, obtain the approval required by Rule 4.
4. Compile locally, compare the unchanged baseline and candidate against the
   same use cases, and follow
   [Audit Evaluation Loop](references/agent-audit-evaluation-loop.md).
5. Report Surface, Structural, and Rewrite assessments separately. Stay
   draft-only unless the user separately requests a release operation.

#### Audit Reference Files

- [Audit Scope and Path Review](references/agent-audit-scope-path-review.md)
- [Audit Repair and Report](references/agent-audit-repair-report.md)
- [Audit Candidate Verification](references/agent-audit-candidate-verification.md)
- [Instruction and Routing Diagnostics](references/agent-audit-diagnostics-instructions-routing.md)
- [Action and State Diagnostics](references/agent-audit-diagnostics-actions-state.md)
- [Architecture and Evaluation Diagnostics](references/agent-audit-diagnostics-architecture-evaluation.md)
- [Action and Sequencing Pitfalls](references/control-flow-actions-sequencing.md)
- [Lifecycle and Side-Effect Pitfalls](references/control-flow-lifecycle-side-effects.md)
- [AgentScript Compiler Setup](references/agentscript-toolchain.md)

### Modify an Existing Agent

Use for an approved change to an existing response, route, action, subagent,
state flow, grounding source, or modality.

1. Comprehend the affected paths first. For a material design change, update the
   Agent Spec and obtain approval; for a narrow specified repair, record the
   affected use case without forcing a full spec rewrite.
2. Read [Core Language](references/agent-script-core-language.md) and only the
   feature references needed for the change. Preserve unrelated metadata,
   contracts, formatting, and behavior.
3. Edit the existing bundle in place. Generate action implementations only when
   explicitly requested.
4. Compile locally and, when available, validate against the target org. Preview
   every changed and adjacent path and inspect traces. Iterate in draft.
5. Use the release workflow only if the user separately requests release.

### Diagnose Compilation Errors

1. Capture the exact reported errors and run the Rule 14 local compiler.
2. When an authenticated target org is available, run org validation; use live
   preview only when compilation succeeds but runtime preparation still fails.
3. Classify and repair each concrete error using
   [Validation & Debugging](references/agent-validation-and-debugging.md) and
   [Core Language](references/agent-script-core-language.md).
4. Rerun the surfaces that exposed the error. Report exact executed checks,
   remaining limitations, and no unexecuted command as validation evidence.

### Diagnose Behavioral or Production Issues

For a local behavioral problem, preserve a baseline, preview with realistic
utterances, and inspect traces using
[Validation & Debugging](references/agent-validation-and-debugging.md). Confirm
which subagent, action calls, action results, state changes, and final response
actually occurred before editing.

For a production session or trace ID, use **agentforce-observe** for retrieval
and reconstruction. Return here only when evidence identifies an AgentScript
change. Never invent unavailable action inputs, outputs, or model reasoning.

### Deploy, Publish, and Activate

1. Read [CLI for Agents](references/salesforce-cli-for-agents.md),
   [Metadata & Lifecycle](references/agent-metadata-and-lifecycle.md), and
   [Deploy](references/deploy-reference.md).
2. Compile locally and validate against the target org. Deploy the bundle and
   dependencies, then run live preview with realistic coverage and inspect
   traces. Do not proceed through a blocking result.
3. Present the exact target org and version state. Obtain explicit user approval
   before publishing or activating.
4. Publish, activate, and verify the user-facing agent only after approval.

### Delete or Rename an Agent

Read the delete/rename sections of [CLI for Agents](references/salesforce-cli-for-agents.md)
and [Metadata & Lifecycle](references/agent-metadata-and-lifecycle.md). Enumerate
references and dependencies, show the exact affected bundle, and obtain explicit
confirmation before deletion. For rename, create and validate the replacement
before deleting the original; verify orphaned metadata afterward.

### Test an Agent

Use **agentforce-test** for test-spec design, security coverage, metadata
creation, execution, and result analysis. First map the Agent Spec and all
reachable routes/actions into coverage targets. Confirm before adding security
tests or running tests that can invoke live actions.

### Optimize an Agent

1. Read [Core Language](references/agent-script-core-language.md) and scan every
   reachable path using [Common Control-Flow Pitfalls](references/common-control-flow-pitfalls.md).
2. Load only applicable optimization references: data flow, deterministic
   logic, reference syntax, human handoff, and voice readiness.
3. Report evidence-backed improvements and obtain approval before editing.
4. Apply only approved changes, compile locally, validate against the org when
   available, and report the resulting evidence.

### Manage MCP Servers

Read [MCP Server Management](references/mcp-management-reference.md) before any
MCP operation. Verify the target org, use `--json`, keep secrets off command
lines, review tools before allowlisting, and require confirmation for destructive
or consequential changes.

## The Agent Spec

**Agent Spec** is the central artifact this skill produces and consumes. A structured design document representing agent purpose, user outcomes, subagent graph, actions and implementations, variables, subagent posture, deterministic controls (when needed), and behavioral intent.

Agent Specs evolve with the agent. Sparse during agent creation (purpose, use cases, planned placeholders). Fleshed out during agent build (flowchart, action implementations mapped, posture choices documented, deterministic controls added only where justified). Reverse-engineered when comprehending existing agents. Critical for advanced troubleshooting, providing reference to compare expected vs. actual behavior. During testing, test coverage maps against it.

Produce or update an Agent Spec for greenfield work, material design changes,
or analysis whose result changes the documented contract. For a narrow,
already-specified repair, record the affected use case and evidence without
forcing a full spec rewrite.

Read [Design & Agent Spec](references/agent-design-and-spec-creation.md) for Agent Spec structure and production methodology.

## Assets

The `assets/` directory contains templates and examples. Read when you need a starting point or a concrete reference for artifacts and source files.

- **`assets/agent-spec-template.md`** — Agent Spec template with all sections and placeholder content. Copy to `<AgentName>-AgentSpec.md` in project directory, then fill in during design. Save Agent Spec as file — significant design artifact that benefits from proper rendering, especially Mermaid Subagent Map diagram.

- **`assets/agents/local-info-agent-annotated.agent`** — Complete annotated example based on Local Info Agent, showing all major Agent Script constructs in context with inline comments explaining why each construct is used. Read when you need concrete reference for how concepts compose into working agent, or as fallback when focused examples in reference files aren't sufficient.

- **`assets/agents/template-single-subagent.agent`** — Compatibility-named focused starter with one `start_agent` execution block and no router or subagent blocks.

- **`assets/agents/template-multi-subagent.agent`** — Minimal agent with multiple subagents and transitions. Copy and modify for complex agents.

- **`assets/agents/router-first.agent`** — Transition-only router example with
  HyperClassifier and concise router instructions.

- **`assets/agents/verification-gate.agent`** — Identity/authorization gate
  with protected action availability.

- **`assets/agents/simple-qa.agent`**, **`production-faq.agent`**, and
  **`order-service.agent`** — Complete examples at increasing behavioral and
  action complexity.

- **`assets/patterns/README.md`** — Route to focused complete patterns for
  callbacks, input binding, lifecycle, delegation, and multi-step workflows.
  Use a pattern only when its stated use-case preconditions apply.

- **`assets/invocable-apex-template.cls`** — Reference for invocable Apex
  classes. Copy and modify when complex Apex action implementations are desired.

## Important Constraints

- **Use supported tooling for the evidence needed.** Use Salesforce CLI and the
  target org for org-backed validation and release operations. Use the published
  AgentScript SDK for local parse/compile checks, and invoke related skills only
  within their documented boundaries.

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
- Architecture mechanics, HyperClassifier routing, and migration: [Architecture Patterns](references/architecture-patterns.md)
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
