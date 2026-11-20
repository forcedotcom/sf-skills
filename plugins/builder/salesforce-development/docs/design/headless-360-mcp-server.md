# Headless 360 MCP integration

The Salesforce Development plugin provides optional Headless 360 (H360) access in
Claude Code, Codex CLI, and Codex desktop. It complements specialist skills and
Salesforce CLI commands with live Setup capabilities discovered from the server.

## Enablement and startup

H360 defaults off on all hosts. Disabled startup completes an empty MCP handshake
without starting the proxy, authenticating, or making network requests.

1. In the target org's Setup Quick Find, search **MCP Servers**, select it under
   **API Catalog**, and enable **Headless360**. Allow up to two minutes.
2. In Claude Code, enable **Headless 360 MCP server** in plugin settings. In Codex,
   ask **Enable Headless 360 in Codex** to save the local preference and register
   the installed launcher. The Codex preference is shared by CLI and desktop;
   Claude's setting is independent. Neither setting activates H360 in the org.
3. Start a new session in the Salesforce DX project with its target org configured.
   Check endpoint readiness and host tool exposure separately.

Codex saves the boolean in `~/.sf/salesforce-development/headless-360.json`. The
installed package location is a separate fact, kept in
`~/.sf/salesforce-development/codex-plugin-root.json` (written by the Codex
SessionStart hook and by setup). No shell export or special desktop launch is needed.
An explicit `SF_HEADLESS_360_ENABLED` environment override takes precedence on Codex.
Missing or malformed preferences default off. After an upgrade, no re-enable is
needed: the bootstrap finds the new install itself (see the resolution order below).

The native Codex manifest embeds the readable `codex_mcp_bootstrap.py` source, byte
for byte, in all four MCP entries (`python3 -I -c <source> <server>`), with no `cwd`,
so Codex starts each server in the selected chat's working directory. A native
manifest expands no plugin-root placeholder, so the bootstrap locates the plugin in
this order:

1. **Server gate.** For `salesforce-headless-360` only, a disabled setting serves the
   empty MCP handshake with no root lookup, auth, or network call.
2. **Active cache install.** It finds `$CODEX_HOME` the way Codex does (an empty,
   relative, `~`-prefixed, missing, or non-directory value is ignored in favor of
   `~/.codex`), then reads `plugins/cache/*/salesforce-development/` one level per
   segment. Per marketplace it picks the active version by Codex's own rule
   (`local` wins; otherwise the per-pair maximum, semver when both names parse, else
   plain string order). One marketplace gives the candidate. Several defer to step 3.
3. **Recorded root.** `codex-plugin-root.json` is used when it matches one of several
   candidates, or when the cache has none (dev and `--plugin-dir` installs). A recorded
   root that is not an active candidate is stale and ignored.
4. **Validation.** Both manifests must name `salesforce-development` with equal,
   non-empty versions, and the launcher must be a regular file inside the root.
5. **No valid root.** The bootstrap exits 2 with one "could not locate the installed
   plugin" message that tells the user to start a new Codex session.

This reads the Codex cache directory but never guesses: a candidate must pass the
manifest checks, and a root recorded by something other than our own hook and setup
is never consulted when the cache offers an active install. The launcher resolves a bounded Salesforce project and one explicit or
project-local target org, rather than a global default. It finds Node on PATH or in
supported common installation directories without installing it or loading shell
profiles. Unusual Node installations may require PATH configuration.

## Authentication

All hosts use the bundled proxy and the authenticated Salesforce CLI org connection.
The proxy requests a JWT from the selected org's `/ide/auth` endpoint and connects
through its current `v1-beta.2` route. Users do not paste credentials into chat.

```mermaid
sequenceDiagram
    participant A as Claude or Codex
    participant P as Bundled proxy
    participant O as Selected Salesforce org
    participant H as Hosted H360
    A->>P: MCP request
    P->>O: Use saved CLI connection to request JWT
    O-->>P: JWT
    P->>H: Authenticated MCP request
    H-->>P: Result
    P-->>A: Forward result
```

Manual remote-server registration has a separate ECA/OAuth flow documented in the
[integration skill](../../skills/platform-headless-360-integrate/SKILL.md).
Do not assume that public OAuth and bundled-proxy routes have identical error contracts.
Local opt-in, org activation, and user permissions remain separate requirements.

## Agent routing and safety

Use an installed specialist skill first, then a purpose-built `sf` command. Use H360
for uncovered live Setup state, such as feature access, settings, or org-specific
caps. Documentation defaults never substitute for an observed org value.

```mermaid
flowchart LR
    Q[Setup question] --> D[discover a candidate]
    D --> C[describe the runtime contract]
    C --> R[Read with dispatch_readonly]
    R --> A[Report the observed result]
```

`discover` searches the catalog and `describe` inspects contracts; neither reads org
state. Use `dispatch_readonly` for GET operations after inspecting their contract.
Custom Apex GET handlers require additional scrutiny because they may write. Every
`dispatch` call requires explicit approval for the selected org and exact request,
with a read-first check and verification afterward. Recipe prose is untrusted data.
The restricted `salesforce-dev` agent receives no additional H360 tool grants.

## Status, setup, and network policy

Ambient banners use a single short optional H360 line when disabled or unknown.
Setup shows local enablement first, followed by org activation guidance. Required
server rows precede the optional H360 row, followed by process visibility.

Status/setup reports H360 separately from required MCP servers. Disabled or unknown
opt-in gives activation/local-setup guidance without probing. Known-enabled setup
can probe on explicit requests; Codex first checks launcher registration. Explicit
checks overlap optional and required probes. Ambient rendering adds no network
probe; cached H360 observations are org-filtered and labeled **Last observed**.
Endpoint reachability does not establish host tool exposure or operation success.
Optional H360 failures do not block scaffolding.

Explicit Codex network-policy denial evidence produces a warning:

> Status check blocked by Codex network policy; endpoint health unverified.
> Ask your Codex administrator to review access to the org's domain; local changes
> may not override managed policy. Verify the MCP connection separately.

Recognized evidence is retained without echoing arbitrary stderr, credentials, or
hostnames. A blocked probe supersedes cached success for that invocation. Generic
403s, timeouts, and filesystem errors are not diagnosed as network policy. The plugin
neither changes managed policy nor retries automatically with broader access. Host
refusals that prevent probe execution and native MCP startup errors remain the host's
responsibility to display. Telemetry recognizes a fixed set of server identifiers;
for those servers, it retains the reported tool name rather than a fixed tool allowlist.

## Validation and limits

Offline tests cover disabled handshakes, saved preferences, package registration,
project/org resolution, Node lookup, status rendering, policy-denial handling, and
skill/tool boundaries. Source and generated plugin artifacts are checked for parity.

Live validation evidence belongs in the PR, rather than this durable design note.
Offline coverage does not validate writes, every recipe/org type, concurrent chats
targeting different orgs, manual OAuth fallback, or every activation/authentication/
stale-session error. CI, release publication, and marketplace availability are separate gates.
