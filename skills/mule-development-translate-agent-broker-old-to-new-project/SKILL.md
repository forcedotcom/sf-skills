---
name: translate-agent-broker-old-to-new-project
description: "Convert a MuleSoft Agent Network V1 project (`schemaVersion: 1.0.0`) into a V2 project (`agentNetwork: 2.0.0`). Each V1 broker becomes a V2 broker with one orchestrator node — no graph splitting, no prompt rewriting. Use when the user asks to upgrade, convert, migrate, translate, or port an Agent Network / Agent Broker / Daisy planner from V1 to V2, or whenever the working folder contains a V1 `agent-network.yaml`."
license: Apache-2.0
metadata:
  author: mulesoft-agent-broker-team
  version: "1.0.0"
---

# MuleSoft Agent Broker V1 to V2 Converter

Converts an Agent Network V1 project (schema `1.0.0`) into V2 (schema `2.0.0`) by producing a brand-new project folder. The conversion is intentionally simple: every V1 broker becomes a V2 broker backed by an Agent Script `.agent` file with exactly one **orchestrator** node. Routing, classification, and conditional logic that V1 stuffed into a single LLM prompt remain inside that orchestrator's `system.instructions` — the upgrade does not break the prompt apart into multiple nodes.

Preserve the user's wording. Do not improvise or "improve" the source instructions. Treat the V1 file as the source of truth and only change what V2 actually requires.

If the user wants a richer multi-node graph (split deterministic routing into `router` nodes, move side-effects into `executor` nodes, separate cheap summary work into `generator` nodes), point them at **`build-agent-broker-project`** as the natural next step.

## When to use

- Convert / upgrade / migrate / port an Agent Network or Agent Broker from V1 to V2.
- The user mentions `schemaVersion: 1.0.0` and wants `agentNetwork: 2.0.0`.
- Working folder contains a V1 `agent-network.yaml` and `exchange.json`.

For general V2 questions (without converting), point at the builder skill instead.

## References

- **`references/v1-example.md`** — canonical V1 input (`customer-onboarding-v1`).
- **`references/v2-example.md`** — canonical V2 output for that input. When in doubt about formatting, mirror this.
- **`references/v2-template.agent`** — the orchestrator template to fill in for Step 3c.

## Workflow

1. **Validate input** — Step 1.
2. **Choose output location** — Step 2.
3. **Read source files in full** — V1 `agent-network.yaml` + `exchange.json` end-to-end.
4. **Translate** — Step 3 (sub-steps 3a/3b/3c).
5. **Write output folder** with suffix `_v2_conversion` — Step 4.
6. **Report** the new path and what was converted — Step 5.

## Step 1: Validate input

Verify the working folder is actually a V1 Agent Network project. **Do not run the conversion against the wrong folder.**

1. Determine working folder. If unclear, ask.
2. Confirm both files exist: `agent-network.yaml` (or `.yml`) and `exchange.json`.
3. Read the YAML — must have `schemaVersion: 1.0.0` at top level. (V2 uses `agentNetwork: 2.0.0`.)
4. Read `exchange.json` — must have `"classifier": "agent-network"`. (V2 uses `"agentic-network"`.)

If any check fails, **stop and ask the user to point you at the correct folder**:

> I don't see a V1 Agent Network project in this folder. Looking for `agent-network.yaml` with `schemaVersion: 1.0.0` and `exchange.json` with `"classifier": "agent-network"`. What folder should I convert?

## Step 2: Choose output location

The new folder name is `<original>_v2_conversion`. Use AskUserQuestion to offer:
- Same parent directory as source (default).
- Specific path the user provides.

**Don't silently overwrite.** If the target exists, ask whether to overwrite or pick a different name.

## Step 3: Translate

The conversion has three outputs derived from the same V1 source.

### 3a. Build the V2 `agent-network.yaml`

V2 has these top-level sections: `agentNetwork`, `info`, `registry`, `context`, `brokers`. Map V1 → V2:

| V1 location | V2 location | Notes |
| --- | --- | --- |
| `schemaVersion: 1.0.0` | `agentNetwork: 2.0.0` | Required string. |
| `label` (top level) | `info.label` | Required. |
| (none in V1) | `info.version` | Required. Use `1.0.0`. |
| `brokers.<id>.card.description` | `info.description` | If present, lift the broker's description into `info`. |
| `agents.<id>` | `registry.agents.<id>` | See **Agent translation**. |
| `mcpServers.<id>` | `registry.mcps.<id>` | V1 says `mcpServers`, V2 says `mcps`. |
| `llmProviders.<id>` | `registry.llms.<id>` | Move card-less LLM info under `metadata`. |
| `connections.<id>` | `context.connections.<id>` | See **Connection translation**. |
| `brokers.<id>` | `brokers.<id>` + `./brokers/<id>.agent` | See **Broker translation**. |

#### Agent translation (`agents` → `registry.agents`)

For each V1 agent:
- Lift `label` into `info.label`.
- Keep `metadata.platform` as-is. **Drop `metadata.protocol`** — GA replaces it with `metadata.interfaces`.
- Build `metadata.interfaces.a2a_v03.card` — V1 agents were A2A v0.3-based, so the conservative conversion places them in the `a2a_v03` (back-compat) branch. The card retains `url: ${<refName>.url}`, `protocolVersion: 0.3.0`, `version: 1.0.0`, `capabilities.pushNotifications: false`, modes = `[application/json, text/plain]`. Defaults for `name` and `description` come from the agent's V1 `label`.
- The broker itself emits A2A v1.0 — keep `brokers.<id>.interfaces.a2a` (NOT `a2a_v03`).
- One `skills` entry per agent. `id` = `<agentName>-<verb>` (e.g. `workday-create-record`); copy purpose into `name` and `description`.

Don't invent capabilities V1 didn't claim. If V1 doesn't say `pushNotifications: true`, leave it `false`.

#### MCP translation (`mcpServers` → `registry.mcps`)

For each V1 MCP server:
- Lift `label` into `info.label`. Add a short `info.description` if you can derive one safely from the V1 broker's instructions.
- Keep `metadata.transport` exactly as-is.
- Add `metadata.tools` array. For each tool the V1 broker calls (look at `brokers.tools[*].mcp.allowed` for the canonical name), add an entry with `name`, `description`, and a minimal `inputSchema` (`type: object`, plus `properties` for arguments you can confidently infer from the broker's instructions). **If you can't determine the schema, leave `properties` empty rather than fabricate.**

#### LLM translation (`llmProviders` → `registry.llms`)

For each V1 LLM provider:
- Lift `label` into `info.label` and `description` into `info.description`.
- Keep `metadata.platform`.
- Add `metadata.models` as a list. Include the model V1 actually uses (`spec.llm.configuration.model`) plus one obvious sibling. Don't pad speculatively.

#### Connection translation (`connections` → `context.connections`)

V1's flat `connections` object has each connection with `kind`, `ref.name`, `spec.url`, optional `spec.configuration` for auth. V2 keeps the idea but URL moves up out of `spec`.

```yaml
# V1
WorkdayAgentTestConnection:
  kind: agent
  ref:
    name: WorkdayAgentTest
  spec:
    url: https://...
```
becomes
```yaml
# V2
workdayAgentConnection:
  kind: a2a            # V1 'agent' becomes V2 'a2a'
  ref:
    name: workdayAgent
  url: ${workdayAgent.url}
```

Mapping rules:
- `kind: agent` (V1) → `kind: a2a` (V2). `kind: mcp` and `kind: llm` stay.
- For LLM connections, move auth into a top-level `authentication` block: `kind: apiKey`, `apiKey: ${<llmName>.apiKey}`. Don't keep V1's `spec.configuration` shape.
- Replace hardcoded URLs with `${<refName>.url}` variables. The actual URL value goes into `exchange.json`.
- **Connection IDs are not format-restricted by the V2 schema**: `context.connections.<id>` keys accept any valid YAML identifier (camelCase, snake_case, or kebab-case all validate). Convert V1 PascalCase like `WorkdayAgentTestConnection` into a readable id — this converter uses snake_case (`workday_agent_connection`) for consistency, but that's a convention, not a lint rule. The one hard requirement: the id must match the `.agent` target (`a2a://<id>`, `mcp://<id>`, `llm://<id>`) exactly.
- Registry `ref.name` values (agents/mcps/llms) typically become camelCase in V2 (e.g. `workdayAgent`).

#### Broker translation

V1 puts the broker's A2A card and the orchestrator's prompt (`spec.instructions`) in one block. V2 splits them:
- A2A card stays in `agent-network.yaml` under `brokers.<broker-id>.interfaces.a2a.card`.
- Orchestrator prompt moves into `./brokers/<broker-id>.agent`.

V2 broker entry (GA, A2A v1.0 — broker IS the endpoint, so its card omits `url` and `protocolVersion`):
```yaml
brokers:
  <broker-id>:
    kind: AgentScript
    implementation: ./brokers/<broker-id>.agent
    interfaces:
      a2a:
        card:
          name: <copied from V1 card.name>
          description: <copied from V1 card.description>
          version: 1.0.0
          capabilities:
            streaming: false
            pushNotifications: <copied from V1 card.capabilities.pushNotifications, default false>
          defaultInputModes: [application/json, text/plain]
          defaultOutputModes: [application/json, text/plain]
          skills:
            - id: <copied, lowercased / kebab-cased>
              name: <copied>
              description: <copied>
              tags: <copied>
              examples: <copied if present>
              inputModes: [application/json, text/plain]
              outputModes: [application/json, text/plain]
```

**Broker IDs are not format-restricted by the V2 schema**: the key under `brokers:` accepts any valid YAML identifier (snake_case, kebab-case, and camelCase all validate). Convert V1 PascalCase like `CustomerOnboardingBrokerTest` into a readable id — this converter uses snake_case (`customer_onboarding`) for consistency, but that's a convention, not a lint rule. The `.agent` *filename* is independent (e.g. `./brokers/customer-onboarding.agent`). The one hard rule: match the trigger `target: "brokers://<broker-id>/a2a"` to the YAML broker key **exactly**.

### 3b. Build the V2 `exchange.json`

Take V1's `exchange.json` and:
- Change `"classifier": "agent-network"` → `"classifier": "agentic-network"`.
- Update `name`, `assetId`, `version` to reflect the V2 conversion (e.g. `-v2` suffix).
- Add a `description` field.
- For every connection that points to an external URL in V1, add `metadata.variables.<refName>.url` with the URL as `default`. This is what makes the `${<refName>.url}` references resolve.
- Preserve any existing variables (e.g. `gemini.apiKey`).
- Mark API keys `"secret": true`. Mark URLs `"secret": false`.

### 3c. Build the Agent Script `<broker-id>.agent`

Use **`references/v2-template.agent`** as the structural skeleton and fill in the placeholders. Critical naming and content rules:

**Action naming:**
- For each V1 linked agent, create one `a2a:send_message` action. Convert the agent name to snake_case (e.g. `WorkdayAgentTest` → `workday_agent`).
- For each V1 MCP tool listed in `brokers.tools[*].mcp.allowed`, create one `mcp:tool` action. Pick a snake_case action id reflecting the tool's purpose (e.g. `SlackMcpServer.send_status_update` → `send_slack_status_update`). **Always preserve the original `tool_name` exactly.**
- **Don't add `inputs:` to MCP actions.** V1 has no tool input schemas. The V2 runtime auto-discovers a tool's arguments. Inferring `inputs:` from the orchestrator's prose is fabrication and produces a wrong schema.
- The only time you'd add `inputs:` is to *fix* or *default* an argument value via `with` later (e.g. pinning a `channel_id`). The conversion shouldn't introduce that.

**Reasoning action aliases:**
- Inside `reasoning.actions`, use short readable aliases (e.g. `workday`, `salesforce`, `slack_update`) rather than reusing the action id verbatim. Makes orchestrator instructions more human-readable.

**Prompt preservation:**
- Copy `spec.instructions` from V1 verbatim into the orchestrator's `system.instructions`.
- Mechanical edits only:
  - Replace dotted MCP tool names with the new V2 action alias if the prompt names a tool.
  - Tighten obvious typos only if they'd confuse (e.g. `"this a long running task"` → `"this is a long running task"`). When in doubt, leave the user's wording alone.
- **Don't split the prompt into multiple nodes.** Don't add routers, executors, or generators. The whole orchestration runs inside one orchestrator — that's the explicit constraint.

## Step 4: Write output

```
<chosen_path>/<original_folder_name>_v2_conversion/
├── agent-network.yaml
├── exchange.json
└── brokers/
    └── <broker-id>.agent
```

Use `mkdir -p` for directories and Write for files. Skip `.mvn`, `.vscode`, `.cursor`, `target/` and other IDE folders — they aren't part of the project spec. If the destination exists, ask before overwriting.

After writing, list the created files.

## Step 5: Report

Tell the user:
- Full path to the new folder.
- Broker name and orchestrator node id.
- One-line note: this is a simple V1→V2 translation with one orchestrator node; for a richer multi-node graph (router/generator/executor split), use `build-agent-broker-project`.

## Common mistakes to avoid

- **Don't** keep `schemaVersion: 1.0.0` — V2 uses `agentNetwork: 2.0.0`.
- **Don't** keep V1's `agent-network` classifier — V2 uses `agentic-network`.
- **Don't** invent extra nodes (router, generator, executor). The user wants a single orchestrator.
- **Don't** rewrite the user's prompt to "improve" it.
- **Don't** hardcode URLs — parameterize via `${<name>.url}` and put the value in `exchange.json`.
- **Don't** forget `info.version` (required in V2, absent in V1).
- **Don't** put auth blocks inside the registry — auth lives on `context.connections.<name>.authentication`.
- **Don't** add `inputs:` to MCP actions during V1→V2 conversion. V1 has no schemas, so any `inputs:` block is guessed from prose.
- **Don't** emit `metadata.protocol` or flat `metadata.card` on registry agents — GA uses `metadata.interfaces.<branch>.card`. Place V1-converted agents under `a2a_v03` (back-compat); the broker itself uses `a2a` (v1.0).
- **Don't** emit `kind: "a2a:response"` with a nested `task: a2a.task({...})` in echo nodes — GA uses `kind: "a2a:status_update_event"` (state + message) or `kind: "a2a:artifact_update_event"` (artifact + append/lastChunk). State values are `TASK_STATE_*` constants.
- **Don't** emit `# @dialect: AGENTFABRIC=0.1-BETA` or `# @dialect: AGENTFABRIC=0.1` — use `# @dialect: AGENTFABRIC=1.0` for GA.
