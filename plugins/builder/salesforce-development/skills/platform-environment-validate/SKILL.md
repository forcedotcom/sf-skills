---
name: platform-environment-validate
description: "Validate and configure the local Salesforce development environment. Runs a prerequisite scan showing 🔴/🟡/🟢 status for all required tools (Salesforce CLI, Code Analyzer plugin, Node.js, NPM, Git, Salesforce MCP, Source Tracking) and offers to install or update missing/outdated items. TRIGGER when the user runs /salesforce-development:platform-environment-validate, asks to 'check my setup', 'validate tools', 'verify prerequisites', 'am I set up correctly', or reports that a tool is missing or not working. DO NOT TRIGGER for: org authentication issues (use /salesforce-development:login), deployment problems (use platform-metadata-deploy), or general status checks (use /salesforce-development:status)."
allowed-tools:
  - Bash
  - Read
---

# Validating: Salesforce Development Environment

Validate all required prerequisites and surface a clear, actionable status report. This skill is on-demand — it does not run automatically on session start. Run it explicitly to check or repair your local setup.

## Phase 1: Prerequisite Scan

Run the tool check:

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/sf-context check-tools
```

The output is a JSON object with a `tools` array (plus a `diagnostic` block on any critical failure).

**The banner is painted for you — do not reproduce it.** When `check-tools` runs, the plugin paints the framed **"Ready to build on Salesforce?"** banner deterministically on the visible channel — one status row per tool, the footer verdict, and the wayfinding footer — exactly like the SessionStart banner. It is a **Tier-1 surface**: read the JSON for your own understanding, but do **NOT** reproduce, redraw, or re-render the banner. Add only a short read of what the result means for the user, then go to **Phase 2**.

The painted banner looks like this (illustrative — the version/message text in each row comes straight from the JSON: `version` for 🟢, `message` + fix hint for 🟡/🔴, the note for ℹ️; the values below show the style, not fixed strings):

```
──────────────────────────────────────────────────────────────
 Ready to build on Salesforce?   checking your toolchain…
──────────────────────────────────────────────────────────────
 🟢 Salesforce CLI             v2.144.6
 🟢 Code Analyzer              v5.14.0 · JIT, auto-installs on first use
 🟢 Node.js                    v22.11.0 LTS
 🟢 NPM                        v10.9.0
 🟢 Git                        v2.50.1
 🟢 Salesforce MCP (config)    .mcp.json + proxy present
 🟢 Salesforce MCP (endpoint)  org instance reachable
 ℹ️  Salesforce MCP (process)   confirm with /mcp or /doctor
 🟢 Source Tracking            enabled
──────────────────────────────────────────────────────────────
 ✓ toolchain ready                                (skill: platform-environment-validate)
```

Each row's status dot carries the state — 🔴 `critical` (missing or below minimum — Salesforce development cannot proceed), 🟡 `warn` (installed but outdated, non-LTS, or misconfigured), 🟢 `ok`, ℹ️ `info` (a contextual note that can't be auto-verified, e.g. MCP process health) — and the framed footer gives the verdict plus the single most relevant `Next:` step. The JSON `status` field is the source of truth per tool; use these states when you write your short read.

**If the banner did not paint** (an older Claude Code build, or a paint fallback), do **not** hand-render it from the JSON. Print it with the deterministic renderer instead:

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/sf-context readiness-banner
```

This reads the same scan result `check-tools` just recorded and prints the identical framed banner — rows in fixed order, the footer verdict, and the "you don't memorize commands here" wayfinding footer with its `Next:` step — so ordering, padding, counts, and next-step selection are decided once in the script, never re-derived by hand. The `check-tools` JSON stays the authoritative, machine-readable result.

**Deterministic results — do NOT override a failure:** the JSON report
is the authoritative, machine-readable result. If a tool reports 🔴/🟡, report it
as-is. Do **not** re-run the tool a different way (PowerShell, a raw shell probe,
a different command) and then present the result as 🟢 — a fallback that happens
to find the tool does **not** mean the deterministic check passed. A failed check
must stay failed until that **same** `check-tools` check passes. When the report
includes a `diagnostic` block (attached on any critical failure), surface it: it
carries the platform, active shell, working directory, plugin root, and the
**resolved executable paths** — the fastest way to see why a tool didn't resolve
(e.g. a Windows `sf.cmd` not on `PATH`). The diagnostic is secret-free by design;
never add tokens or org auth to it.

**MCP is reported as three distinct rows — never inferred from one another:**
`Salesforce MCP (config)` (is `.mcp.json` + the `sf-mcp-proxy.bundled.js` present?),
`Salesforce MCP (endpoint)` (is the platform endpoint reachable?), and
`Salesforce MCP (process)` (is the MCP process actually healthy?). The process row
is reported as ℹ️ **informational** (not a warning) — this script cannot see the
MCP subprocess that Claude Code owns, so a green config/endpoint must **not** be
presented as a working MCP. Confirm process health with `/mcp` or `/doctor`. The
endpoint row probes the org **instance URL** as a connectivity proxy, not the
platform-MCP endpoint itself.

## Tools Checked

| Tool | Minimum Requirement | Verification |
|---|---|---|
| Salesforce CLI | Present, and on the latest release | `sf --version` (🟡 when an update is available) |
| Code Analyzer plugin | Installed **or** JIT-registered | `sf plugins inspect @salesforce/plugin-code-analyzer`, falling back to the CLI's `oclif.jitPlugins` registry |
| Node.js | >= 18 (even/LTS) | `node --version` |
| NPM | >= 3.10 | `npm --version` |
| Git | Must be present | `git --version` |
| Salesforce MCP (config) | `.mcp.json` configured + proxy bundle present | Plugin root `.mcp.json` check + `sf-mcp-proxy.bundled.js` presence |
| Salesforce MCP (endpoint) | Org instance URL reachable (connectivity proxy) | HTTP probe of org instance URL |
| Salesforce MCP (process) | ℹ️ informational — not verifiable here | Confirm with `/mcp` or `/doctor` |
| Source Tracking | Enabled for connected org | `sf project deploy preview` |

All external tools (`sf`, `npm`, `node`, `git`) are launched through a single
cross-platform resolver: `shutil.which` (PATHEXT-aware) finds the tool,
and a Windows `.cmd`/`.bat` shim (`sf.cmd`, `npm.cmd`) is invoked via a
COMSPEC-wrapped argv array — never a shell string — so this scan and
`/salesforce-development:org` detect `sf`/`npm`/the default org correctly on
Windows, macOS, and Linux.

**Code Analyzer is a JIT plugin — registered ≠ installed.** The Salesforce CLI
declares `@salesforce/plugin-code-analyzer` as a "just-in-time" (JIT) plugin: it
is only physically installed the first time a `sf code-analyzer` command runs.
Until then, `sf plugins inspect` **fails** for it even though it is fully
available to the user. The check therefore treats JIT registration as success —
if `inspect` returns no version, it falls back to the CLI's own
`oclif.jitPlugins` registry (read from the root entry of `sf plugins --json`) and
reports 🟢 with the pinned version and a note that it auto-installs on first use.
Only a plugin that is neither installed nor JIT-registered is 🔴 critical.

## Phase 2: Install / Update

**If all green:** Confirm setup is complete. The user is ready to develop.

**If warnings or critical items exist:** Present the user with options:

```
Some tools need attention. What would you like to do?

  [1] Fix all items
  [2] Choose which items to fix
  [3] Skip for now
```

For each tool the user wants to fix, provide the correct install/update command for their OS. Do **not** run install commands automatically — show the command and ask the user to confirm before running it.

### Install / Update Commands by Tool

**Salesforce CLI — not installed:**
```bash
# macOS/Linux (npm)
npm install --global @salesforce/cli

# macOS (Homebrew)
brew install sf
```

**Salesforce CLI — update:**
```bash
sf update
```

**Code Analyzer plugin — not installed:**
```bash
sf plugins install @salesforce/plugin-code-analyzer
```

**Code Analyzer plugin — update:**
```bash
sf plugins update @salesforce/plugin-code-analyzer
```

**Node.js — not installed or below minimum:**
```bash
# macOS (nvm — recommended, installs LTS)
nvm install --lts && nvm use --lts

# macOS (Homebrew)
brew install node

# Windows — download from https://nodejs.org (LTS version)
```

**NPM — update:**
```bash
npm install --global npm@latest
```

**Git — not installed:**
```bash
# macOS (Xcode CLT)
xcode-select --install

# macOS (Homebrew)
brew install git

# Windows — download from https://git-scm.com
```

**Source Tracking — not enabled:**
```bash
sf org enable tracking --target-org <alias>
```

**Salesforce MCP — misconfigured:** If `.mcp.json` is missing or empty, reload the plugin:
```
/reload-plugins
```

## Important Notes

- After installing a tool that modifies PATH (Node.js, SF CLI), the user may need to exit and restart Claude Code for the change to take effect.
- Source Tracking requires a connected org — if no org is configured, prompt to run `/salesforce-development:login` first.
- For org authentication issues (expired session, wrong org, INVALID_SESSION_ID), run `/salesforce-development:login` instead of this skill.
- **SF CLI outdated → 🟡 in the readiness scan:** readiness means *latest*. When the CLI's cached update check reports a newer release, `check-tools` reports the Salesforce CLI as 🟡 (installed but outdated) with the correct update command, rather than 🟢. Unlike the session-start notice below, this warning ignores the per-version no-nag gate — an explicit readiness scan always reports the factual state — but it still honors the hard opt-out `SFDX_SKIP_CLI_UPDATE_CHECK=1`.
- **SF CLI update notice at session start:** when the CLI reports an available update, the `sf-context detect` SessionStart hook surfaces it once and asks the agent to offer the update (`sf update`, or `npm install --global @salesforce/cli@latest` for npm-global installs). Declining or a failed update records a **per-version** no-nag gate (`.sf/sf-cli-update-state.json`) so the same version won't nag again, but a newer release will re-prompt. Set `SFDX_SKIP_CLI_UPDATE_CHECK=1` to disable the check entirely.
