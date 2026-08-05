# MCP Server Management Reference

Register, configure, and manage Model Context Protocol (MCP) servers in the
Salesforce API Catalog using the `sf agent mcp` CLI commands. This reference
backs the **Manage MCP Servers** task domain in `SKILL.md`.

MCP servers expose **assets** — tools, prompts, and resources — that become
available as agent actions once whitelisted. This reference covers server
registration, lifecycle management, and interactive asset whitelisting.

**Requires:** `sf` CLI with the `agent mcp` plugin installed. Verify with
`sf help agent mcp`. If the command is missing, check `sf version`, run
`sf update`, and confirm plugin availability with `sf plugins`.

**Developer preview:** Every `sf agent mcp` command is currently in developer
preview. Each response includes a `warnings` array containing a preview notice
(`"This command is currently in developer preview..."`). Parse `result` as usual
and ignore the warning for automation, but be aware flag/output shapes may change.

**ID formats (observed):** Server IDs use the `0Le` prefix (e.g. `0LeSB000000JoFd`),
and asset IDs use the `1XO` prefix (e.g. `1XOSB0000008riJ`). The `0XSxx…`/`0YSxx…`
placeholders in older examples are illustrative only.

## Core Principles

1. **Always `--json`** — Include `--json` on every `sf agent mcp` command to get
   structured output. (Consistent with Rule 1 in `SKILL.md`.)
2. **Verify target org** — Before any operation, confirm a target org is set with
   `sf config get target-org --json`. If none, ask the user to run
   `sf config set target-org <alias>`. (Consistent with Rule 2.)
3. **Interactive approval** — When whitelisting tools, display metadata for each
   tool individually and wait for user approval before activating.
4. **Security first** — For OAuth servers, handle client secrets securely (stdin
   piping) and warn about credential exposure. Flag destructive or broadly-scoped
   tools before activation.

## Task Workflows

### 1. Register a New MCP Server

When the user wants to register/create/add an MCP server:

#### Required Information

Gather from the user (ask if not provided):

- **Server name** (`-n, --name`) — Unique identifier
- **Server URL** (`--server-url`) — Endpoint URL
- **Target org** (`-o, --target-org`) — Org alias or username
- **Label** (optional, `--label`) — Human-readable display name
- **Description** (optional, `--description`) — Server purpose
- **Authentication type** (`--auth-type`) — `NO_AUTH` (default) or `OAUTH`

If `--auth-type OAUTH`, also gather:

- **Identity provider** (`--identity-provider`)
- **Client ID** (`--client-id`)
- **Client secret** (`--client-secret`) — Handle securely via stdin
- **Scope** (`--scope`)

#### Execution Steps

1. **Verify target org is set**

   ```bash
   sf config get target-org --json
   ```

   If no target org, ask user to set one with `sf config set target-org <alias>`

2. **Gather required information** — Ask for any missing required fields

3. **Create the server**

   **NO_AUTH example:**

   ```bash
   sf agent mcp create -n MyServer --server-url https://mcp.example.com/mcp -o myOrg --json
   ```

   **OAUTH example (secure client secret handling):**

   ```bash
   echo "secret-value" | sf agent mcp create -n MyServer --server-url https://mcp.example.com/mcp --auth-type OAUTH --identity-provider MyIdp --client-id abc123 --client-secret - --scope "read write" -o myOrg --json
   ```

4. **Extract server ID** — Parse the JSON response and extract `result.server.id`
   (format: `0LeSB000000Jp5F`). Note the ID is under `result.server`, not
   `result` directly. This ID is required for all subsequent operations. The
   response also includes `result.assets` (discovered but not yet registered —
   they have `id: null` and `status: "NOT_REGISTERED"` until you activate them).

5. **Display confirmation** — Show the user:
   - Server name
   - Server ID
   - Server URL
   - Connection status

6. **Offer next steps**
   - "Would you like to fetch and whitelist tools from this server now?"
   - If yes, proceed to **Fetch and Whitelist Assets** workflow

### 2. List MCP Servers

When the user wants to see all registered MCP servers:

1. **Verify target org**

   ```bash
   sf config get target-org --json
   ```

2. **List servers**

   ```bash
   sf agent mcp list -o myOrg --json
   ```

   **Optional filters:**
   - By status: `--status ACTIVE` or `--status DISCONNECTED`
   - By type: `--type EXTERNAL`
   - By label: `--label "My Server"`

3. **Display results** — The server array is under `result.mcpServers`. Show a
   table or list with: Server name, Server ID, Status (ACTIVE/DISCONNECTED),
   Server URL, Label. Auth type is under each server's `authorization.authType`.

4. **Offer actions** — Ask if the user wants to get details on a specific server,
   fetch assets, or update/delete a server

### 3. Get Server Details

When the user wants details on a specific server:

1. **Verify target org**

   ```bash
   sf config get target-org --json
   ```

2. **Get server details**

   ```bash
   sf agent mcp get -i 0XSxx0000000001 -o myOrg --json
   ```

3. **Display details** — Name, label, description, server URL, status,
   authentication type (`authorization.authType`), and created/modified
   timestamps. Audit fields are IDs only (`createdById`/`lastModifiedById`) —
   there are no user-name objects. For OAUTH servers, `authorization.scope` and
   `authorization.identityProvider` (a token endpoint URL) are also present.

### 4. Fetch and Whitelist Assets (Interactive Tool Approval)

This is the **core whitelisting workflow** with interactive tool-by-tool approval.

1. **Verify target org**

   ```bash
   sf config get target-org --json
   ```

2. **Fetch live assets from the server**

   ```bash
   sf agent mcp fetch -i 0XSxx0000000001 -o myOrg --json
   ```

3. **Parse the response** — Extract the list of assets from `result.assets`.
   Each asset includes: `id`, `name` (e.g., `McpTool__getTickets`), `label`,
   `kind` (`MCP_TOOL`/`MCP_PROMPT`/`MCP_RESOURCE`), `active` (boolean),
   `availableAsAgentAction` (boolean), `description`, and `status`
   (`IN_SYNC`/`NOT_REGISTERED`). Note: `inputSchema`, `outputSchema`, and
   `annotations` are NOT guaranteed to be present (the live server did not
   return them) — handle their absence gracefully.

4. **Interactive tool review** — For EACH tool in the list:

   a. **Display tool metadata clearly** (only render schema/annotations fields
   if the server actually returned them — they are often absent):

   ```text
   Tool: <name> (<label>)
   Kind: <kind>
   Description: <description>

   Input Schema:
   <formatted JSON inputSchema> (or "Not specified")

   Output Schema:
   <formatted JSON outputSchema> (or "Not specified")

   Annotations:
   <formatted JSON annotations> (or "None")

   Current Status: <active ? "ACTIVE" : "INACTIVE">
   ```

   b. **Ask for approval:**

   ```text
   Do you want to ACTIVATE this tool? (yes/no/skip)
   - yes: Add to allowlist
   - no: Exclude from allowlist (deactivate if currently active)
   - skip: Keep current status unchanged
   ```

   c. **Record the user's choice** — Build an array of approved assets

5. **Build the asset allowlist** — Create a JSON payload with the approved assets:

   ```json
   {
     "assets": [
       { "name": "McpTool__add", "active": true },
       { "name": "McpTool__subtract", "active": false }
     ]
   }
   ```

6. **Replace the server's asset allowlist** — Pass the payload inline via
   `--assets`, or pipe it through stdin with `--assets -`. No temp file needed.

   Inline (small payloads):

   ```bash
   sf agent mcp asset replace -i 0XSxx0000000001 \
     --assets '{"assets":[{"name":"McpTool__add","active":true},{"name":"McpTool__subtract","active":false}]}' \
     -o myOrg --json
   ```

   Via stdin (larger payloads):

   ```bash
   echo '<json payload>' | sf agent mcp asset replace -i 0XSxx0000000001 --assets - -o myOrg --json
   ```

7. **Confirm results** — The replace response returns the full resulting asset
   set under `result.assets` (no `assetsUpdated` count field). Derive counts by
   inspecting each asset's `active` flag in the response, e.g.:

   ```text
   Asset Allowlist Updated:
   - Active: <count of active:true> tools
   - Inactive: <count of active:false> tools
   ```

#### Notes on Asset Replacement

- **Full replacement semantics** — `sf agent mcp asset replace` is a FULL
  replacement, not a merge. Assets not in the payload are removed/deactivated.
- **Always include the full desired state** — If a tool should remain active,
  include it in the payload with `"active": true`.
- **Read current state first** — Use `sf agent mcp fetch` or
  `sf agent mcp asset list` to see current assets before replacement.

### 5. List Assets for a Server

When the user wants to see the current asset allowlist:

1. **Verify target org**

   ```bash
   sf config get target-org --json
   ```

2. **List assets**

   ```bash
   sf agent mcp asset list -i 0XSxx0000000001 -o myOrg --json
   ```

3. **Display results** — Show each asset with: Name, Kind (MCP_TOOL, MCP_PROMPT,
   MCP_RESOURCE), Active status, Available as agent action

### 6. Update MCP Server

When the user wants to modify server configuration:

#### Updatable Fields

- `--label` — New display label ⚠️ (observed not to persist — see command note)
- `--description` — New description (persists)
- `--server-url` — New endpoint URL ⚠️ (observed not to persist — see command note)
- `--auth-type` — Change authentication (requires full OAuth params if switching
  to OAUTH)

⚠️ In live preview-CLI testing, only `--description` persisted; `--label` and
`--server-url` returned success but were silently ignored. Always confirm with a
follow-up `get`. See the `sf agent mcp update` command reference below for details.

#### Execution Steps

1. **Verify target org**

   ```bash
   sf config get target-org --json
   ```

2. **Gather update fields** — Ask which fields to change

3. **Update the server**

   ```bash
   sf agent mcp update -i 0XSxx0000000001 --label "New Label" --description "Updated description" -o myOrg --json
   ```

   **Switching to OAuth:**

   ```bash
   echo "secret" | sf agent mcp update -i 0XSxx0000000001 --auth-type OAUTH --identity-provider MyIdp --client-id abc --client-secret - --scope "read write" -o myOrg --json
   ```

4. **Confirm results** — Display updated server details

### 7. Delete MCP Server

When the user wants to remove a server registration:

1. **Verify target org**

   ```bash
   sf config get target-org --json
   ```

2. **Get server details first** — Show what will be deleted

   ```bash
   sf agent mcp get -i 0XSxx0000000001 -o myOrg --json
   ```

3. **Confirm deletion** — Ask user:

   ```text
   Are you sure you want to delete this MCP server?
   - Name: <name>
   - URL: <url>
   - This action is PERMANENT and cannot be undone.

   Confirm deletion? (yes/no)
   ```

4. **Delete the server**

   ```bash
   sf agent mcp delete -i 0XSxx0000000001 -o myOrg --no-prompt --json
   ```

5. **Confirm deletion** — Display success message

## Command Reference

### sf agent mcp create

**Purpose:** Register a new MCP server in the API Catalog

**Required Parameters:**

- `-n, --name <value>` — Unique server name. It cannot contain spaces, has to start with a letter and can only contain alphanumeric characters.
- `-o, --target-org <value>` — Target org alias/username
- `--server-url <value>` — MCP server endpoint URL

**Optional Parameters:**

- `--label <value>` — Human-readable display name
- `--description <value>` — Server description
- `--auth-type <OAUTH|NO_AUTH>` — Default: `NO_AUTH`
- `--identity-provider <value>` — OAuth IdP (required with `OAUTH`)
- `--client-id <value>` — OAuth client ID (required with `OAUTH`)
- `--client-secret <value>` — OAuth secret (use `-` for stdin)
- `--scope <value>` — OAuth scope (required with `OAUTH`)
- `--api-version <value>` — API version override
- `--json` — JSON output (ALWAYS use this)

**Response Structure:**

`create` returns BOTH the discovered `assets` and the newly created `server`
object (`result` keys: `assets`, `server`). Each asset item has exactly these
keys: `active`, `availableAsAgentAction`, `description`, `id`, `kind`, `label`,
`name`, `status`. On creation the assets are discovered but not yet registered,
so each asset's `id` is `null` and its `status` is `NOT_REGISTERED` (activate
them with `agent mcp asset replace`). The server's audit fields (`createdById`,
`createdDate`, `lastModifiedById`, `lastModifiedDate`) also come back `null` in
the immediate create response.

```json
{
  "status": 0,
  "result": {
    "assets": [
      {
        "active": false,
        "availableAsAgentAction": false,
        "description": "Gets all tickets for driver...",
        "id": null,
        "kind": "MCP_TOOL",
        "label": "getTickets",
        "name": "McpTool__getTickets",
        "status": "NOT_REGISTERED"
      }
    ],
    "server": {
      "authorization": {
        "authType": "NO_AUTH",
        "identityProvider": null,
        "scope": null
      },
      "createdById": null,
      "createdDate": null,
      "description": "temp server for output reconciliation",
      "id": "0LeSB000000Jp5F",
      "label": "Recon Test",
      "lastModifiedById": null,
      "lastModifiedDate": null,
      "name": "reconTestServer",
      "serverUrl": "https://mcp.example.com/mcp",
      "status": "ACTIVE",
      "type": "EXTERNAL"
    }
  },
  "warnings": ["This command is currently in developer preview..."]
}
```

To extract the server ID after create, read `result.server.id` (NOT `result.id`).

**Error Response:**

Errors are emitted with a non-zero `status`/`exitCode` (e.g. `4`) and include
`name`, `message`, `context`, `stack`, `cause`, `code`, and `commandName` fields:

```json
{
  "name": "GetMcpServerFailed",
  "message": "Failed to get MCP server: MCP server not found",
  "exitCode": 4,
  "context": "ApiCatalogMcpServerGet",
  "code": "GetMcpServerFailed",
  "status": 4,
  "commandName": "ApiCatalogMcpServerGet",
  "warnings": ["This command is currently in developer preview..."]
}
```

### sf agent mcp list

**Purpose:** List all registered MCP servers

**Required Parameters:**

- `-o, --target-org <value>` — Target org

**Optional Parameters:**

- `--label <value>` — Filter by label
- `--type <EXTERNAL>` — Filter by type
- `--status <ACTIVE|DISCONNECTED>` — Filter by status
- `--json` — JSON output

**Response Structure:**

The server array is nested under `result.mcpServers` (NOT directly under
`result`). Each server carries a nested `authorization` object and bare
`createdById`/`lastModifiedById` string IDs.

```json
{
  "status": 0,
  "result": {
    "mcpServers": [
      {
        "authorization": {
          "authType": "NO_AUTH",
          "identityProvider": null,
          "scope": null
        },
        "createdById": "005SB00000iwVrhYAE",
        "createdDate": "2026-07-22T21:07:55Z",
        "description": null,
        "id": "0LeSB000000JoFd",
        "label": "ticketsMCP",
        "lastModifiedById": "005SB00000iwVrhYAE",
        "lastModifiedDate": "2026-07-22T21:09:22Z",
        "name": "ticketsMCP",
        "serverUrl": "https://mcp.example.com/tickets/mcp",
        "status": "ACTIVE",
        "type": "EXTERNAL"
      }
    ]
  },
  "warnings": ["This command is currently in developer preview..."]
}
```

### sf agent mcp get

**Purpose:** Get details on a specific MCP server

**Required Parameters:**

- `-i, --mcp-server-id <value>` — Server ID
- `-o, --target-org <value>` — Target org

**Optional Parameters:**

- `--json` — JSON output

**Response Structure:**

Auth details are nested under `authorization` (`authType`, `identityProvider`,
`scope`). For OAUTH servers `identityProvider` holds the token endpoint URL. There
is NO `clientId` field in the response, and audit info is exposed as bare
`createdById`/`lastModifiedById` string IDs (not `createdBy` objects with names).

```json
{
  "status": 0,
  "result": {
    "authorization": {
      "authType": "OAUTH",
      "identityProvider": "https://mcp.example.com/auth/token",
      "scope": "read"
    },
    "createdById": "005SB00000iwVrhYAE",
    "createdDate": "2026-07-15T23:38:04Z",
    "description": null,
    "id": "0LeSB000000Jk0j",
    "label": "TestHKWithAuth",
    "lastModifiedById": "005SB00000iwVrhYAE",
    "lastModifiedDate": "2026-07-15T23:40:43Z",
    "name": "TestHKWithAuth",
    "serverUrl": "https://mcp.example.com/test/mcp",
    "status": "ACTIVE",
    "type": "EXTERNAL"
  },
  "warnings": ["This command is currently in developer preview..."]
}
```

### sf agent mcp update

**Purpose:** Update an existing MCP server

**Required Parameters:**

- `-i, --mcp-server-id <value>` — Server ID
- `-o, --target-org <value>` — Target org
- At least one of `--label`, `--description`, `--server-url`, or `--auth-type`.
  Supplying none errors with `NoFields` (exit code 1): "No fields to update.
  Provide at least one of --label, --description, --server-url, or --auth-type."

**Optional Parameters:**

- `--label <value>` — New label
- `--description <value>` — New description
- `--server-url <value>` — New URL
- `--auth-type <OAUTH|NO_AUTH>` — New auth type
- `--identity-provider <value>` — OAuth IdP
- `--client-id <value>` — OAuth client ID
- `--client-secret <value>` — OAuth secret (use `-`)
- `--scope <value>` — OAuth scope
- `--json` — JSON output

**Response Structure:**

`update` returns the FULL server object (same shape as `get`), not a partial
subset.

**⚠️ Observed preview-stage bug — not all updatable fields persist:** In live
testing against the preview CLI (`sf` 2.144.6, plugin-agent), only
`--description` actually persisted. `--label` and `--server-url` updates
returned `status: 0` (apparent success) but the value was **silently ignored** —
a follow-up `get` showed the old value unchanged, and the `label` in the update
response echoed the server `name` rather than the requested label. Always verify
`update` results with a follow-up `get`, and do not rely on `--label` or
`--server-url` taking effect until this is fixed. (`--auth-type` was not
re-verified in this pass.)

```json
{
  "status": 0,
  "result": {
    "authorization": {
      "authType": "NO_AUTH",
      "identityProvider": null,
      "scope": null
    },
    "createdById": "005SB00000iwVrhYAE",
    "createdDate": "2026-07-23T21:16:03Z",
    "description": "updated desc",
    "id": "0LeSB000000Jp5F",
    "label": "reconTestServer",
    "lastModifiedById": "005SB00000iwVrhYAE",
    "lastModifiedDate": "2026-07-23T21:16:17Z",
    "name": "reconTestServer",
    "serverUrl": "https://mcp.example.com/tickets/mcp",
    "status": "ACTIVE",
    "type": "EXTERNAL"
  },
  "warnings": ["This command is currently in developer preview..."]
}
```

### sf agent mcp delete

**Purpose:** Delete an MCP server

**Required Parameters:**

- `-i, --mcp-server-id <value>` — Server ID
- `-o, --target-org <value>` — Target org

**Optional Parameters:**

- `--no-prompt` — Skip confirmation
- `--json` — JSON output

**Response Structure:**

Returns only `id` and `deleted` — there is NO `name` field.

```json
{
  "status": 0,
  "result": { "id": "0LeSB000000Jp5F", "deleted": true },
  "warnings": ["This command is currently in developer preview..."]
}
```

### sf agent mcp fetch

**Purpose:** Fetch live assets from an MCP server

**Required Parameters:**

- `-i, --mcp-server-id <value>` — Server ID
- `-o, --target-org <value>` — Target org

**Optional Parameters:**

- `--json` — JSON output

**Response Structure:**

Assets are returned directly under `result.assets` — there is NO `serverId` or
`serverName` field. Each asset carries `active`, `availableAsAgentAction`,
`description`, `id`, `kind`, `label`, `name`, and a `status` field
(`IN_SYNC` for registered assets, `NOT_REGISTERED` for freshly discovered ones).

Observed assets do NOT include `inputSchema`, `outputSchema`, or `annotations` —
those fields were not returned by the live server. Do not rely on them being
present. Descriptions may contain HTML entities (e.g. `&#39;` for `'`).

```json
{
  "status": 0,
  "result": {
    "assets": [
      {
        "active": true,
        "availableAsAgentAction": true,
        "description": "Gets all tickets for driver using their driver&#39;s license id...",
        "id": "1XOSB0000008riJ",
        "kind": "MCP_TOOL",
        "label": "getTickets",
        "name": "McpTool__getTickets",
        "status": "IN_SYNC"
      },
      {
        "active": true,
        "availableAsAgentAction": true,
        "description": "Evaluates whether a ticket should be waived based on a reason...",
        "id": "1XOSB0000008riI",
        "kind": "MCP_TOOL",
        "label": "disputeTicket",
        "name": "McpTool__disputeTicket",
        "status": "IN_SYNC"
      }
    ]
  },
  "warnings": ["This command is currently in developer preview..."]
}
```

### sf agent mcp asset list

**Purpose:** List the current asset allowlist for a server

**Required Parameters:**

- `-i, --mcp-server-id <value>` — Server ID
- `-o, --target-org <value>` — Target org

**Optional Parameters:**

- `--json` — JSON output

**Response Structure:**

Assets are returned directly under `result.assets` — there is NO `serverId`
field. Each asset has exactly these keys: `active`, `availableAsAgentAction`,
`description`, `id`, `kind`, `label`, `name`. Note: unlike `fetch`, `asset list`
does NOT include a `status` field on each asset.

**Important:** `asset list` reflects only _registered_ assets. Immediately after
`create`, before any `asset replace`, this returns an empty set
(`"assets": []`) even though the server advertises assets — because the assets
are discovered but not yet registered. Use `fetch` to see advertised (but
unregistered) assets, and `asset replace` to register/activate them.

```json
{
  "status": 0,
  "result": {
    "assets": [
      {
        "active": true,
        "availableAsAgentAction": true,
        "description": "Evaluates whether a ticket should be waived...",
        "id": "1XOSB0000008riI",
        "kind": "MCP_TOOL",
        "label": "disputeTicket",
        "name": "McpTool__disputeTicket"
      },
      {
        "active": true,
        "availableAsAgentAction": true,
        "description": "Gets all tickets for driver...",
        "id": "1XOSB0000008riJ",
        "kind": "MCP_TOOL",
        "label": "getTickets",
        "name": "McpTool__getTickets"
      }
    ]
  },
  "warnings": ["This command is currently in developer preview..."]
}
```

### sf agent mcp asset replace

**Purpose:** Replace the full asset allowlist for a server

**Required Parameters:**

- `-i, --mcp-server-id <value>` — Server ID
- `-o, --target-org <value>` — Target org
- Either `--assets <value>` OR `--assets-file <value>`

**Optional Parameters:**

- `--assets <value>` — JSON string or `-` for stdin. Mutually exclusive with
  `--assets-file` (supplying both errors with exit code 2).
- `--assets-file <value>` — Path to JSON file. Mutually exclusive with `--assets`.
  A missing file path errors with exit code 2 before any API call.
- `--json` — JSON output

**Asset Payload Format:**

Each asset item may include `id`, `name`, `label`, `description`, `active`, and
`kind` (per the command help). In practice `name` + `active` is sufficient to set
the allowlist; the other fields are optional. The payload accepts either an array
or an object with an `assets` key, supplied inline via `--assets`, from stdin via
`--assets -`, or from a file via `--assets-file`.

Array format:

```json
[
  { "name": "McpTool__add", "active": true },
  { "name": "McpTool__subtract", "active": false }
]
```

Object format:

```json
{
  "assets": [{ "name": "McpTool__add", "active": true }]
}
```

**Response Structure:**

Returns the full resulting asset set under `result.assets` (same shape as
`asset list`) — there is NO `serverId` or `assetsUpdated` field. Each asset in
the response is a full asset object (`active`, `availableAsAgentAction`,
`description`, `id`, `kind`, `label`, `name`), not just the `{name, active}` pairs
sent in the request payload.

**The response lists ALL of the server's assets, not only those in your payload.**
Any advertised asset omitted from the payload is returned with `active: false`
(this is the "full replacement" semantics — omission = deactivation). For example,
sending a payload with just `getTickets: true` against a 3-asset server returns
all three assets: `getTickets` active, and the two omitted ones as `active: false`.
After a replace, previously-unregistered assets now have real (non-null) `id`s.

```json
{
  "status": 0,
  "result": {
    "assets": [
      {
        "active": false,
        "availableAsAgentAction": false,
        "description": "Evaluates whether a ticket should be waived...",
        "id": "1XOSB0000008rok",
        "kind": "MCP_TOOL",
        "label": "disputeTicket",
        "name": "McpTool__disputeTicket"
      },
      {
        "active": true,
        "availableAsAgentAction": true,
        "description": "Gets all tickets for driver...",
        "id": "1XOSB0000008rol",
        "kind": "MCP_TOOL",
        "label": "getTickets",
        "name": "McpTool__getTickets"
      }
    ]
  },
  "warnings": ["This command is currently in developer preview..."]
}
```

## Concepts

### Asset Kinds

| Kind           | Description                | Use Case                                        |
| -------------- | -------------------------- | ----------------------------------------------- |
| `MCP_TOOL`     | Executable function/action | Agent can invoke tools to perform operations    |
| `MCP_PROMPT`   | Reusable prompt template   | Agent can use prompts for structured generation |
| `MCP_RESOURCE` | Data source or endpoint    | Agent can read resources for context            |

### Server Status

| Status         | Meaning                                 | Action                   |
| -------------- | --------------------------------------- | ------------------------ |
| `ACTIVE`       | Server is reachable and responding      | Normal operation         |
| `DISCONNECTED` | Server is unreachable or not responding | Check URL, auth, network |

### Asset Activation States

| State            | Meaning                                | Visibility              |
| ---------------- | -------------------------------------- | ----------------------- |
| `active: true`   | Asset is whitelisted and available     | Available to agents     |
| `active: false`  | Asset is fetched but not whitelisted   | Not available to agents |
| Not in allowlist | Asset exists on server but not tracked | Not available to agents |

The `availableAsAgentAction` boolean mirrors whether an active asset is exposed as
an agent action.

### Asset Sync Status (`fetch` only)

The `fetch` command returns a `status` field on each asset (the `asset list`
command does NOT):

| Status           | Meaning                                                                                                                                       |
| ---------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| `IN_SYNC`        | Asset is registered in the catalog and matches the live server                                                                                |
| `NOT_REGISTERED` | Asset was discovered on the server but is not yet registered (its `id` is `null`) — e.g. immediately after `create` before an `asset replace` |

### Authentication Types

**NO_AUTH** — No authentication required. The MCP server is publicly accessible or
uses a different auth mechanism (e.g., IP allowlisting, API gateway).

```bash
sf agent mcp create -n PublicServer --server-url https://public.mcp.example.com/mcp --auth-type NO_AUTH -o myOrg --json
```

**OAUTH** — OAuth 2.0 client credentials flow. Requires identity provider, client
ID, client secret, and scope.

```bash
echo "my-secret" | sf agent mcp create \
  -n SecureServer \
  --server-url https://secure.mcp.example.com/mcp \
  --auth-type OAUTH \
  --identity-provider MyIdentityProvider \
  --client-id abc123xyz \
  --client-secret - \
  --scope "read write execute" \
  -o myOrg \
  --json
```

OAuth parameters: `--identity-provider` (named credential or external IdP),
`--client-id`, `--client-secret` (use `-` for stdin), `--scope` (space-separated).

### Tool Metadata Fields

**Required:** `name` (e.g., `McpTool__add`), `kind`, `description`.

**Optional:** `inputSchema` (JSON Schema for inputs), `outputSchema` (JSON Schema
for outputs), `annotations` (custom metadata). Common annotations: `category`,
`rateLimit`, `cost`, `latency`, `destructive`, `requiresAuth`.

## Security Best Practices

### Client Secret Handling

- NEVER pass `--client-secret` directly on the command line (visible in shell
  history):
  ```bash
  # ❌ NEVER
  sf agent mcp create -n Server --server-url https://mcp.example.com --auth-type OAUTH --client-secret "my-secret" -o myOrg
  ```
- ALWAYS use stdin piping:
  ```bash
  # ✅ stdin
  echo "my-secret" | sf agent mcp create -n Server --server-url https://mcp.example.com --auth-type OAUTH --client-secret - -o myOrg --json
  # ✅ file piping
  cat /secure/location/secret.txt | sf agent mcp create -n Server --server-url https://mcp.example.com --auth-type OAUTH --client-secret - -o myOrg --json
  ```

### Credential Storage

- Warn users that credentials are stored in the Salesforce org.
- Recommend org-specific service accounts, not personal credentials.

### Server URL Validation

- Verify HTTPS for production servers.
- Warn if using HTTP for non-local development.

### Tool Review Checklist

Before activating a tool, review:

1. **Destructive operations** — Does it delete, update, or modify data? Execute
   code/commands? Have file system access?
2. **Data exposure** — Does it access sensitive data (PII, credentials)? Query
   databases directly? Have broad read permissions?
3. **Rate limits** — Are there rate limit annotations? Could it cause DoS if
   overused? Cost implications?
4. **Authentication** — Does it require additional auth? Impersonate users? Have
   elevated privileges?
5. **Scope** — Is the tool's purpose clear? Narrowly scoped or overly broad? Does
   it align with agent use cases?

### Recommended Warnings

**Production org deployment:**

```text
⚠️  WARNING: You are deploying to a PRODUCTION org.
    This will activate MCP tools in a live environment.
    Ensure all tools have been reviewed and tested.

    Continue? (yes/no)
```

**Destructive tool activation:**

```text
⚠️  CAUTION: This tool has destructive capabilities.
    Tool: McpTool__deleteRecord
    Description: Delete records from the database
    Annotations: {"destructive": true, "scope": "all_records"}

    Are you sure you want to activate this tool? (yes/no)
```

**Broad permissions:**

```text
⚠️  NOTICE: This tool has broad data access.
    Tool: McpResource__customerData
    Description: Access to all customer records

    Consider limiting scope or using field-level security.
    Activate anyway? (yes/no)
```

## Error Handling

| Error                     | Likely message                                                      | Resolution                                                 |
| ------------------------- | ------------------------------------------------------------------- | ---------------------------------------------------------- |
| No target org set         | `No default org found`                                              | Ask user to run `sf config set target-org <alias>`         |
| Server not found          | `MCP server not found`                                              | Verify server ID with `sf agent mcp list`                  |
| Connection refused        | `Failed to connect to <url>: Connection refused`                    | Verify URL, network connectivity, ensure server is running |
| Invalid OAuth credentials | `OAuth authentication failed: Invalid client credentials`           | Verify client ID, secret, identity provider, scope         |
| Duplicate name            | `Failed to create MCP server: API Catalog External service registration with name: <name> already exists. Use a new name or edit the existing one` (name `CreateMcpServerFailed`, exit code 4) | Use a unique name or update the existing server            |
| Unparseable asset JSON    | `The assets input does not contain valid JSON.` (name `InvalidJson`, exit code 1) | Fix the JSON syntax of the `--assets`/stdin payload |
| Wrong asset JSON shape    | `The assets input must be a JSON array of asset items or an object with an "assets" array.` (name `InvalidShape`, exit code 1) | Use an array of asset items or `{ "assets": [...] }` |
| Asset not found           | `Failed to replace MCP server assets: API Catalog DataSource MCP DataSource Asset <name> not found on server <id>` (name `ReplaceMcpServerAssetsFailed`, exit code 4) | Fetch fresh assets with `sf agent mcp fetch`               |
| Server disconnected       | `Cannot update assets: Server is DISCONNECTED`                      | Check server status, verify URL and auth                   |
| Deactivating an exposed Agent Action | `Failed to replace MCP server assets: Cannot deactivate asset(s) [<name>]: each is currently exposed as an Agent Action and must remain active for the lifetime of the server. Delete the Agent Action first, or delete the server with DELETE /mcp-servers/{id}.` (name `ReplaceMcpServerAssetsFailed`, exit code 4) | Delete the Agent Action referencing the tool first, or delete the server |

### Edge Cases

**Empty asset list** (`"assets": []`) — The server exposes nothing, is newly
registered and not yet indexed, or fetch errored. Offer to check server status,
retry fetch, or update server config.

**All tools declined/skipped** — No assets will be activated. Offer to review the
tools again, fetch fresh assets, or cancel and keep current state.

**Partial OAuth configuration** — If some but not all OAuth params are provided,
list the required set (`--identity-provider`, `--client-id`, `--client-secret`,
`--scope`) and which are missing.

**Server ID ambiguity** — If the user refers to a server by name, resolve to an ID
via `sf agent mcp list`. If multiple names match, present the matches and ask which
ID to use.

## Windows Compatibility

- **Python command:** Use `python` instead of `python3`.
- **Stdin piping (PowerShell):** `"secret" | sf agent mcp create ... --client-secret -`

**PowerShell — pass assets inline or via stdin:**

```powershell
$assets = @{
  assets = @(
    @{ name = "McpTool__add"; active = $true },
    @{ name = "McpTool__subtract"; active = $false }
  )
} | ConvertTo-Json -Depth 10 -Compress

$assets | sf agent mcp asset replace -i 0XSxx0000000001 --assets - -o myOrg --json
```

**cmd — create server (no auth):**

```cmd
sf agent mcp create ^
  -n MyServer ^
  --server-url https://mcp.example.com/mcp ^
  -o myOrg ^
  --json
```

For OAuth with a client secret, use PowerShell or Git Bash for stdin piping.

## Complete Workflow Example

### Scenario: Register and whitelist a weather MCP server

```bash
# 1. Verify target org
sf config get target-org --json

# 2. Create MCP server (no auth)
sf agent mcp create \
  -n WeatherServer \
  --server-url https://weather.mcp.example.com/mcp \
  --label "Weather MCP Server" \
  --description "Provides current weather and forecasts" \
  -o myOrg \
  --json
# Extract server ID from response: 0XSxx0000000123

# 3. Fetch available tools
sf agent mcp fetch -i 0XSxx0000000123 -o myOrg --json

# 4. Review each tool interactively (handled by Claude — see Workflow 4)
#    Tool getCurrentWeather → yes, Tool getForecast → yes

# 5. Build allowlist and replace it (pipe payload via stdin — no temp file)
echo '{
  "assets": [
    {"name": "McpTool__getCurrentWeather", "active": true},
    {"name": "McpTool__getForecast", "active": true}
  ]
}' | sf agent mcp asset replace -i 0XSxx0000000123 --assets - -o myOrg --json

# 6. Verify activation
sf agent mcp asset list -i 0XSxx0000000123 -o myOrg --json
```

### Scenario: Register an OAuth-authenticated server

```bash
# Store client secret securely, then pipe via stdin
echo "my-oauth-secret" | sf agent mcp create \
  -n OAuthServer \
  --server-url https://secure.mcp.example.com/mcp \
  --auth-type OAUTH \
  --identity-provider MyIdentityProvider \
  --client-id abc123xyz \
  --client-secret - \
  --scope "read write execute" \
  -o myOrg \
  --json
```

## Quick Reference

| Command                      | Purpose                                   |
| ---------------------------- | ----------------------------------------- |
| `sf agent mcp create`        | Register a new MCP server                 |
| `sf agent mcp list`          | List all registered servers               |
| `sf agent mcp get`           | Get details on a specific server          |
| `sf agent mcp update`        | Update server configuration               |
| `sf agent mcp delete`        | Remove server registration                |
| `sf agent mcp fetch`         | Fetch live assets from server             |
| `sf agent mcp asset list`    | List current asset allowlist              |
| `sf agent mcp asset replace` | Update asset allowlist (full replacement) |

## Troubleshooting

**Server shows DISCONNECTED status**

1. Check server URL is accessible: `curl -v <server-url>`
2. Verify authentication credentials (if OAuth)
3. Check server logs for connection errors
4. Try updating the server URL: `sf agent mcp update -i <id> --server-url <new-url>`

**Tools not appearing after whitelisting**

1. Verify asset activation: `sf agent mcp asset list -i <id>`
2. Check tools are marked `active: true`
3. Fetch fresh assets: `sf agent mcp fetch -i <id>`
4. Verify server is ACTIVE: `sf agent mcp get -i <id>`

**"Command not found: agent mcp"**

- The `sf agent mcp` plugin may not be installed
- Check SF CLI version: `sf version`; update with `sf update`
- Verify plugin availability: `sf plugins`
