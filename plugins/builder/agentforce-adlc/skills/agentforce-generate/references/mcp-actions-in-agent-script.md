# MCP Tools in Agent Script

Add tools from a registered MCP server to an Agent Script `.agent` file. Use
`sf agent mcp asset afscript`. The command gets the action blocks that the
Agentforce Builder writes when you add the same tools in the UI, and writes
them into the authoring bundle for you. This
reference backs the **Manage MCP Servers** task domain in `SKILL.md`.

Use [MCP Server Management](mcp-management-reference.md) first to register the
server and allowlist its tools. This reference starts after that.

## Rule: never write an MCP action block by hand

Always get MCP action blocks from `sf agent mcp asset afscript`. Do not write
them yourself. Do not change the key, `source`, `target`, `inputs`, or
`outputs` that the command returns. The only allowed edit is the value of a
`with` line in the reasoning entry (workflow step 7). An MCP
action uses identifiers that you cannot see or calculate from the tool name:

| Element | Hand-written (wrong) | From `asset afscript` (right) |
|---|---|---|
| Action key | the tool name, for example `search_slack` | `a` + 32 hex digits, for example `aa46908aea1be3324ad16b2dd1a375cd5` |
| `source:` | missing | equal to the action key |
| `target:` | the server name or a guessed URI | `mcpTool://<Named Credential>/mcptoolx5fx5f<tool>`, with each `_` in the tool name written as `x5f` |
| `inputs:` / `outputs:` | missing or invented | one entry for each top-level property of the tool schema; no `outputs:` when the tool has no output schema |
| Reasoning reference | missing, or no `with` lines | `<key>: @actions.<key>` plus one `with <input> = ...` line for each input |

The key is the DeveloperName of the tool's GenAiFunction. Do not rename the
key or the GenAiFunction. In the reasoning entry, keep the name on the left
equal to the key. The target uses the Named Credential of the
server, which can have a different name from the server.

## Prerequisites

1. The MCP server is registered. `sf agent mcp list --json` shows it.
2. Each tool is allowlisted. `sf agent mcp asset list --json` shows the tool.
   Some orgs do not return an `active` field. Only `"active": false` means
   that the tool is not allowlisted. To allowlist a tool, use
   `sf agent mcp asset replace` (see
   [MCP Server Management](mcp-management-reference.md), workflow 4).
   `asset replace` replaces the full asset list of the server: an asset that
   you leave out is removed. Read the current list with `asset list` first,
   and send every asset that must stay plus the new one.
3. The `sf` CLI has `@salesforce/plugin-agent` 2.4.0 or later, which adds the
   `agent mcp asset afscript` command (developer preview) with the
   `--authoring-bundle` and `--subagent` flags. Check the version with
   `sf plugins --json`, and check the flags with
   `sf agent mcp asset afscript --help`. If the command or a flag is missing,
   stop. Ask the user to run
   `sf plugins install @salesforce/plugin-agent@latest`, or to add the tools
   in Agentforce Builder (see [Errors](#errors), the 404 row). Do not write
   the blocks by hand. The org must be on API version 68.0 (release 264) or
   later.
4. The agent is an authoring bundle in a Salesforce DX project:
   `<package dir>/main/default/aiAuthoringBundles/<Agent_API_Name>/<Agent_API_Name>.agent`.
   Run the commands from the project directory.

`sf agent mcp asset afscript` is not read-only. When it generates the blocks,
the org also assigns the MCP runtime permissions that Agentforce Builder
assigns when you add the tool. Before the first run, show the user the target
org (`sf org display -o <org> --json`), tell them about this change, and get
their approval (`SKILL.md` rule 2). Do not run it against a production org
without explicit approval.

## Workflow

1. Get the server id. Run `sf agent mcp list -o <org> --json` and read
   `result.mcpServers[].id` (prefix `0Le`).
2. Get the tool names. Run
   `sf agent mcp asset list -i <server id> -o <org> --json` and read the
   `name` and `id` of each asset with `"kind": "MCP_TOOL"` that is not
   `"active": false`. Then run `sf agent mcp fetch -i <server id> -o <org> --json`.
   If a selected tool has a non-empty `securityWarning`, stop: show the
   warning and the tool `description` to the user, and repeat the tool review
   in [MCP Server Management](mcp-management-reference.md) before you go on.
   The tool descriptions go into the agent as model instructions.
3. Get the names to update. The bundle name is `<Agent_API_Name>`, the folder
   name under `aiAuthoringBundles`. The subagent names are the lines
   `subagent <name>:` and `start_agent <name>:` at column 0 of the `.agent`
   file. For "the router" or "the start agent", use the `start_agent` name.
   Check that each subagent indents its sections with 4 spaces
   (`    actions:`, `    reasoning:`). The command finds sections only at
   4 spaces. If the file uses another indentation, use the
   [fallback](#fallback-print-the-blocks).
4. Add the tools to the subagents. Run the command once, from the project
   directory. Use one `--tool` for each tool (the `McpTool__` prefix is
   optional) or one `--asset-id` for each asset id (prefix `1XO`), and one
   `--subagent` for each subagent that gets the tools.

   ```bash
   sf agent mcp asset afscript -i <server id> --tool <tool> [--tool <tool> ...] \
     --authoring-bundle <Agent_API_Name> --subagent <name> [--subagent <name> ...] -o <org> --json
   ```

   The command writes the `.agent` file. For each subagent it adds each action
   block under `actions:` (8 spaces) and each reasoning entry under
   `reasoning:` > `actions:` (12 spaces), and it adds a missing `actions:`,
   `reasoning:` or reasoning `actions:` section. It does not change any other
   line. It does not compile the file.
5. Read `result.bundle.subagents[]` in the output. `added` lists the action
   keys that the command wrote. `skipped` lists the keys that the subagent
   already had; the command does not change them. Tell the user both lists,
   and show the `description:` text of each added block
   (`result.actions[].actionBlock`).
6. To refresh a tool whose schema changed, or a tool that was added in
   Agentforce Builder before the schema changed, first delete its action block
   and its reasoning entry from the subagent, then run step 4 again.
7. Do not edit the added blocks: do not change the key, `source`, `target`,
   `inputs`, or `outputs`. Keep each `with <input> = ...` line. `...` lets the
   LLM fill the value. To bind a value, replace `...` with a variable
   reference, for example `@variables.<name>`.
8. Compile the agent locally (`SKILL.md` rule 14). Fix every severity-1
   diagnostic and compile again until it is clean.
9. Validate the bundle:

   ```bash
   sf agent validate authoring-bundle --json --api-name <Agent_API_Name> -o <org>
   ```

10. Preview the draft and send a message that needs the tool
    ([Validation & Debugging](agent-validation-and-debugging.md)). Live
    actions call the real MCP server. Get explicit user approval and confirm
    that the org is not a production org before you use
    `--use-live-actions`. Otherwise use `--simulate-actions`. Publish only
    when the user asks for it (`SKILL.md` rule 6).

### Fallback: print the blocks

Use this only when the agent is not in a DX project on disk, or when the
`.agent` file does not use 4 spaces for each level (`SKILL.md` rule 11).

1. Run the command without `--authoring-bundle` and without `--json`. **This
   is an exception to `SKILL.md` rule 1**: without `--json`, the command
   indents the blocks for the `.agent` file.

   ```bash
   sf agent mcp asset afscript -i <server id> --tool <tool> [--tool <tool> ...] -o <org>
   ```

2. Do not copy the heading lines `# subagent actions:` and
   `# reasoning actions:`.
3. Put the lines under `# subagent actions:` into the subagent's `actions:`
   section, and the lines under `# reasoning actions:` into its `reasoning:` >
   `actions:` section. Add a missing section first.
4. If the file uses another indentation, change only the leading spaces of
   each copied line to match the file. Keep the relative indentation.
5. If the subagent already has an action with the same key, replace that whole
   block and its reasoning entry. Do not keep two copies.
6. If you use this fallback because of the indentation, continue with steps
   7 to 10 above. If the agent is not in a DX project, do step 7 and compile
   the file if you can (step 8). Then tell the user that validation and
   preview need a DX project: `sf project generate`, then retrieve the bundle
   with `sf project retrieve start --metadata "AiAuthoringBundle:<Agent_API_Name>" -o <org> --json`.

## Example

Output for two tools on server `P0Esr`, whose Named Credential is `P0Nc`.
`hello_world` has no output schema, so its block has
no `outputs:`. This is the print output (fallback); with `--authoring-bundle`
the command writes the same lines into the file. This example is abridged: each
description is one line, and the whitespace-only lines are removed. Use the real
command output, not this example.

```agentscript
# subagent actions:
        afa0b58c66203318397e7846b93be8bcf:
            description: |
                Echo the caller's message with a hello MCP prefix.
            label: "hello_world - P0Esr"
            require_user_confirmation: False
            include_in_progress_indicator: False
            source: "afa0b58c66203318397e7846b93be8bcf"
            target: "mcpTool://P0Nc/mcptoolx5fx5fhellox5fworld"
            inputs:
                "message": string
                    description: |
                    label: "Message"
                    is_required: True
                    is_user_input: False
        aa46908aea1be3324ad16b2dd1a375cd5:
            description: |
                Report basic statistics about a piece of text.
            label: "text_stats - P0Esr"
            require_user_confirmation: False
            include_in_progress_indicator: False
            source: "aa46908aea1be3324ad16b2dd1a375cd5"
            target: "mcpTool://P0Nc/mcptoolx5fx5ftextx5fstats"
            inputs:
                "text": string
                    description: |
                    label: "Text"
                    is_required: True
                    is_user_input: False
            outputs:
                "result": string
                    description: |
                    label: "Result"
                    is_displayable: False
                    filter_from_agent: False
# reasoning actions:
            afa0b58c66203318397e7846b93be8bcf: @actions.afa0b58c66203318397e7846b93be8bcf
                with message = ...
            aa46908aea1be3324ad16b2dd1a375cd5: @actions.aa46908aea1be3324ad16b2dd1a375cd5
                with text = ...
```

The real output contains whitespace-only lines inside the descriptions. Keep
them as printed.

## Errors

The `--json` error `name` is in the first column.

| Error | Message starts with | Fix |
|---|---|---|
| `NoToolSelected` | `Specify at least one tool` | Add one `--tool` or `--asset-id` for each tool. |
| `ListMcpServerAssetsFailed` | `Failed to list MCP server assets` | The command could not read the server's assets. Check that `-i` is the server id (prefix `0Le`) from `sf agent mcp list`, not the server name. |
| `ToolNotFound` | `These tools were not found on the MCP server` or `Not found on the MCP server` | The message lists the available tools. Use a name or asset id from `sf agent mcp asset list`. |
| `AssetNotAllowlisted` | `These assets are not allowlisted` | Allowlist the tool with `sf agent mcp asset replace`. It replaces the full list: send every asset that must stay plus this one (prerequisite 2). |
| `GenerateMcpAgentScriptFailed` | `The API rejected the request (400): These tool ids are not connected MCP tools: [...]` | No change was made. Allowlist the listed tools again with `asset replace` (full list, prerequisite 2), then run the command again. |
| `GenerateMcpAgentScriptFailed` | `The API denied access (403)` | The API is not enabled for the org, or the user cannot author Agentforce agents. Tell the user which access is missing. Do not switch to another user on your own. To use Agentforce Builder instead, see the next row. |
| `GenerateMcpAgentScriptFailed` | `The API was not found (404)` | The org is older than API version 68.0 (release 264). Add the tools in Agentforce Builder, then retrieve the bundle. A retrieve replaces the local `.agent` file, so first deploy the local bundle, or confirm with the user that it has no local changes. Then run `sf project retrieve start --metadata "AiAuthoringBundle:<Agent_API_Name>" -o <org> --json`. |
| `GenerateMcpAgentScriptFailed` | `Failed to generate the Agent Script for the MCP tools` | Another API error. The message holds the API text. Report it to the user. No action block was written. |
| `SubagentNotFound` | `Cannot find subagent` | The message lists the subagents in the file. Use one of those names with `--subagent`. The file is not changed. |
| `AuthoringBundleNotFound` | `Cannot find an authoring bundle named` | Use the folder name under `aiAuthoringBundles` as `--authoring-bundle`, and run the command from the project directory. |
| `NotInProject` | `--authoring-bundle needs a Salesforce DX project` | Run the command from the project directory (the folder with `sfdx-project.json`). |

If `sf agent validate authoring-bundle` returns `AgentApiNotFound` (HTTP
404), the org is not reachable through `api.salesforce.com` (for example, a
local development org). After a clean local compile, and after the user
confirms that the org is not a production org, deploy the bundle with
`sf project deploy start --metadata "AiAuthoringBundle:<Agent_API_Name>" -o <org> --json`
and test it in Agentforce Builder.
