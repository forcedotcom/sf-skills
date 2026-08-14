---
name: platform-lsp-integrate
description: "Reference for how to call the Salesforce LSP MCP tools and what to do when they are unavailable. Use when the user asks how to use the Salesforce LSP, which LSP/MCP tools exist, what apex.diagnostics / validate_soql / complete_soql do, why an LSP tool returned an error like lsp_disabled or no_apex_workspace or no_org_connected, how to debug the LSP host, or how to turn the LSP off. Also the contract other skills follow when they call an LSP tool: which tool to prefer, how to read its result, and the fallback when the LSP host is absent. DO NOT TRIGGER for generating or editing Apex/LWC/metadata (use platform-apex-generate), running deploys (use platform-metadata-deploy), or SOQL authoring (use platform-soql-query); this skill is a reference and contract document — use it only when the question is specifically about the LSP layer or its MCP tools."
allowed-tools: Bash Read mcp__plugin_salesforce-development_salesforce-lsp__lsp_health
metadata:
  mcpTools:
    # Native salesforce-lsp server tool ID (the bundled LSP host registers it
    # dotted as lsp.health). In allowed-tools it appears in Claude Code's
    # sanitized form: mcp__plugin_salesforce-development_salesforce-lsp__lsp_health.
    salesforce-lsp:
      tools: ["lsp.health"]
      semver: ">=0.1.0"
  cliTools:
    - tool: ["sf"]
      semver: ">=2.0.0"
  relatedSkills:
    - "platform-apex-generate"
    - "platform-metadata-deploy"
    - "platform-soql-query"
---

# Using the Salesforce LSP

The `salesforce-development` plugin hosts a local MCP server named
**`salesforce-lsp`** that lazily spawns Salesforce Language Server children and
exposes their semantic capabilities as MCP tools. This skill is the **contract**
other skills follow when they call those tools, and the answer to "how do I use
the Salesforce LSP?" — what each tool does, how to read its result, what every
error code means, and how to fall back when the host is absent.

This is a documentation/reference skill. It does not author or deploy code; it
tells you (and other skills) how to drive the LSP tools correctly.

> **This plugin build vendors Apex + SOQL only.** The `salesforce-lsp` host
> ships the Apex language server (`@salesforce/apex-ls`) and the SOQL language
> server. The **LWC** language server is intentionally **not** bundled in this
> plugin — the `lwc.*` tools are registered by the host but will always return
> an `unavailable`-class envelope here. Treat any `lwc.*` call as unavailable
> and use the fallback (read the component source / deploy-compile).

## When to Use This Skill

- A user asks how to use the Salesforce LSP, or which LSP/MCP tools are available.
- A user asks what a specific tool does (`apex.diagnostics`, `validate_soql`,
  `complete_soql`, etc.) or how to read its output.
- An LSP tool returned an error envelope (`lsp_disabled`, `spawn_timeout`,
  `circuit_open`, `no_apex_workspace`, `no_org_connected`) and you need to know
  what it means and how to recover.
- You're authoring or reviewing another skill that calls an LSP tool and need the
  canonical call/fallback pattern.
- The LSP seems broken and you need to debug it (`lsp.health`,
  `${CLAUDE_PLUGIN_ROOT}/bin/lsp-doctor`, the kill switch).

## The Tools

All tools are served by the MCP server **`salesforce-lsp`** (invoke names follow
the plugin-prefixed pattern:
`mcp__plugin_salesforce-development_salesforce-lsp__<tool_name>`, where dots in
tool names become underscores — e.g. `apex.diagnostics` becomes
`mcp__plugin_salesforce-development_salesforce-lsp__apex_diagnostics`). Spawning
is lazy: a tool that needs a language server brings the child up on first call (a
one-time cold start of a few seconds for Apex), then reuses it. The pure
static-analysis tools never spawn anything.

### Apex (spawns the Apex LSP)

| Tool | Purpose | Key input | Key output |
|---|---|---|---|
| `apex.diagnostics` | Compile-check a `.cls`/`.trigger`; surface errors/warnings | `{ filePath }` | `{ ok, diagnostics: [{ line, column, severity, message }] }` |
| `apex.hover` | Type/signature at a position | `{ filePath, line, character }` | hover markdown |
| `apex.documentSymbol` | Outline of a file's symbols | `{ filePath }` | symbol tree |
| `apex.completion` | Code-completion at a position | `{ filePath, line, character }` | completion items |

### SOQL

| Tool | Purpose | Spawns? | Key output |
|---|---|---|---|
| `validate_soql` | Parse a SOQL string for **syntax** errors | SOQL LSP | `{ ok, diagnostics: [{ line, column, severity, message }] }` |
| `complete_soql` | Schema-aware completion at a cursor (SObjects, fields, picklist values resolved against the org) | SOQL LSP | `{ ok, items, expanded, unresolved, hint? }` |
| `extract_soql_from_apex` | Statically pull every inline `[SELECT …]` out of Apex | **No** (pure static) | `{ ok, totalQueries, totalDynamic, files }` |
| `check_soql_selectivity` | Selectivity heuristics (optional org LIMIT-0 probe) | **No** by default | selectivity report |
| `refresh_org_schema` | Invalidate the cached org describe so completion re-fetches | **No** | `{ ok, removed }` |

> **Just deployed a field/object and it won't resolve?** When a SOQL or Apex
> reference to a *freshly-deployed* field fails (e.g. `No such column 'Foo__c'`,
> or `complete_soql` doesn't offer it) right after a deploy, the cached org
> describe is stale — call **`refresh_org_schema`** to invalidate it, then re-run
> the check before assuming a code error or renaming anything. This is the lever
> for post-deploy schema lag; reach for it *before* treating the failure as a bug
> in your query/class. (It only clears the local cache; it can't speed up
> server-side propagation, so if the org itself hasn't finished publishing the
> field, re-running after a moment is the fallback.)

### LWC — not available in this build

The `lwc.*` tools (`lwc.diagnostics`, `lwc.hover`, `lwc.definition`,
`lwc.completion`, `lwc.workspace_symbols`) are registered by the host but the LWC
language server is **not vendored** in this plugin. Every `lwc.*` call returns an
unavailable envelope. For LWC work, fall back to reading the component
source/templates directly or deploy-compiling and reading the CLI errors.

### Diagnostics / health

| Tool | Purpose | Spawns? |
|---|---|---|
| `lsp.health` | Read-only view of kill-switch mode, workspace, per-server state, circuit-breaker state, cold-spawn timing, apex-ls version | **No** — never spawns |

Coordinates everywhere are **one-based** (`line`/`column`). `validate_soql`
diagnostic coordinates are relative to the **query string**, not a file — when a
query came from `extract_soql_from_apex`, translate back using that query's range.

## The Call / Fallback Contract

Every skill that calls an LSP tool follows the same three rules:

1. **Prefer the LSP tool over guessing.** If a tool exists for the step (validate
   a query, compile-check a class, complete against the org schema), call it
   before falling back to hand-analysis.
2. **Treat an error envelope as "unavailable," never as "passed."** A tool may
   return `{ error: <code> }` instead of a result (see Error Codes). On any such
   code, record `<tool>=unavailable: <code>` in your report and continue down the
   fallback path — **never** report the input as valid/clean just because the
   check didn't run.
3. **Degrade, don't fail.** The LSP is an accelerator, not a hard dependency. If
   the host isn't available at all, the `salesforce-lsp` tools simply won't
   exist — fall back to the CLI/manual path for that step and say so.

### When the LSP host is absent

If the plugin/host isn't available, the MCP tools above are not registered, so a
call to (e.g.) `validate_soql` will not resolve. Detect this the same way you
detect an error envelope — the tool is unavailable — and use the documented
fallback:

| LSP tool unavailable | Fallback |
|---|---|
| `apex.diagnostics` | Deploy/compile via `sf project deploy` and read CLI errors |
| `validate_soql` | Smoke-check by running the query read-only via `sf data query --json` (a parse error surfaces in the CLI error) |
| `complete_soql` | `sf sobject describe --sobject <O> --json` for fields; author from the user's stated names |
| `extract_soql_from_apex` | Read the file(s) and locate `[SELECT … ]` by hand |
| `apex.completion` / `apex.hover` | Read the source directly |
| `lwc.*` (always unavailable here) | Read the component source/templates directly, or deploy-compile and read CLI errors |

## Error Codes

A tool returns `{ error: <code> }` (or, for `complete_soql`, a `hint`) instead of
a result. Each maps to a recovery:

| Code | Meaning | What to do |
|---|---|---|
| `lsp_disabled` | The kill switch (`SFDX_LSP`) forbids this language | Use the non-LSP fallback; or re-enable the LSP (see Debugging) |
| `spawn_timeout` | The language server didn't come up in time | Retry once; if it persists, fall back and run `${CLAUDE_PLUGIN_ROOT}/bin/lsp-doctor` |
| `circuit_open` | Repeated spawn failures tripped the breaker; calls are short-circuited | Fall back now; investigate with `lsp.health` / `${CLAUDE_PLUGIN_ROOT}/bin/lsp-doctor` |
| `no_apex_workspace` | No `classes/*.cls` under any package dir — Apex tools won't spawn | Expected in a non-Apex project; nothing to check |
| `no_org_connected` | (`complete_soql` hint) org schema couldn't be resolved | Keyword completion still works; ask for exact field/object names or connect an org. **Do not** surface `__…_PLACEHOLDER` labels as real fields |

The first three are transient/config states shared by every spawning tool; the
rest are expected, healthy states for a particular workspace/org/file context —
not signs of a broken install. (`no_lwc_bundles` / `unsupported_lwc_file` are
LWC-only codes; in this build the LWC server is not vendored, so `lwc.*` returns
unavailable regardless.)

## Debugging the LSP

Three layers, cheapest first:

1. **`lsp.health` (MCP tool).** The fastest check — never spawns a child. Reports
   the kill-switch mode, resolved workspace, per-server status, circuit-breaker
   state, last cold-spawn timing, and the vendored apex-ls version. Ask Claude to
   "run lsp.health," or call the `lsp.health` tool directly.

2. **`bin/lsp-doctor` (CLI).** A deeper, install-level diagnostic for support and
   onboarding. Verifies the committed bundles exist, the vendored apex-ls
   artifacts resolve, the org-schema cache is parseable, and each LSP child can
   actually spawn. Exits `0` when healthy, `1` with structured per-check output
   when something is wrong.

   ```bash
   "${CLAUDE_PLUGIN_ROOT}"/bin/lsp-doctor            # human-readable report
   "${CLAUDE_PLUGIN_ROOT}"/bin/lsp-doctor --json     # machine-readable
   "${CLAUDE_PLUGIN_ROOT}"/bin/lsp-doctor --no-spawn # skip child-spawn probes (CI/restricted)
   ```

   (In this build `lsp-doctor` will report the LWC server as missing — that is
   expected; only Apex + SOQL are vendored here.)

3. **`SFDX_LSP_DEBUG=1`.** Emits single-line JSON telemetry (spawn timing, cache
   hits, circuit events, per-tool latency) to stderr. Off by default (zero
   overhead).

### The kill switch — `SFDX_LSP`

The fast way to control or disable the LSP. Set the environment variable:

| `SFDX_LSP` | Effect |
|---|---|
| unset / `all` | Every vendored LSP may spawn (default) |
| `apex-only` | Only the Apex LSP may spawn; SOQL tools return `lsp_disabled` |
| `disabled` | No LSP spawns; every LSP tool returns `lsp_disabled` |

To rule the LSP in or out of a problem, set `SFDX_LSP=disabled` and re-run: if the
issue persists it isn't the LSP, and skills will have fallen back to their non-LSP
paths automatically. An unknown value defaults to `all` (with a warning) so a typo
never silently disables the feature.

## Pre-deploy diagnostics gate

A `PreToolUse` hook (`bin/lsp-precheck`) runs Apex diagnostics on the
`.cls`/`.trigger` files a `sf project deploy start`/`validate` is about to push,
and emits a decision. It is **fail-open**: any error (including a missing/slow
LSP) allows the deploy. Mode is controlled by `SFDX_LSP_DEPLOY_GATE`
(`off` | `warn` | `block`, default `warn`) — `warn` surfaces diagnostics without
blocking; `block` denies a deploy that has Apex compile errors.

## Verification

- Asked "how do I use the Salesforce LSP tools?", this skill is the match and lists
  the tools, their inputs/outputs, and the fallback contract.
- Appears in the `/skills` listing as `platform-lsp-integrate`.
- Given an error code (e.g. `no_apex_workspace`), it explains the meaning and the
  correct recovery without treating the unrun check as a pass.

## Cross-Skill Integration

| Need | Delegate to |
|---|---|
| Compile-check + analyze Apex you just wrote | `platform-apex-generate` |
| Validate inline SOQL in `.cls`/`.trigger` | `validate_soql` (this skill); fallback: run read-only via `sf data query --json` |
| Author & run a SOQL query against the org | `complete_soql` + `sf data query` |
| Pre-deploy diagnostics gate behavior | see "Pre-deploy diagnostics gate" above |
