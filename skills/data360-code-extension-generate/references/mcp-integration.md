# Using the Data 360 MCP Server (optional)

The hosted **Data 360 MCP server** (`data/data360`, GA with API v66.0+) gives the agent direct access to Data 360 Connect APIs. It is **optional** for this skill: every step below has a CLI or UI fallback in SKILL.md.

- **Set up:** follow the Salesforce hosted MCP servers docs: https://developer.salesforce.com/docs/platform/hosted-mcp-servers/overview
- **Detect:** check whether the agent has tools from a Data 360 MCP server, named `search`, `payload_examples` and `execute`. Clients add their own prefixes (for example `mcp__prod_d360_mcp__search`), so match on the suffix. Many hosts list MCP tools as **deferred** (name only, schema loaded on demand). They still count as available: load them, don't skip to the CLI fallback.

## How the server works

It exposes three meta-tools. The concrete `d360_*` tools are discovered at runtime and the list may change. For a tool named in the table below, go straight to `payload_examples`; call `search` only when that tool isn't found or you need a different one.

1. `search`: describe the intent, for example `"code extension list deploy delete"`. It returns tool families and tool names. **Send only the query.** The tool's schema lists `limit`, but the server rejects it (`JSON_PARSER_ERROR: Unrecognized field "limit"`).
2. `payload_examples`: get the parameter schema and an example for a named tool. Call it before the first `execute` of each tool in a session; don't hardcode payloads, because inputs differ by tool (DLO, DMO, query and others) and can change.
3. `execute`: run the named tool with JSON parameters.

Calls count against Connect API limits and Flex Credits. Don't poll in tight loops.

## Where it helps

| Skill phase | Intent to `search` for | Example tools (verify with `search`) | Fallback |
|---|---|---|---|
| Phase 2: discover schemas | "get DLO schema fields" | `d360_dlo_get` (one DLO per call; returns fields, status and record count) |
| Phase 2: sample input data | "query data sql" | `d360_query_sql` with `SELECT ... FROM <INPUT_DLO> LIMIT 20` | `sf api request rest .../ssot/query-sql` |
| Phase 6: redeploy | "delete data transform", "delete code extension" | transform delete tool, `d360_code_extension_delete` | UI: Data Transforms, then Code Extensions |
| Phase 6: inspect deployments | "list code extensions" | `d360_code_extension_list`, `d360_code_extension_get` | UI: Code Extensions |
| Phase 7: run and verify | "run data transform", "code extension execution history" | transform run tool, `d360_code_extension_executions_list`, `d360_code_extension_execution_get` | UI: Data Transforms → Run Now |
| Phase 7: check output | "query data", "row count" | `d360_query_sql` | UI: Data Explorer |
| Phase 7: check run logs | "query data" | `d360_query_sql` with the latest-run query on `DataCustomCodeLogs__dll` from run-logs.md | `sf api request rest .../ssot/query-sql`, UI: Data Explorer |

## Rules

- **Confirm with the user before every create, update, delete or run.** These change the org.
- Delete order for a redeploy or cleanup: **data transform first, then code extension.**
- Prefer the `sf data-code-extension ... deploy` CLI for deploys. It builds the package with Docker. Use MCP for discovery, runs, history and deletes.
- If a call fails with `Session not found` (HTTP 404), the server dropped an idle session. Retry the same call once; many clients reconnect on the next call. If it fails again, fall back to the CLI for this step, and tell the user to reconnect or restart the Data 360 MCP server in their agent's MCP settings.
- If the MCP server returns an auth error, ask the user to re-authenticate in their MCP client. Never extract or print tokens or client IDs.
