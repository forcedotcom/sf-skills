---
name: build-agent-broker-project
description: "Build, edit, validate, publish, and deploy a MuleSoft Agent Broker (Agent Network V2) project end-to-end. Use whenever the user asks to build, create, scaffold, configure, edit, validate, publish, or deploy an Agent Broker, agent network V2, AgentScript, `.agent` file, or `agentNetwork: 2.0.0` project. Do NOT trigger for V1→V2 migration (use the converter skill)."
license: Apache-2.0
metadata:
  author: mulesoft-agent-broker-team
  version: "1.0.0"
---

# ⚠️ HARD OUTPUT CONTRACT — applies to EVERY assistant turn in this skill

**You MUST output ≤ 4 lines of user-facing text per turn**, unless you are emitting a numbered list of confirmed items (asset list, validation findings, asset → node assignments) — in which case the list itself is the output and gets no preamble.

**FORBIDDEN openings.** Never start a turn with any of these phrases or their synonyms. If you catch yourself typing one, delete it:

- "I'll now..." / "Now I'll..." / "Next, I'll..." / "Let me..."
- "First, ..." / "To start, ..." / "Before I do..."
- "Based on..." / "Given that..." / "Since..."
- "Great!" / "Perfect!" / "Got it!" / "Understood!" / "Sure!"
- "I'm going to..." / "I plan to..." / "My approach is..."
- "Let me think about..." / "Let me analyze..." / "Let me check..."
- "Here's what I'm doing..." / "Here's my plan..." / "Here's a summary..."
- "Moving on to..." / "Now that we've..." / "Now we'll..."
- Any sentence describing what *you* are about to do. Just do it.

**FORBIDDEN content.** Never include in a turn:

- Recap of what the user just said. They remember.
- Pre-explanation of what comes after this turn. Wait until you get there.
- Restating the goal of the current phase. The phase headings handle that.
- Step-by-step narration of how you're reasoning. The user sees only the conclusion.
- Phase numbers or step numbers in the prose ("Step 4 says..." / "In Phase 2..."). The model uses these to navigate; the user doesn't see them.

**REQUIRED shape of a normal turn:**

```
<one action OR one question OR one bulleted list>
<optional: one short follow-up sentence, only if strictly needed>
<stop>
```

**End-of-phase confirmation shape:**

```
<bulleted list of what was captured, ≤ 6 bullets>
Anything missing?
```

**Validation-result shape:**

```
✅ PASS    (or)    ❌ FAIL — <N> issue(s)
- <issue 1>
- <issue 2>
```

If a phase needs multiple actions, do them in tool calls without narrating between them. Only emit user-facing text at decision/confirmation points.

---

# MuleSoft Agent Broker Builder

Turns a natural-language description of a multi-agent workflow into a complete, validated, deployable Agent Network V2 (GA, A2A v1.0) project. Runs a 6-phase guided experience and adds publish + deploy.

**The skill is CLI-first end-to-end.** Validate/publish/deploy use the **Anypoint CLI Agent Fabric plugin** (`mulesoft-anypoint-cli-agent-fabric-plugin`). Exchange asset search uses **Anypoint CLI v4** (`anypoint-cli-v4 exchange asset list`). Both are portable across Claude Code, Cursor, Codex, and Vibes, and match the CI/CD path. MCP tools (`mcp__mulesoft__*`) work as a fallback when present, but no MCP dependency is required.

## When to use

- Use for: building a new Agent Broker; adding/swapping nodes, agents, MCP tools, or LLMs; tuning instructions; changing routing; running validate/publish/deploy.
- Don't use for: V1→V2 conversions (use `translate-agent-broker-old-to-new-project`); standalone Mule apps, DataWeave, or APIs.

If the YAML has `schemaVersion: 1.0.0`, this is V1 — stop and route to the converter. The V2 marker is `agentNetwork: 2.0.0` (unquoted, top of file).

## References (read on demand)

- **`references/canonical-example.md`** — A complete, working Agent Network V2 (GA, A2A v1.0) project. The structural template — when in doubt, copy it.
- **`references/gotchas.md`** — GA syntax rules, compile-error rules, RULE-ASSET-MODE (inline vs Exchange), subagent-vs-orchestrator decision, auth casing, CLI + MCP tooling integration, graceful degradation.

The MuleSoft Agent Network GA docs (Anypoint Code Builder section) are the authoritative reference. The references above cover the gotchas and worked example.

## Node-type terminology (phase language ↔ schema keyword)

The 6 phases below use **user-facing names** for node types. The actual `.agent` file uses **schema keywords**. When talking to the user, use the phase name; when writing the file, use the keyword.

| Phase language | `.agent` keyword | What it is |
|---|---|---|
| **Reasoning node** | `subagent` | LLM-with-tools. Accepts actions; has built-in HITL. The default LLM-powered node type. |
| **Orchestrator node** | `orchestrator` | LLM-with-tools, specialized for coordinating **multiple** actions toward a compound goal. Use only when a node has ≥2 actions AND they jointly serve one outcome. |
| **Generate node** | `generator` | LLM **without** tools. For one-shot generation/summarization/classification with structured output. |
| (no LLM, deterministic) | `router` | Branching based on a known value. Conditions, not prompts. |
| (no LLM, side-effect) | `executor` | Runs one tool with known args, sets a variable. |
| (terminal) | `echo` | Sends the final A2A response to the client. |

## Tooling integration (CLI-first, MCP-fallback)

The skill prefers the **Anypoint CLI Agent Fabric plugin** (`mulesoft-anypoint-cli-agent-fabric-plugin`) for validate/publish/deploy and **Anypoint CLI v4** (`anypoint-cli-v4`) for Exchange search. The MuleSoft MCP server (`mcp__mulesoft__*`) is the fallback.

**Try CLI first. If the CLI fails, fall back to MCP immediately — do NOT ask the user, do NOT retry the CLI, do NOT stop the phase.**

A CLI attempt counts as **failed** when ANY of these happen:
- `command -v` returns nothing (binary not installed).
- The command exits non-zero for a reason OTHER than the user's own input (e.g., `ENOENT`, plugin not installed, auth env vars unset, network error, npm install needed, "command not found", `EACCES`).
- The command hangs past a reasonable timeout (~60s for search, ~5min for build/publish/deploy).
- The command returns success but the output is empty / malformed when the schema requires content (e.g., zero assets returned where the user explicitly named one).

A CLI attempt does **NOT** count as failed when:
- The user's input was bad (invalid project name, missing required field) — surface the error to the user, don't fall back.
- The validation/build legitimately found schema errors — report them; that's the CLI doing its job.

**Fallback procedure (apply silently, in this order):**
1. Catch CLI failure. Note the failure reason in one short internal line — do NOT narrate it to the user unless they ask.
2. Check if the equivalent `mcp__mulesoft__*` tool is registered in the session. If yes, call it with the equivalent inputs.
3. If MCP also fails or isn't present, fall back to the no-tool path (doc link / structural checklist / user prompt) per `references/gotchas.md` § "Graceful degradation".
4. Tell the user **only the outcome** ("found 3 LLM assets" / "validated — 2 issues" / "couldn't reach Exchange — give me the assetId manually?"), not the tool-by-tool path you took to get there.

**If a CLI command needs more info before running** (unknown flag, unfamiliar subcommand, ambiguous syntax error): try `<command> --help` first, then a public-web search if `--help` doesn't resolve it. Only after both come up empty should you ask the user. This applies to the CLI plugin AND `anypoint-cli-v4`. Do NOT narrate the lookup; just run the command with the corrected syntax.

See `references/gotchas.md` § "Tooling integration" for the full capability matrix, CLI command syntax, env-var auth (`ANYPOINT_CLIENT_ID/SECRET/ORG/ENV`), and the per-step CLI ↔ MCP mapping.

---

## Workflow A — Build a new project (Phases 1–6 + Publish/Deploy)

The 6 phases below structure the build experience. Each phase ends with a stop point — wait for the user. Apply each user response immediately (no batch-then-update).

## Step 1: Pre-flight + scaffold

1. **Detect existing project.** If working folder has `agent-network.yaml` + `exchange.json` + `brokers/`, ask: *"Edit this one, or scaffold new in a sibling folder?"* Default edit (Workflow B).
2. **Detect schema version.** `schemaVersion: 1.0.0` → route to converter.
3. **Confirm intent in one sentence:** *"You want me to build a new Agent Broker that does X. Sound right?"*
4. **Collect scaffold inputs** (ask before invoking CLI):
   - **Project name** (kebab-case, e.g. `it-help-investigation`) — also becomes the default `assetId`.
   - **Output directory** (default: current working dir).
   - **Asset version** (default `0.0.0` while in development; user can bump on first publish).
5. **Scaffold via CLI.** Run the create command from the parent directory:
   ```
   anypoint-cli-agent-fabric-plugin agent-network project create \
     --name <project-name> \
     --output-dir <parent-dir> \
     --create-dir
   ```
   This produces `<project-name>/agent-network.yaml` + `exchange.json` + `brokers/` with the correct `groupId`/`organizationId` (pulled from `ANYPOINT_ORG`) and starter template. Skill then edits the generated files in place.
   - If CLI is unavailable AND `mcp__mulesoft__create_agent_network_project` is present, call the MCP tool with the same inputs.
   - If neither is available, fall back to writing the canonical scaffold structure directly (`agent-network.yaml` with `agentNetwork: 2.0.0`, `exchange.json` with `"classifier": "agentic-network"`, empty `brokers/`) and tell the user the `groupId`/`organizationId` placeholder needs to be filled in before publish.
6. **Capture network `info`** for `agent-network.yaml`: ask for `info.label` (required) and `info.description` (optional). Default `info.version` to `1.0.0` unless user provides one. Apply to the scaffold immediately.

## Step 2: Functional Requirements (Phase 1)

**Goal:** Get the user to define functional requirements clearly. **Refuse vague answers** — keep prompting until each item is concrete. The user does not need to use graph terminology; natural-language steps are fine.

Capture, in order:

1. **Trigger** — what event starts the flow? (Almost always A2A `message/send`. Confirm.)
2. **Workflow steps & branching logic** — *"If X happens, then strictly do Y."* Walk through each step.
3. **Hard constraints** — what is absolutely restricted? These become **router conditions**, not prompt sentences.
4. **Determinism vs. open-endedness** — per step: 100% predictable outcome (graph branching) or LLM reasoning/judgment (LLM-powered node)?

If the user gives a vague answer twice on the same item, accept a placeholder, flag it, and move on.

End the phase with **one** confirmation: *"Here's what I captured: [bulleted summary]. Anything missing?"* Stop.

## Step 3: Initial Asset Registration (Phase 2)

**Goal:** Find the right assets in Exchange and register them in the YAML.

Asset types: **LLMs** (always ≥1), **MCP tools**, **A2A agents**.

**Asset search order** — for each capability identified in Phase 1:

1. **Private Exchange first.** If `anypoint-cli-v4` is installed: `anypoint-cli-v4 exchange asset list --search "<keywords>" --organization <orgId>`. Else if MCP `search_asset` is available: call with `assetFilters: ["llm"]` / `["mcp"]` / `["agent"]` + `exchangeScope: "Private"`.
2. **Public Exchange** if no Private match. Drop `--organization` / set `exchangeScope: "Public"`.
3. **Placeholder** if neither has it. Register as Inline with `${var}`-style URL/auth placeholders the user can fill in later.

**LLM selection is different.** Don't auto-pick. **List the LLM options** found in Exchange (e.g., `claude`, `openai`, `gemini`) and ask: *"Pick one or more, or create a new one."* Stop.

**Review with the user** before writing: *"Selected: [list]. Confirm?"* Stop.

**Register every confirmed asset** in `agent-network.yaml` + `exchange.json`. Each asset is in one of two modes — see `references/gotchas.md` § "RULE-ASSET-MODE":

- **Inline** (asset NOT in Exchange): registry entry + `context.connections` with `ref.name`.
- **Exchange** (asset already published): `exchange.json.dependencies` + `context.connections` with `ref.name` AND `ref.namespace`. **No registry entry.**

Auth always lives on `context.connections.<id>.authentication`. Parameterize URLs/secrets via `${<name>.url}` / `${<name>.apiKey}`. Add corresponding `exchange.json.metadata.variables`. Mark secrets `"secret": true`.

Per-type schema notes:

- **LLM** — Inline: `info.label`, `metadata.platform: Gemini | OpenAI | AzureOpenai`. Connection: `kind: llm` + `url` + `authentication`.
- **MCP** — Inline: `info.label`, `metadata.transport.kind` (`streamableHttp` | `sse` | `stdio`). After registering, ask the user **what `tool_name`** to call (required for the action). Ask if they know the input parameters. If yes, declare in action `inputs:`. If no, omit `inputs:` — runtime auto-discovers. **Never fabricate tool names or input schemas.**
- **A2A** — Inline: `info.label` + interfaces branch. Use `a2a` for current A2A v1.0 agents, `a2a_v03` for legacy A2A v0.3 (Agent Broker stays backward-compatible). Card under `metadata.interfaces.<branch>.card` includes `name`, `description`, `url`, `protocolVersion`, `version`, `capabilities`, `defaultInputModes`, `defaultOutputModes`, `skills`. See `references/gotchas.md` § "Registry agents" for the per-branch shape.

## Step 4: Technical Graph Definition (Phase 3 — Agent Script)

**Goal:** Translate the functional requirements into the `.agent` graph. **Brief drafts** of `system.instructions` and per-node instructions only — Phase 5 refines prose.

**Guiding principle: Graph = pre-defined rules. LLM node = reasoning.** Use the graph for anything that can be definitively hard-coded. Use an LLM-powered node (reasoning/orchestrator/generate) only for tasks that genuinely need reasoning. The graph acts as the **spine** that enforces high-level stages (e.g. Research → Draft → Review); within each stage, the LLM-powered node has autonomy.

Write the first version of the graph:

1. **Configuration.** Pick `agent_name` from the user's requirements (kebab-case; also the `.agent` filename stem and broker id, e.g. `it-help-investigation`).
2. **Trigger (entrypoint).** Each broker has exactly one trigger per declared interface. `kind: "a2a"`, `target: "brokers://<broker-id>/a2a"`, `on_message:` is a fixed `transition to`. Conditionals in the trigger are a compile error — use a router downstream.
3. **LLM-powered nodes** (pick the right type per stage):
   - **Reasoning node** (`subagent` keyword) — LLM-with-tools. Default LLM-powered type. Has built-in HITL.
   - **Orchestrator node** (`orchestrator` keyword) — LLM-with-tools, specialized for coordinating multiple actions toward a compound goal.
   - **Generate node** (`generator` keyword) — LLM-without-tools. One-shot generation, summarization, or classification with structured output.
4. **Data structure (variables).** Declare any state shared across nodes.
5. **Deterministic connections.** Every non-terminal node has a single `on_exit: -> transition to @<nodeType>.<nodeId>`. Every reachable path terminates at `echo`.
6. **Conditionals** live in **router** nodes. Routers declare `routes:` + `otherwise:` and have **no** `on_exit` (`transition to` inside router `on_exit` is a compile error). Hard constraints from Phase 1 → router conditions, not prompts. Prompts can be ignored; router conditions cannot.
7. **First node after trigger should NOT be a pass-through executor** that copies `@request.payload.message`. Reference `@request.payload.message.parts[0].text` directly downstream.
8. **Echo terminus.** Every reachable path ends in `echo` with `kind: "a2a:status_update_event"` (or `"a2a:artifact_update_event"` for artifacts). See `references/gotchas.md` § "Echo node" for the `TASK_STATE_*` enum and `a2a.*` helper rules.

Write a first version of `system.instructions` and each LLM-powered node's prompt — keep them brief; Phase 5 refines.

Update the `brokers` entry in `agent-network.yaml` to reference the new `.agent` file. For full compile-error rules see `references/gotchas.md` § "Compile-error rules". For the structural template see `references/canonical-example.md`.

## Step 5: Asset Assignment to Graph (Phase 4)

**Goal:** Assign assets from the YAML to the correct LLM-powered nodes.

**Guiding principles:**

- **Specialize each LLM-powered node in one domain.** Lump similar assets into the same node rather than spreading them.
- **Reasoning vs. Orchestrator** — pick by what's connected:
  - **Only MCP assets** on the node → **Reasoning node** (`subagent`).
  - **Any A2A assets** on the node → **Orchestrator node** (`orchestrator`).
- **≤ 4 total assets per LLM-powered node** (A2A + MCP combined). More than that → hallucinations. Split the node.
- **Principle of Least Privilege.** One node gets read-only tools; another gets write-access tools. Never combine.
- **Irreversible mutations (escalate, delete, send-to-customer, etc.) MUST be in `executor` nodes gated by `router`.** Never put them on a reasoning/orchestrator node — the LLM could invoke them bypassing the router. Idempotent updates (status updates, ticket updates) MAY live on an orchestrator if part of the compound goal.

**Action:**

1. Re-read the graph, the YAML, and the per-node instructions to refresh context.
2. For each reasoning/orchestrator node, assign assets: *"Which YAML asset does this node need?"* If none is available, ask the user to create one.
3. Bind in the `.agent` file. Each asset gets an `actions:` entry (A2A: `target` + `kind` only, no `inputs:`; MCP: `target`, `kind`, `tool_name`, optional `inputs:`). Reference from `reasoning.actions` (reasoning/orchestrator nodes) or `do: run` (executor nodes).
4. **Review with the user** once all nodes are assigned: *"Here are the asset → node assignments: [list]. Confirm?"* Stop.
5. **Ask the user to pick the LLM** for each LLM-powered node (different nodes can use different LLMs — cheap one for classification, stronger one for orchestration).
6. **Write a one-line human-readable description** of what each reasoning/orchestrator node does. Store it on the node.

For full binding rules see `references/gotchas.md`:
- **§ "Compile-error rules — action invocation"** — A2A bare reference vs `with message =` in executor; MCP `with` rules; `http_headers` implicit.
- **§ "Stage 4: Bind to nodes"** — 4-asset cap, least-privilege, action alias naming.

## Step 6: Instruction Refinement (Phase 5)

**Goal:** Refine and battle-test instructions on every LLM-powered node. **One node at a time, never batch.**

For each generate/reasoning/orchestrator node:

1. **Name the node**, once: *"Refining `classifySeverity`."* (Don't repeat which node you're on across turns — the user remembers.)
2. **Show V1** of `system.instructions` (the brief draft from Phase 3).
3. **Ask once:** *"Overall feedback? Any success criteria or few-shot examples?"* Stop.
4. **Write V2** as a numbered routine. Each step → one tool call or one output decision. No "be helpful" / "be professional".
5. **Make outputs concrete.** If the node has `outputs.properties.severity.enum`, the prompt must say *"Set severity to high when X, low otherwise"* using the enum literals exactly.
6. **Anticipate edge cases.** What if a key field is missing? Bake the answer in.
7. **Per-node contradiction test.** Does any V2 step get ruled out by deterministic graph logic? Reconcile.
8. Apply V2 to file immediately. Move to next node.

**After every node is refined:** run the **cross-node contradiction test** — does any prompt step conflict with another node's prompt or the graph? Surface conflicts to the user and resolve.

## Step 7: Final Topology Review (Phase 6)

Cleanup, then validate.

**Cleanup:**
1. Remove unresolved `{{...}}` markers, unused `exchange.json` variables.
2. Remove unused `registry` assets (not referenced by `context.connections`, actions, or LLM blocks).
3. Remove unused `context.connections` entries.
4. Remove orphaned action definitions in `.agent` file.
5. Remove empty YAML keys (`registry.llms:` with no entries → drop the key).

**Validate.** Run the build command (CLI preferred → MCP fallback → structural checklist below + install hint). Full command syntax in `references/gotchas.md` § "Step 7 — Validate / build".

**Structural checklist:**
- Every node reachable from trigger? No orphans.
- Every reachable path terminates at `echo`?
- Every `router` has `routes` (≥1) and `otherwise`?
- Every `subagent`/`orchestrator` has `reasoning.instructions` AND ≥1 action OR HITL?
- Every action referenced in nodes matches an entry in `actions:`?
- Every `${...}` variable has matching `exchange.json.metadata.variables` entry?
- Every `context.connections.<id>.ref.name` resolves to a registry entry OR `exchange.json.dependencies`?
- All A2A actions in `reasoning.actions` are bare references (no `with message =`)?
- All MCP `with` parameters reference declared `inputs:` fields?
- All echo `state` values in the allowed enum?
- Hard constraints enforced via router conditions, not prompts?
- Operational caps set: `max_number_of_loops` lowered from default 25 (e.g., 3 classification, 5–10 orchestration); `task_timeout_secs` set if calling slow downstream agents?

**Fix loop:**
- Group errors by file. Auto-fix formatting/indentation/missing required keys. For schema-required references missing, ask the user — **never auto-insert missing assets**. Loop until clean.

When clean: *"Project is validated and ready. Want to publish to Exchange and deploy to runtime?"*

## Step 8: Publish (optional)

Only if user wants to. Prereqs: authenticated CLI/MCP context; `exchange.json` has `assetVersion` and no empty `default: ""` for `secret: true` variables.

Run the publish command (CLI preferred → MCP fallback → doc link). Surface published asset URLs from the output. Full command syntax is in `references/gotchas.md` § "Step 8 — Publish".

## Step 9: Deploy (optional)

Only if user wants to. Publish must have happened first.

Ask the user: `environmentName`, `targetSpace` (private space), and any deployment properties for env-specific secrets (e.g., `--property openai.apiKey:STAGING_API_KEY`).

**One-time setup per private space:** if the target space has no gateways yet, run the gateway setup command first.

Run the deploy command (CLI preferred → MCP fallback → doc link). Surface deployment URL/ID. Full command syntax, gateway defaults, and CI flags are in `references/gotchas.md` § "Step 9 — Deploy".

---

## Workflow B — Edit an existing project

**Universal edit principles:**

- **Impact analysis first.** Identify every downstream node, expression, or connection that depends on the change. Confirm with user.
- **Minimal disruption.** Edit only what's asked. Exception: node-type changes (subagent ↔ orchestrator) when actions are added/removed.
- **Registry-first.** New assets go in `agent-network.yaml` registry/context (or `exchange.json.dependencies`) BEFORE being referenced from `.agent`.
- **Defer validation while editing.** Lint errors mid-edit are expected; validate at the end.

### B.1 — Add or swap an asset

1. Decide mode (Inline or Exchange — see `gotchas.md`).
2. **Inline:** `registry.{agents,mcps,llms}` + `context.connections.<id>` with auth + `exchange.json.metadata.variables`. **Exchange:** `exchange.json.dependencies` + `context.connections.<id>` with `ref.name` + `ref.namespace`.
3. Add `actions:` entry in the `.agent` file.
4. Reference from target node's `reasoning.actions` (subagent/orchestrator) or `do: run` (executor).
5. **Re-evaluate node type if action count changed.** Single action → `subagent`. Multi-action → `orchestrator`. Update `@<oldType>.<id>` references downstream.
6. **Cap check.** If a node now exceeds 4 actions, propose splitting.
7. **Update `system.instructions`** to explain how to use the new asset.
8. Run Step 7 (validate).

### B.2 — Change graph logic

Edit `.agent`. After any change, walk trigger → every echo and confirm:
- Every router `when:` references a real, reachable upstream output (not `@request.payload` directly).
- Hard constraints still in router conditions, not prompts.
- No node became unreachable or dead-end.
- No `transition to` in a router's `on_exit` (compile error).

Run Step 7.

### B.3 — Refine instructions

Edit `.agent` only. Apply Phase 5 contradiction tests. If user pastes a policy doc, transform into numbered routine — don't paste verbatim. Run Step 7.

### B.4 — Add or change a connection policy

Edit `agent-network.yaml`. The GA schema supports policies even though the build flow doesn't surface them.

A policy has **two parts**:
1. **Definition** — `context.policies.<policyId>`.
2. **Binding** — referenced from `context.connections.<connId>.policies.outbound` or `brokers.<brokerId>.interfaces.a2a.policies.{inbound,outbound}`. Always reference by id.

For Exchange-published policies: add to `exchange.json.dependencies` first, then bind. Run Step 7.
