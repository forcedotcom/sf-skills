# Standalone MCP configuration delivery

Use when the user wants connection configuration without a plugin. Ask for the target client and an absolute path to a **new JSON file**. Do not change an existing client configuration; generate a file the user can review and import or merge using their client's supported workflow.

The delivery workflow is client-neutral; configuration schemas still depend on the client. The current generator supports the `claude-code` profile (default, `oauth.clientId`) and an explicitly requested custom `requested` profile (`auth.CLIENT_ID`). Do not claim either schema works in every client. For another client, establish its supported schema before generating; report unsupported formats rather than guessing.

A configuration input needs only `destination`, `mcp`, and optionally `authStyle`:

```json
{
  "destination": "/absolute/user-selected/new-mcp-config.json",
  "authStyle": "claude-code",
  "mcp": {
    "serverName": "partner-tools",
    "environment": "production",
    "domain": "your-my-domain",
    "siteDeveloperName": "PartnerPortal",
    "mcpName": "PartnerTools",
    "clientId": "actual-public-eca-consumer-key"
  }
}
```

Substitute the selected environment (`production`, `developer`, `sandbox` or `scratch`), its My Domain token and the exact site/server developer names as described in the skill; the generator builds the environment's route, so users need not supply or assemble the URL. Replace the four route components with `url` only when reusing an authoritative setup URL. An explicitly selected integer `mcp.callbackPort` is supported only for `claude-code`; omit it when skipped. Plugin identity, author, icon, repository and skills are unnecessary.

Preview:

```bash
node "<skill-dir>/scripts/generate_mcp_config.mjs" /path/to/delivery-config.json
```

Create the selected file:

```bash
node "<skill-dir>/scripts/generate_mcp_config.mjs" /path/to/delivery-config.json --write
```

Inspect the written JSON: `mcpServers` wraps the selected server key; its entry contains `type: "http"`, the exact HTTPS URL and the selected public client ID in the target profile. Confirm an omitted callback port remains absent. The generator refuses existing destinations and does not write plugin files or a README. Report the file path, selected org/site/server/ECA, profile and validation results. Provide import/merge guidance for the selected client; leave OAuth, routing, tool listing and user permissions pending until verified there. Do not run `claude plugin validate` on a standalone configuration file or provide publication steps unless separately requested.
