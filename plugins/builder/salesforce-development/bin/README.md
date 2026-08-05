# bin/ — vendored Salesforce LSP runtime

Prebuilt, **vendored** artifacts for the `salesforce-lsp` MCP server.
**Do not hand-edit** — regenerate from source and re-vendor.

This directory (and `../vendor/apex-ls/dist/`) is deliberately re-included in the
repo-root `.gitignore`, which otherwise blocks `bin/` and `dist/`. The host
resolves these files by fixed plugin-relative path, so they must live here.

| File | What |
|---|---|
| `sf-lsp-host.bundled.js` | The `salesforce-lsp` MCP host (esbuild bundle). Wired in `../.mcp.json`. Spawns the Apex + SOQL language servers lazily. |
| `soql-lsp.bundled.js` | Self-contained SOQL language server (esbuild bundle). Spawned by the host. |
| `lsp-precheck` / `lsp-precheck.bundled.js` | PreToolUse pre-deploy Apex-diagnostics gate. Wired via `if`-field hooks in `../.claude-plugin/plugin.json`. Fail-open. |
| `lsp-doctor` / `lsp-doctor.bundled.js` | Install-level diagnostic CLI. `--json` / `--no-spawn` flags. |

The `.bundled.js` files are single-file esbuild bundles (only Node built-ins are
external). The bare `lsp-precheck` / `lsp-doctor` are thin bash shims that set
`CLAUDE_PLUGIN_ROOT` and `exec node …bundled.js`.

## Scope: Apex + SOQL only (no LWC)

A full LSP runtime would also vendor a ~36 MB `@salesforce/lwc-language-server`
`node_modules` tree (spawned by path). This plugin **omits** it to keep the
committed footprint small. The host still registers `lwc.*` tools, but they
return an unavailable envelope here — see the `platform-lsp-integrate` skill. Apex
diagnostics come from the vendored `../vendor/apex-ls/` bundles; SOQL from
`soql-lsp.bundled.js`.

## Apex language server

`@salesforce/apex-ls` is **not published to public npm** — it is built from the
`apex-language-support` monorepo and committed as a prebuilt bundle at
`../vendor/apex-ls/dist/{server.node.js,worker.platform.js}`. The pinned version
is recorded in `../vendor/apex-ls/VERSION`.

That bundle embeds third-party code (`data-structure-typed` (MIT), the ANTLR4
runtime (BSD-3-Clause), and `vscode-jsonrpc` (MIT)) with original copyright
notices intact — see `../NOTICE` for the full attribution, along with the other
bundled MCP dependencies.

`soql-lsp.bundled.js` embeds the same ANTLR4 runtime (used to parse SOQL) and
`vscode-jsonrpc` — also attributed in `../NOTICE`.
