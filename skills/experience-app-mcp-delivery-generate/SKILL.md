---
name: experience-app-mcp-delivery-generate
description: "Package and deliver an existing Salesforce hosted MCP server/App MCP for an Experience Site as an MCP configuration file or a Claude plugin repository. Discover the serving URL and External Client Application client ID, generate client configuration, optionally bundle skills in a plugin, and provide local testing and private GitHub handoff instructions. Plugin packaging supports Claude only; reject requests for Codex, ChatGPT, or other plugin platforms. Use for connecting clients and packaging delivery, not for creating or activating the Salesforce MCP server."
metadata:
  version: "1.0"
  minApiVersion: "68.0"
  cliTools:
  - tool:
    - "git"
    semver: ">=2.0"
  - tool:
    - "node"
    semver: ">=18.0.0"
  - tool:
    - "sf"
    semver: ">=2.0.0"
---

# Deliver an Experience Site MCP Connection

Create a standalone MCP configuration file or a local Claude plugin for an existing hosted server. This skill owns client connection discovery and ECA client-ID retrieval. It reads Salesforce configuration and creates local files; publishing requires a separate user request.

`<skill-dir>` is the absolute directory containing this `SKILL.md`. Run discovery helpers from the selected SFDX project root and write delivery files to the user's chosen destination.

Reuse the org/site/server/ECA identities, exact site developer name, serving URL and validation results already established in the current context. Discover only missing, stale, conflicting or unverified facts. Ask only for choices that have not already been supplied.

## Supported plugin platform

Check the requested delivery format and plugin platform before preflight or connection discovery. This skill generates **Claude plugins only**. If the user requests a Codex, ChatGPT, or any other non-Claude plugin, explain that the requested plugin platform is unsupported and stop without running helpers or creating files. Do not substitute a Claude plugin, claim cross-platform compatibility, or use `authStyle: "requested"` to bypass this boundary. Changing the delivery format requires a new, explicit user choice.

If the user asks for a plugin without naming its platform, ask which platform they want and state that this skill supports Claude plugins only. Determine the platform from the requested artifact, not from the application running this skill; an explicit request for a Claude plugin remains supported when made in Codex or ChatGPT. Standalone MCP configuration requests continue through the configuration-only path.

## 0. Preflight

For supported delivery requests, reuse the target org alias or ask if missing. Run from the selected SFDX project root before every supported entry path, including repair and resume. Unsupported plugin requests stop at the platform check above without running preflight. Proceed only on `decision: continue`.

If the project root has no `sfdx-project.json`, create it before running any bundled script, with `packageDirectories` `[{"path": "force-app", "default": true}]` and `sourceApiVersion` `"68.0"`. Do not change an existing one.

IMPORTANT: Set `<skill-named>` to `true` only if the user's request explicitly names `experience-app-mcp-delivery-generate`; otherwise use `false`. Do not count the agent's own skill selection or messages.

```bash
node "<skill-dir>/scripts/preflight.mjs" <target-org-alias> --skill-named <skill-named>
```

Read the JSON `decision`:

- `continue`: proceed to step 1.
- `skip`: immediately exit this skill and pursue the original request another way. Say nothing about this skill, its check, or the result.
- `disabled`: say only the returned `userMessage`, without error details; exit this skill and pursue the original request another way.
- `needs_input` or `error`: show only `userMessage` and `nextAction`, obtain corrections and rerun preflight. Proceed only on `continue`; never infer entitlement from errors.

## 1. Choose the delivery format

Reuse known choices. Establish whether the user wants **MCP configuration only** or an explicitly selected **Claude plugin**, following the supported-platform check above. Configuration-only delivery requires no plugin name, author, version, icon or bundled skills. Ask for its target client, an absolute path to a new JSON file, and missing connection facts. Read [standalone configuration delivery](references/mcp-config-delivery.md).

For a Claude plugin, load [package format and publishing](references/plugin-format-and-publishing.md) and ask together for missing inputs:

- Target org alias, MCP server DeveloperName, and Experience Site, if not already known.
- Where to create the plugin's GitHub repository locally: an absolute path to a **new directory**. Never assume the Salesforce project or this skill's directory is the destination.
- Kebab-case plugin name, short purpose/description, author, and semantic version (suggest `1.0.0` for the first release). Ask for the intended private `github.com` repository owner/name and license if the user knows them; both can be skipped for local testing. Do not invent author details or choose a license for them.
- Ask: **“Do you want to bundle any skills in this plugin?”** If yes, ask whether the user wants to include one or more existing skills, create one or more new skills, or both. For each new skill, ask for its goal, intended users, and the MCP tasks it should help with. For each existing skill, ask for the absolute folder path containing `SKILL.md`.
- Establish the OAuth callback port choice for every plugin request. Reuse an explicitly selected port or an explicit decision to skip from this session; otherwise ask: **“Provide the callback port matching your ECA's registered callback URL, or choose to skip setting a fixed port.”** If provided, pass it as the numeric `mcp.callbackPort` (integer 1–65535); the Claude Code profile writes it as `oauth.callbackPort`. Omit the field from both the generation config and `.mcp.json` when the user skips it or cannot provide a port—do not add a default, `null`, empty string or guessed port. Note any unverified callback registration as pending; packaging does not modify the ECA.
- Ask: **“Would you like to add a plugin icon? Provide an image file path, or skip for now.”** Reuse an image only if the user selected it for this plugin; do not reuse a removed icon or substitute Anthropic branding. Supply `iconPath` according to the reference's input requirements. Omit it when the user skips and continue with local testing.

Do not repeatedly ask for permission to inspect configuration, read the selected skill, generate new local files in the chosen scope, or validate them. Resolve ambiguity and incompatible existing files before proceeding. Do not deploy or activate a server, change ECA settings or permissions, authenticate as another user, or create/push any GitHub repository as part of packaging alone.

## 2. Discover and confirm the connection

```bash
node "<skill-dir>/scripts/discover_mcp_context.mjs" <target-org-alias> [SERVER_DEV_NAME]
```

The helper prints only selected non-secret org fields, Tooling MCP server/access records, Network sites with their developer names, and ECA names/record IDs. Use the selected site's `DeveloperName` from this output. It captures `sf org display` internally; never print its full raw response because it contains an access token. A non-empty `errors` array or `incomplete` status indicates a failed or incomplete lookup, not absence. Report which lookup failed and resolve only the missing facts.

Select the exact deployed server and site from those results. Confirm the selected server's activation state; if it is inactive or activation lookup failed, report readiness as pending rather than activating it. An ECA need not share the server's name, and the server inventory does not prove an ECA association. Reuse a previously selected ECA or ask the user to choose its DeveloperName from the inventory.

Users do not need to know the full serving URL. Reuse an authoritative HTTPS URL from the existing server setup when available. Otherwise the generator builds the URL from route components; the path depends on the org environment:

| Environment | `https://api.salesforce.com/platform/mcp/v1/p/…` |
|---|---|
| `production` | `{my-domain}/{site-dev-name}/custom/{server-name}` |
| `developer` | `{my-domain}/develop/{site-dev-name}/custom/{server-name}` (token usually ends in `-dev-ed`) |
| `sandbox` | `{my-domain}--{sandbox-name}/sandbox/{site-dev-name}/custom/{server-name}` |
| `scratch` | `{my-domain}/scratch/{site-dev-name}/custom/{server-name}` |

- **Environment**: select `production`, `developer`, `sandbox`, or `scratch`. If the user explicitly requests one, use it. Otherwise use the discovery helper's `environment.value` (from the Organization record) and confirm it equals `domainCandidate.hostEnvironment` (from the instance hostname). If they differ or either is missing, report both pieces of evidence and ask; never guess.
- **My Domain token** is `domainCandidate.value`, **not** the full hostname, when its `hostEnvironment` matches the selected environment. When the user requests an environment other than the connected org's, or the host is unrecognized, ask only for that environment's token (for a sandbox, `{my-domain}--{sandbox-name}`) or resolve it through read-only org configuration.
- `site-dev-name` is the selected site's exact developer name, including case. Use its `DeveloperName` from the discovery output or current setup context. If it is missing, resolve the failed lookup and ask only for the missing authoritative value. Never substitute the display name, URL prefix, or a guessed bundle name.
- `server-name` is the exact deployed server DeveloperName, including case. Keep it separate from the plugin slug and MCP configuration key.

Pass `mcp.environment`, `mcp.domain`, `mcp.siteDeveloperName` and `mcp.mcpName` to the generator; never assemble the URL by hand or convert one environment's URL into another by editing path segments. Pass `mcp.url` instead only for an authoritative URL from existing setup. The legacy `mcp.sitePrefix` configuration is rejected. Show the environment, the resulting URL and their evidence in the delivery preview. Ask only about missing, ambiguous or conflicting components; do not require the user to research or assemble the URL.

Do not invoke business tools to determine a route. A correctly constructed URL does not prove the selected org has Experience Site MCP support enabled, its server is active, or OAuth and user access work. Record those connection checks as unverified until checked in the intended client.

## 3. Retrieve the ECA client ID

Read [ECA lookup and recovery](references/eca-consumer-key.md).

If the caller already supplied a consumer key from a successful lookup in this session for the same selected org and ECA, reuse it. Otherwise run:

```bash
node "<skill-dir>/scripts/retrieve_eca_consumer_key.mjs" <target-org-alias> <ECA_DEV_NAME> --json
```

Use the returned **`clientId`** as the public OAuth client ID in the delivery output. Never fetch a consumer secret or copy an access/refresh token.

A non-zero exit means lookup/validation failed. Exit `0` with `status: not_found` proves no deployed ECA matched; `status: selection_required` lists consumer IDs/names and requires a selection. On `selection_required`, ask once which consumer to use, then rerun with its ID before `--json`. Do not guess a key or print candidate keys. Packaging does not change callback URLs, scopes, or permissions; note any needed readiness work in the generated README/handoff.

## 4. Deliver configuration or prepare plugin skills

For **MCP configuration only**, follow [standalone configuration delivery](references/mcp-config-delivery.md), validate the written JSON and report the destination, client profile and pending connection checks. Stop there; do not run plugin generation, plugin validation or publication steps below.

For a **Claude plugin**, continue below.

For **no skills**, use `skills: []` in the generation config and create an MCP-only plugin.

For **each new skill**, inspect the selected server's available tool definitions/descriptions through an authenticated, read-only client connection when available. Otherwise use existing server metadata and backing-action descriptions as evidence, and mark unverified runtime tool names instead of inventing them. Write each focused `SKILL.md` and any necessary companions in a temporary staging directory: kebab-case name, concise trigger description, the user's stated goal, guidance on using the actual MCP tools, and consent before actions that change business data. Do not invoke business actions while authoring the skills, embed org credentials, or promise tools that are not exposed. Match tool references to the client-visible names once the plugin is loaded. Keep each skill self-contained; only bundle resources that serve its goal.

For **each existing skill**, inspect the chosen `SKILL.md`, its references, scripts, assets and local dependencies. Review it for public sharing, required companions and third-party license notices. Pass its absolute directory path in the configuration's `skills` array; the generator handles resource copying and file permissions. Create a staged copy only when edits are needed, such as resolving missing dependencies or machine-specific absolute references; pass that staged directory instead and leave the original unchanged. Resolve reported symlinks or credential files in the staged copy before retrying.

## 5. Generate and validate

Create a temporary JSON configuration using the input contract in the reference. Omit `authStyle` or set it to `"claude-code"` for Claude Code. Select the custom `"requested"` OAuth profile only when the user explicitly requests it for the Claude plugin; leave runtime compatibility pending until validated. An OAuth profile changes connection settings, not the supported plugin platform. Supply the public client ID, never a secret.

Run the bundled generator to preview and write the package:

```bash
node "<skill-dir>/scripts/generate_plugin.mjs" /path/to/package-config.json
node "<skill-dir>/scripts/generate_plugin.mjs" /path/to/package-config.json --write
```

Show the preview: destination, manifest identity/version, MCP URL, public client ID source, auth profile, bundled skills and file inventory. Resolve uncertain routing/auth facts or naming changes in one question. Once the plan is within the user's selected scope, create the files with `--write`; do not ask a second time just to create them. Existing destinations block generation and are never overwritten.

On a blocked result or nonzero exit, report the generator's error, resolve the invalid inputs and rerun the preview; do not bypass the generator by constructing the output manually. Inspect the written files against the approved inputs: identity/version, server URL, public client ID, selected profile, icon and skill resources. Check that referenced resources resolve and that no credentials or private material entered the package.

Run `claude plugin validate <absolute-plugin-path>` after generation and after any correction; report its exit status and actual output, including warnings. If `claude` is not on PATH, look for an existing installation before declaring the CLI unavailable. Fix packaging errors within scope and rerun; unresolved errors mean the package is not validated. If the CLI is unavailable, report validation as pending rather than passed. Follow the reference for local `--plugin-dir` and `/mcp` OAuth/listing checks. Do not confuse file/schema validation with a verified connection or successful business action.

## 6. Handoff for publication

Read the generated `README.md` and present its local testing and publication instructions to the user. Preserve its separate command blocks, safe path quoting and stop-on-error guidance. Adapt the instructions when the user's actual repository, account, version or installed CLI requires it; follow the reference for those cases. Present the launch command for the user to run, without starting an interactive Claude session automatically.

Report the local folder, files, chosen site/server/ECA, final serving URL, selected authentication profile, actual validation results and unresolved routing/OAuth or licensing work. Creating a repository, uploading, tagging or submitting requires a separate user request; presenting the README's commands does not authorize executing them. Keep hosting private unless the user explicitly requests another visibility, and review directory eligibility separately. Report publication or approval only when actually completed. Make the final documentation link in the completion message [Submit your plugin](https://claude.com/docs/plugins/submit).
