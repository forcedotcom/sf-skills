---
name: platform-models-api-configure
description: "Configure (or troubleshoot) an AI coding agent or CLI to route through the Salesforce Models API using a signed OrgJWT. Use this skill when pointing an agent at the Salesforce model endpoint (api.salesforce.com/ai/gpt/v1), setting up OrgJWT / Bedrock-mode auth, wiring the agent's settings, API-key helper, and credentials file for the Salesforce endpoint, or fixing Models API 401 / 404 / \"model not available\" errors. DO NOT TRIGGER when the user needs to create or configure the Salesforce Connected App itself (use integration-connectivity-connected-app-configure) or set up Named Credentials / callout auth (use integration-connectivity-generate)."
metadata:
  cliTools:
    - tool: ["curl"]
      semver: ">=7.29.0"
    - tool: ["jq"]
      semver: ">=1.6.0"
    - tool: ["sf"]
      semver: ">=2.0.0"
  relatedSkills:
    - "integration-connectivity-connected-app-configure"
    - "integration-connectivity-generate"
  version: "1.0"
  domains: ["Platform", "Agentforce"]
---

# Salesforce Models API setup for an AI coding agent

The Salesforce Models API (`https://api.salesforce.com/ai/gpt/v1`) is
authenticated with a signed **OrgJWT** (obtained via `client_credentials` with
the `sfap_api` scope — see `scripts/get-orgjwt.sh`; no proxy). That auth and the
base URL are the same for **any** agent. How each agent then talks to the
endpoint is agent-specific: Anthropic clients (**Claude Code** and the **Claude
Agent SDK**) route through **Bedrock mode** (the env vars in Step 3), whereas
other agents (e.g. Codex) use their own client config against the same endpoint
and token — Bedrock mode does **not** apply to them.

The steps below are the **Claude Code / Claude Agent SDK reference
implementation** (Bedrock mode + a JSON settings file + an API-key helper). For
a non-Bedrock agent, reuse the OrgJWT auth (Step 1) and the base URL, and apply
the equivalent client settings in that agent's own config location instead of
the Bedrock env vars.

Bundled scripts are in `scripts/`. Path placeholders below: `<SKILL>` = the
absolute path to **this skill's own directory** (the folder containing this
`SKILL.md`; resolve it from the skill path in context). `<ABS>` = the absolute
path to the user's project root. Always emit fully resolved absolute paths —
the API-key helper runs from an undefined working directory, so relative paths
break it.

## Prerequisite

A connected app in the org with the **`sfap_api`** OAuth scope and the
**client_credentials** flow enabled (consumer key/secret + a run-as user).
Setup steps: https://developer.salesforce.com/docs/ai/agentforce/guide/access-models-api-with-rest.html
`curl` + `jq` installed.

## Inputs to collect

- `SF_INSTANCE_URL` — org My Domain, e.g. `https://acme.my.salesforce.com`
- `SF_CLIENT_ID`, `SF_CLIENT_SECRET` — connected-app consumer key/secret
- Models API base URL: `https://api.salesforce.com/ai/gpt/v1`
- Model: a fully qualified `sfdc_ai__…` name, e.g.
  `sfdc_ai__DefaultBedrockAnthropicClaude46Sonnet`
  (full list: https://developer.salesforce.com/docs/ai/agentforce/guide/supported-models.html)
- Scope: project (`<cwd>/.claude/settings.json`, default) or user (`~/.claude/settings.json`) — reference-agent settings paths
- Headers — `<FEAT>` = `x-client-feature-id` (default `ai-platform-models-connected-app`),
  `<APP>` = `x-sfdc-app-context` (default `EinsteinGPT`). Used in the Step 2 verify curl
  and in `ANTHROPIC_CUSTOM_HEADERS`.

## Steps (reference implementation)

Concrete values for a JSON-settings + API-key-helper agent. Reuse the OrgJWT
auth, verify curl, and base URL verbatim for any agent; adapt the settings-file
location and env-var wiring to the target agent.

1. Write `<project>/.claude/.orgjwt.env` (chmod 600), gitignore it:
   ```ini
   SF_INSTANCE_URL="..."
   SF_CLIENT_ID="..."
   SF_CLIENT_SECRET="..."
   ```
2. Verify — must return `200` before writing settings:
   ```bash
   TOKEN=$(bash <SKILL>/scripts/get-orgjwt.sh <ABS>/.claude/.orgjwt.env)
   curl -s -o /dev/null -w '%{http_code}\n' \
     <MODELS_API_URL>/model/<MODEL>/invoke-with-response-stream \
     -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
     -H 'x-client-feature-id: <FEAT>' -H 'x-sfdc-app-context: <APP>' \
     --data '{"anthropic_version":"bedrock-2023-05-31","max_tokens":16,"messages":[{"role":"user","content":"hi"}]}'
   ```
3. Write `.claude/settings.json` (merge into existing; keep other keys):
   ```json
   {
     "apiKeyHelper": "bash <SKILL>/scripts/get-orgjwt.sh <ABS>/.claude/.orgjwt.env",
     "model": "<MODEL>",
     "env": {
       "ANTHROPIC_AUTH_TOKEN": "",
       "CLAUDE_CODE_USE_BEDROCK": "1",
       "CLAUDE_CODE_SKIP_BEDROCK_AUTH": "1",
       "ANTHROPIC_BEDROCK_BASE_URL": "<MODELS_API_URL>",
       "ANTHROPIC_SMALL_FAST_MODEL": "<MODEL>",
       "ANTHROPIC_DEFAULT_MODEL": "<MODEL>",
       "ANTHROPIC_CUSTOM_HEADERS": "x-client-feature-id: <FEAT>\nx-sfdc-app-context: <APP>"
     }
   }
   ```
   Use absolute paths in `apiKeyHelper`. (`<FEAT>` / `<APP>` defaults are in
   "Inputs to collect" above.)
4. Tell the admin to fully restart the agent (`claude` for the reference agent) —
   settings and the API-key helper load at startup only.

### Capturing as a runbook (when asked to document, not apply)

If the user wants the setup written up for review instead of applied to their
machine (e.g. "save it as a Markdown runbook"), write **all** of the above into
the requested file (e.g. `models-api-setup-runbook.md`), in order and self-contained:
the exact `.orgjwt.env` contents, the `chmod 600` + gitignore note, the
verification curl (with the "must be `200` before writing settings" note), the
full `settings.json` block with every key from Step 3, and the final
"fully restart `claude`" step. Don't omit any of the nine `settings.json` keys.

## Verify before finishing

- [ ] `.claude/.orgjwt.env` created, `chmod 600`, and gitignored
- [ ] Verification curl returned HTTP `200` before `settings.json` was written
- [ ] `ANTHROPIC_AUTH_TOKEN` set to `""` in `settings.json`
- [ ] `CLAUDE_CODE_USE_BEDROCK` set to `"1"`
- [ ] `CLAUDE_CODE_SKIP_BEDROCK_AUTH` set to `"1"`
- [ ] `ANTHROPIC_BEDROCK_BASE_URL` is exactly `https://api.salesforce.com/ai/gpt/v1` (no trailing slash/path)
- [ ] `model`, `ANTHROPIC_DEFAULT_MODEL`, and `ANTHROPIC_SMALL_FAST_MODEL` all use the fully qualified `sfdc_ai__…` alias
- [ ] `ANTHROPIC_CUSTOM_HEADERS` contains `x-client-feature-id` and `x-sfdc-app-context`
- [ ] `apiKeyHelper` uses absolute paths (`bash <SKILL>/scripts/get-orgjwt.sh <ABS>/.claude/.orgjwt.env`)
- [ ] User told to fully restart `claude`

## Must be exact (each prevents a specific failure)

- `"ANTHROPIC_AUTH_TOKEN": ""` — clears any global token that would otherwise
  outrank `apiKeyHelper` (precedence: `ANTHROPIC_AUTH_TOKEN` > `ANTHROPIC_API_KEY`
  > `apiKeyHelper`). Without it → wrong/old bearer → 401/404.
- `CLAUDE_CODE_USE_BEDROCK=1` — activates the Bedrock API client; without it
  Claude Code uses the standard Anthropic API protocol and ignores
  `ANTHROPIC_BEDROCK_BASE_URL` entirely, so every call bypasses the Models API.
- `CLAUDE_CODE_SKIP_BEDROCK_AUTH=1` — else Claude Code overwrites `Authorization`
  with AWS SigV4 and the OrgJWT never lands.
- `apiKeyHelper` must be invoked as `bash <path> <credsfile>` (avoids exit-126).
- Model must be a fully qualified `sfdc_ai__…` name (see supported models).
- Auth is the OrgJWT from `client_credentials` (a signed JWT, 2 dots, scope
  `sfap_api`) — NOT `sf org display` (unsigned session token → 404). `sf` CLI
  has no client_credentials command; the helper calls `/services/oauth2/token`.
- Only `ANTHROPIC_BEDROCK_BASE_URL` routes; no tenant-id header needed.

## Diagnose

| Error | Meaning | Check first |
|-------|---------|-------------|
| `401` | Token is not a valid OrgJWT | Connected App `sfap_api` scope, `client_credentials` flow enabled, consumer key/secret in `.orgjwt.env`; `ANTHROPIC_AUTH_TOKEN` not cleared to `""` |
| `404` | Token valid but model/env/org not routable | Fully qualified `sfdc_ai__…` model alias, `ANTHROPIC_BEDROCK_BASE_URL` exactly `https://api.salesforce.com/ai/gpt/v1`, org entitled for the Models API, `ANTHROPIC_AUTH_TOKEN` cleared |
| `model not available` | Non-alias model id | Replace with a fully qualified `sfdc_ai__…` alias (see supported models) |
