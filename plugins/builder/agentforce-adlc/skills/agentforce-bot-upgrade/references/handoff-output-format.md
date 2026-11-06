# Handoff Output Format

## Required Files

1. `<AgentName>-AgentSpec.md`
2. `<AgentName>-einstein-bot-handoff.json`
3. `<AgentName>-open-questions.md`

The extraction step also persists `extraction-summary.json` in the same directory (see [Extraction Blueprint](extraction-blueprint.md)); it is carried forward as supporting context in the handoff.

Write all required files in the run-specific SFDX project directory for the selected input mode:
- Online: org-backed run project directory created during SF CLI setup
- Offline: run project directory containing/associated with provided XML inputs
Do not write handoff artifacts in the repository root.

## 1) Agent Spec Markdown

Create `<run_project_dir>/<AgentName>-AgentSpec.md` by copying:
[agent-spec-template.md](../assets/_vendored/agent-spec-template.md) from the `agentforce-generate` skill.

The handoff Agent Spec MUST:

1. retain the same section names and ordering as the template
2. fill every section with migration-specific content derived from extraction outputs

Required section order:

1. `## Purpose & Scope`
2. `## Behavioral Intent`
3. `## Subagent Posture`
4. `## Subagent Map`
5. `## Variables`
6. `## Actions`
7. `## Action Invocation Strategy`
8. `## Deterministic Controls (When Needed)`
9. `## Architecture Pattern`
10. `## Agent Configuration`

### How the generated agent works

Write every section below for this runtime model.

The generated agent is an intelligent, LLM-backed conversational experience provider. Unlike the bot, it does not follow a fixed dialog tree: it interprets each user message and decides which subagent should handle it.

1. **Router first.** Every incoming user message is processed first by the router subagent — the `start_agent` block. The router only classifies and routes; it never answers the user directly.
2. **Intent-based transitions.** The router transitions to the subagent that best matches the user's intent, judged against each subagent's `description` and its transition action descriptions. Write every subagent description with a clear positive scope and important exclusions, so routing stays unambiguous.
3. **Default `ambiguous` and `off_topic` subagents.** Always include both subagents, each with its own router transition, in every generated Agent Spec — even if the bot had no equivalent dialogs. List them in `## Subagent Posture` and `## Subagent Map` like any other subagent. Neither invokes any action.
   - **`ambiguous`** — handles requests whose intent is unclear or could match more than one subagent. Say briefly that the request is unclear and ask one focused question for the missing detail. Do not guess an intent.
   - **`off_topic`** — handles requests that no subagent covers. Say that the request is outside what the agent can help with, state the supported capabilities, and ask which of them the user wants help with. Do not answer the out-of-scope question.
   - Write the two router transition descriptions so they do not overlap: unclear-but-possibly-supported requests go to `ambiguous`; clearly unsupported requests go to `off_topic`.
   - Once the user's reply makes the intent clear, the router can route the request.

   This default applies to every bot upgrade. It overrides agentforce-generate's general guidance to create `ambiguous_question` or `off_topic` subagents only when needed.

Related agentforce-generate references:
- [Router-First Architecture Mechanics](_vendored/architecture-patterns.md#router-first-architecture-mechanics) — router behavior and transition paths.
- [Guardrail subagents](_vendored/agent-design-and-spec-creation.md) ("Guardrail Subagents") — example `ambiguous_question` and `off_topic` instructions.
- [Off-Topic and Escalation Routing](_vendored/agent-subagent-map-diagrams.md#off-topic-and-escalation-routing) — how ambiguity and out-of-scope paths appear in the Subagent Map.

### Bot-specific artifact translation rules (required)

When generating the Agent Spec, do not retain raw bot-only entities. Translate them into agent-native behavior.

1. Do not carry forward bot-only references directly, including:
   - intent names derived from dialog naming
   - intent utterance lists as bot-training artifacts
   - dialog identifiers/names
   - menu redirection constructs
2. Replace each with equivalent capability-level descriptions:
   - user goal summaries
   - behavioral routing intent
   - reasoning instructions for when/how to route or invoke actions
3. Menu redirections must be translated by:
   - capturing the user intent behind each menu option
   - converting each option into an equivalent reasoning-based LLM instruction
   - preserving functional outcomes without reproducing rigid bot menu mechanics
4. Evaluate every bot return message/response shown to users:
   - if a message contains no actionable information and is only small talk, ignore it
   - otherwise, preserve equivalent user-facing messaging in the relevant subagent behavior
   - do not miss messages containing information about next steps, required actions, documentation, policy, or handoff guidance
5. For each subagent, evaluate whether menu translation is necessary at all:
   - prefer direct intent/reasoning behavior when menus are unnecessary
   - retain a lightweight guided-choice pattern only when it materially improves clarity or control
6. If menu translation approach is ambiguous, ask the user and record the decision in open questions before finalizing. When `--interactive=false`, do not ask — apply the recommended translation, record it in open questions as an auto-applied decision, and continue.

### Action Invocation Optimization Rules

Use this step to optimize conversation efficiency by reducing unnecessary action invocations while preserving behavior and data contracts.

#### Allowed optimization operations

1. **Add action** — only when required to preserve an existing conversational outcome after removing/replacing bot-only behavior.
2. **Update action** — only for invocation optimization (for example, replacing multi-hop equivalent invocations with one semantically equivalent action).
3. **Delete action** — only when action is bot-only or redundant in the agent architecture.

#### Hard constraints

1. Do not merge or modify unrelated actions just to reduce invocation count.
2. Do not change action inputs/outputs in a way that causes data loss.
3. Preserve all variable assignments needed by downstream steps/subagents.
4. Preserve required action side effects that are part of business behavior.

#### Bot-only action handling

If an action is applicable only to Einstein Bot runtime (for example, internal bot-state bookkeeping actions):

Examples of bot-only actions:
- storing the previous or current dialog name (for example, to return the user to a dialog later)
- updating bot-only variables, such as dialog counters, menu-selection flags, or retry and fallback counters
- tracking bot navigation state, such as recording which menu option or dialog path the user took
- logging dialog visits or bot-session telemetry that no business process consumes

An action that also changes business data, or sets a variable that a business action or a routing decision still needs, is not bot-only.

1. Mark the action as `CANDIDATE_FOR_REMOVAL`.
2. Show the user why it is bot-only and why it is not needed in Agentforce.
3. Do not remove it automatically.
4. Remove only after explicit user confirmation. When `--interactive=false`, do not remove it — keep the action in place as the safe recommended default and record it as a deferred `CANDIDATE_FOR_REMOVAL` decision in open questions.
5. After the user confirms a removal, update `## Behavioral Intent` to match: in every workflow that invoked the removed action, drop its invocation from the ordered events and action sequencing, and drop any variable reads/writes that only that action used. Keep the rest of each workflow's behavior and ordering unchanged. Also remove the action from `## Actions` and `## Action Invocation Strategy`.

#### User review gate (required)

When `--interactive=false`, skip the interactive review: apply only non-destructive recommended optimizations (adds/updates), never auto-delete actions, record every applied and deferred change in open questions, then treat those recommended changes as final without prompting.

Before finalizing optimized actions, present a complete change summary to the user:

1. Added actions
2. Updated actions
3. Candidate removals
4. For each affected action, include:
   - action description/purpose
   - full input contract
   - full output contract
   - variable assignments (reads/writes)
   - rationale for optimization

Apply changes only after user approval.

### Section-by-section generation guidance (from `extraction-summary.json`)

#### `## Purpose & Scope`

1. Derive a meaningful purpose statement from bot description/identity and extracted intent summaries.
2. Describe the agent's business scope using the intents the bot actually handles.
3. Restrict scope to capabilities backed by configured actions:
   - do not claim unsupported capabilities
   - call out out-of-scope requests when no action support exists

#### `## Behavioral Intent`

1. Start traversal from `Welcome` (or extracted entry dialog when `Welcome` is absent).
2. Build each workflow using:
   - `dialog_functionality_summary`
   - ordered `step_functionality`
3. Handle navigations by following target dialogs recursively, while preserving navigation semantics:
   - **`Call` navigation**: transfer control to the target dialog, then return control back to the source dialog after target execution completes. Continue source-dialog remaining steps after return.
   - **`Redirect` navigation**: transfer control permanently to the target dialog and halt source-dialog execution immediately (no return to source flow).
4. While reconstructing flows, track `Call` vs `Redirect` semantics internally so downstream agent design preserves return/non-return behavior.
5. For `Call` flows, capture both:
   - the delegated target workflow behavior, and
   - the resumed source workflow behavior after return.
6. For `Redirect` flows, do not append post-redirect source steps to the same path unless there is an explicit later re-entry edge.
7. Reconstruct meaningful user conversation flows across traversed dialogs.
   - Each workflow might contain variable-based conditions for routing to other dialogs. Parse these and convert routing-specific conditions into equivalent natural-language LLM instructions. For example, `if selected_option == 'Bookings'` can be converted into "If the user wants bookings information, route to the bookings subagent."
8. Identify hard checkpoints by capturing strict ordering constraints, mandatory preconditions, and enforced branches/escalations.
   - If the ordering of actions is strictly enforced, retain the same ordering in the agent. For example, the user can check their bookings only after logging in: enforce this with variable-based conditions (via `available when`) in `## Deterministic Controls (When Needed)`, in `## Behavioral Intent`, or both.
9. Final behavioral intent must include:
   - ordered events for one or more workflows
   - action invocation scope and sequencing
   - variable usage scope (reads/writes and gating variables)
   - escalation/routing behavior
   - normalized transition behavior (return-after-delegation vs one-way transfer) expressed in agent-native terms only
   - other critical bot-specific constraints that affect conversation behavior

10. Do NOT emit raw bot navigation constructs (`Call`, `Redirect`) in the final Agent Spec text. Convert them into agent-native behavioral descriptions only.

#### `## Subagent Posture`

Use [posture-and-determinism.md](_vendored/posture-and-determinism.md) from the `agentforce-generate` skill as the definition of posture (scripted / mixed / agentic) and of how to choose it. Read it before deriving this section; do not invent posture categories or criteria beyond it.

1. Derive baseline subagents from dialog clusters (`1 cluster -> 1 subagent`).
2. Ensure each subagent has coherent responsibility boundaries based on associated dialog behavior and actions.
3. Add additional subagents when dialogs are not assigned to any cluster but represent distinct bot functionality.
4. Ensure all dialog functionality is covered by at least one subagent.
5. Record any uncertain assignments in open questions instead of forcing low-confidence grouping.
6. For each subagent, choose its posture per the posture definition, based on the extracted dialog behavior. A rigid bot step order does not by itself require scripted posture; pin only what the definition says needs a guarantee (for example authorization or identity checks, confirmed consequential actions, or externally required ordering).
7. Fill the template's posture table for every subagent: `Subagent`, `Posture`, `Why this posture?` (grounded in the bot's dialog behavior), and `Deterministic controls (if any)`. Keep the deterministic controls consistent with `## Deterministic Controls (When Needed)`.
8. If the posture of a subagent is ambiguous, record it in open questions with a recommended posture.

### Persistence requirement

After user confirms, update the Agent Spec file to reflect all finalized action changes (adds/updates/deletes), including:

- action descriptions
- input/output contracts
- variable read/write assignments
- action invocation strategy updates required by the optimization
- `## Behavioral Intent` workflow updates for removed actions (see Bot-only action handling, step 5)

Do not treat non-confirmed changes as final.

## 2) Open Questions Markdown

Include:

- Blocking decisions (must resolve before `/agentforce-generate` handoff)
- Non-blocking clarifications (resolve when they materially affect generated spec/actions)
- Recommended defaults for each question

Write this file as:

- `<run_project_dir>/<AgentName>-open-questions.md`

## 3) Einstein Bot Handoff JSON

Create `<run_project_dir>/<AgentName>-einstein-bot-handoff.json` as a machine-readable companion to the Agent Spec markdown, derived from `extraction-summary.json` and the mapping produced per [Mapping Rules](mapping-rules.md).

The handoff JSON MUST:

1. Capture the structured mapping used to build the spec:
   - subagent/topic mapping
   - action inventory with input/output contracts and `EXISTS`/`NEEDS_STUB`/`NEEDS_CREATION`/`CANDIDATE_FOR_REMOVAL` status
   - variable mappings (`mutable`/`linked`)
   - routing/transition mapping
   - unmapped items
2. Stay aligned with the finalized Agent Spec markdown — after the open-questions loop completes, regenerate it so it reflects the resolved spec before handoff (no contradictory mappings).

## Open Question Resolution Loop (Required)

After generating initial artifacts, resolve open questions one-by-one with the user. When `--interactive=false`, do not prompt — auto-apply the recommended default recorded for each question and mark it resolved.

For each resolved question:

1. Update `<run_project_dir>/<AgentName>-AgentSpec.md` with the resolved decision.
2. Update `<run_project_dir>/extraction-summary.json` with the same resolved finding and any downstream mapping updates.
3. Mark the question as resolved (or remove it) in `<run_project_dir>/<AgentName>-open-questions.md`.

Do not leave ambiguous or contradictory outcomes in any artifact.
