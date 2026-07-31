# service-helpagent-coordinate

A Claude Code skill that stands up a **Service Cloud Help Agent** (Agentforce ASA)
end-to-end on a Salesforce org, following the guided four-checkpoint flow of the
Help Agent Quick Setup wizard.

This is a **`-coordinate`** skill (per sf-skills taxonomy): it orchestrates existing
skills against a canonical spec — it does **not** author a new agent primitive.

## What's here

| Path | Contents |
|---|---|
| `SKILL.md` | The skill: scope, coordinated skills, and the four-checkpoint workflow |
| `assets/help-agent-spec.md` | The canonical Help Agent spec — the guided flow (source of truth), kept small |
| `references/agent-script.md` | The canonical agent script + placeholders; loaded only at agent-creation time |
| `references/channel-web-chat.md` | Web Chat channel provisioning detail; loaded only when Web Chat is chosen |
| `references/channel-help-portal.md` | Help Portal channel (coming soon) — hard-stop guidance |
| `references/channel-voice.md` | Voice channel (coming soon) — hard-stop guidance |

The spec is split for **progressive disclosure**: the large agent script and the per-channel
branches live in `references/` and are read only when the flow reaches them, keeping the
always-loaded footprint small.

## Environment setup

Run these once per org before invoking the skill.

### Install and verify the tooling

```bash
claude --version
sf --version
```

Claude Code and the Salesforce CLI must both be installed.

### Activate MCP servers

Setup → Quick Find → **MCP Servers** (Integrations → API Catalog) → **Salesforce Servers** tab.
Activate all three: `metadata-experts`, `salesforce-api-context`, `sobject-reads`.

### Create an External Client App

Setup → **External Client App Manager** → **New External Client App**.

- **API (Enable OAuth Settings)** → Enable OAuth
  - Callback URL: `http://localhost:8080/callback`
  - Scopes: `Access Salesforce hosted MCP servers (mcp_api)` and `Perform requests at any time (refresh_token, offline_access)`
- **Security Settings**: uncheck *Require Secret for Web Server Flow* and *Require Secret for
  Refresh Token Flow*; check *Issue JWT-based access tokens for named users* and *Enable PKCE
  Extension for Authorization Code Flow*.
- Save → Settings → OAuth Settings → **Consumer Key and Secret** → copy the **Consumer Key**.

Claude Code is a public OAuth client — PKCE replaces the client secret. For the automated,
source-controlled ECA path (scopes + certificate/JWT), use the
`integration-connectivity-connected-app-configure` skill.

### Connect the CLI and register the MCP servers

```bash
sf org login web --alias <your-org-alias> --set-default
sf project generate --name help-agent --template standard
cd help-agent
```

Confirm the URL format on the `salesforce-api-context` server detail page — if it contains
`/sandbox/platform/`, substitute that for `/platform/` below. Replace `<CONSUMER_KEY>` with the
key from the ECA:

```bash
claude mcp add salesforce-api-context --transport http "https://api.salesforce.com/platform/mcp/v1/platform/salesforce-api-context" --callback-port 8080 --client-id <CONSUMER_KEY>
claude mcp add salesforce-metadata-experts --transport http "https://api.salesforce.com/platform/mcp/v1/platform/metadata-experts" --callback-port 8080 --client-id <CONSUMER_KEY>
claude mcp add sobject-reads --transport http "https://api.salesforce.com/platform/mcp/v1/platform/sobject-reads" --callback-port 8080 --client-id <CONSUMER_KEY>
claude mcp list
```

### Install Salesforce Skills

```bash
! npx skills add forcedotcom/sf-skills
```

Verify: `! ls .agents/skills/` and `! cat skills-lock.json`.

## Quick start

1. Complete **Environment setup** above.
2. Install this skill into your SFDX project:
   ```bash
   ! cp -R /path/to/service-helpagent-coordinate .agents/skills/service-helpagent-coordinate
   ```
3. In Claude Code:
   ```text
   I want to add a help agent to my Salesforce org so customers can get answers to
   common questions, manage their support cases, and reach a human agent when needed.
   I want it accessible as a chat widget on our customer website.
   ```
   The skill walks four checkpoints — identity → grounding → channel → go-live — waiting
   for your input at each. Nothing is built without confirmation.

## Status

- Tested on orgs with Data Cloud not yet provisioned — the readiness check enables Data
  Cloud (or hands off to the user to enable it) before proceeding. Any org shape that
  supports Agentforce + Data Cloud + Experience Cloud works.
- Creates an **Agentforce Service Agent** on the `QuickASA__QuickASA` template shape.
  This is the shape the eventual Help Agent Quick Start UI produces; treat it as the
  Help Agent lineage even though the official template-creation API is not yet shipped.

## Troubleshooting

- **MCP servers not connecting** — confirm the Consumer Key and the platform-vs-sandbox URL against the server detail page.
- **"No Einstein Agent User found"** — ask Claude Code to create one; it runs the CLI + permission-set steps.
- **Publish fails "Internal Error, try again later"** — `default_agent_user` in the `.agent` file doesn't match an active Einstein Agent User:
  ```bash
  sf data query --json -q "SELECT Username FROM User WHERE Profile.UserLicense.Name = 'Einstein Agent' AND IsActive = true"
  ```
- **OAuth doesn't redirect** — free port 8080 or pick another with `--callback-port` and update the ECA callback URL to match.

## Related

- ECA / OAuth setup skill: `integration-connectivity-connected-app-configure`
