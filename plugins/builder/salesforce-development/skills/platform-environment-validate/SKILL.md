---
name: platform-environment-validate
description: "Validate and configure the local Salesforce development environment. Runs a prerequisite scan across required tools with per-tool status and offers to install or update missing items. Use when the user asks to 'check my setup', 'validate tools', 'verify prerequisites', 'am I set up correctly', or reports a tool is missing or not working. DO NOT TRIGGER for org auth (/salesforce-development:login), deployment problems (platform-metadata-deploy), or status checks (/salesforce-development:status)."
metadata:
  internal: true
  domains: ["Platform"]
  relatedSkills: ["platform-metadata-deploy"]
  cliTools:
    - tool: ["sf"]
      semver: ">=2.0.0"
    - tool: ["npm"]
      semver: "*"
    - tool: ["node"]
      semver: "*"
    - tool: ["git"]
      semver: "*"
allowed-tools:
  - Bash
  - Read
---

# Validating: Salesforce Development Environment

Validate all required prerequisites and surface a clear, actionable status report. This skill is on-demand — it does not run automatically on session start. Run it explicitly to check or repair your local setup.

**Plugin required.** This skill runs commands that ship with its plugin, and a standalone `npx skills add` install doesn't include them. If one of those commands isn't found, or `CLAUDE_PLUGIN_ROOT` is empty, tell the user this skill needs its plugin installed. Don't improvise a replacement for the command. Where a step says what to do when its command fails, do that.

## Phase 1: Prerequisite Scan

Run the tool check:

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/sf-context check-tools
```

The output is a JSON object with a `tools` array (plus a `diagnostic` block on any critical failure).

**The banner is painted for you — do not reproduce it.** When `check-tools` runs, the plugin paints the framed **"Ready to build on Salesforce?"** banner deterministically on the visible channel — one status row per tool, the footer verdict, and the wayfinding footer — exactly like the SessionStart banner. It is a **Tier-1 surface**: read the JSON for your own understanding, but do **NOT** reproduce, redraw, or re-render the banner. Add only a short read of what the result means for the user, then go to **Phase 2**.

The painted banner looks like this (illustrative — the version/message text in each row comes straight from the JSON: `version` for READY, `message` + fix hint for WARN/CRITICAL, the note for INFO; the values below show the style, not fixed strings):

```
──────────────────────────────────────────────────────────────
 Ready to build on Salesforce?   checking your toolchain…
──────────────────────────────────────────────────────────────
 READY Salesforce CLI             v2.144.6
 READY Code Analyzer              v5.14.0 · JIT, auto-installs on first use
 READY Node.js                    v22.11.0 LTS
 READY NPM                        v10.9.0
 READY Git                        v2.50.1
 READY Salesforce MCP (config)    .mcp.json + proxy present
 READY Salesforce MCP (metadata-experts) Server active and reachable
 READY Salesforce MCP (metadata-grounding) Optional; endpoint reachable
 INFO  Salesforce MCP (headless-360) Optional; local opt-in unknown. Recommended for live Setup settings…
 INFO  Salesforce MCP (process)   confirm with /mcp or /doctor
 READY Source Tracking            enabled
──────────────────────────────────────────────────────────────
 PASS toolchain ready                                (skill: platform-environment-validate)
```

Each row's status label carries the state — CRITICAL `critical` (missing or below minimum — Salesforce development cannot proceed), WARN `warn` (installed but outdated, non-LTS, or misconfigured), READY `ok`, INFO `info` (a contextual note that can't be auto-verified, e.g. MCP process health) — and the framed footer gives the verdict plus the single most relevant `Next:` step. The JSON `status` field is the source of truth per tool; use these states when you write your short read.

**If the banner did not paint** (an older Claude Code build, or a paint fallback), do **not** hand-render it from the JSON. Print it with the deterministic renderer instead:

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/sf-context readiness-banner
```

This reads the same scan result `check-tools` just recorded and prints the identical framed banner — rows in fixed order, the footer verdict, and the "you don't memorize commands here" wayfinding footer with its `Next:` step — so ordering, padding, counts, and next-step selection are decided once in the script, never re-derived by hand. The `check-tools` JSON stays the authoritative, machine-readable result.

**Deterministic results — do NOT override a failure:** the JSON report
is the authoritative, machine-readable result. If a tool reports CRITICAL/WARN, report it
as-is. Do **not** re-run the tool a different way (PowerShell, a raw shell probe,
a different command) and then present the result as READY — a fallback that happens
to find the tool does **not** mean the deterministic check passed. A failed check
must stay failed until that **same** `check-tools` check passes. When the report
includes a `diagnostic` block (attached on any critical failure), surface it: it
carries the platform, active shell, working directory, plugin root, and the
**resolved executable paths** — the fastest way to see why a tool didn't resolve
(e.g. a Windows `sf.cmd` not on `PATH`). The diagnostic is secret-free by design;
never add tokens or org auth to it.

**MCP reports configuration, required-server probes, and process visibility separately:**
`Salesforce MCP (config)` (are `.mcp.json` and the required proxy bundle present?),
the individually probed required servers, and `Salesforce MCP (process)` (is the MCP process
actually healthy?). Headless 360 has a separate optional row: a missing launcher warns;
otherwise it reports local opt-in and endpoint evidence. Known-enabled opt-in allows an
on-demand probe outside hook deadlines. Disabled/unknown opt-in never probes. Cached
health is labeled **Last observed** and must match the selected org. Reachable endpoints
do not prove host tool exposure. Claude commands may not receive the plugin option;
report unknown and point to `/plugin` in that case. Codex reads its saved local preference.
Recommend H360 for better answers about live Setup settings and org-specific caps.
If a probe reports inactive, direct the user to org Setup → Quick Find **MCP Servers** →
**MCP Servers** under **API Catalog** → toggle **Headless360** on. Allow up to two minutes,
then rerun status. Do not activate it automatically. See the
[activation guide](https://developer.salesforce.com/docs/platform/hosted-mcp-servers/guide/activate-mcp-servers.html).
Metadata grounding has a separate optional row too. It is probed on demand outside hook
deadlines, and cached readings are labeled **Last observed**. When the server is not connected
the row reports WARN, never CRITICAL. Grounding needs Salesforce Catalog: an admin with a Data
Cloud license turns on Catalog through Feature Manager in Data Cloud Setup. Then the admin
searches **MCP Servers** in Setup and activates **metadata-grounding**. The same warning also
covers a network or VPN problem. Do not activate it automatically. Without grounding, the
grounding skills fall back to name matching.
Optional warnings do not block scaffolding or affect required-server health.
The process row is reported as INFO **informational** (not a warning) — this script cannot see the
MCP subprocess that Claude Code owns, so a green config/endpoint must **not** be
presented as a working MCP. Confirm process health with `/mcp` or `/doctor`.

## Tools Checked

| Tool | Minimum Requirement | Verification |
|---|---|---|
| Salesforce CLI | Present, and on the latest release | `sf --version` (WARN when an update is available) |
| Code Analyzer plugin | Installed **or** JIT-registered | `sf plugins inspect @salesforce/plugin-code-analyzer`, falling back to the CLI's `oclif.jitPlugins` registry |
| Node.js | >= 18 (even/LTS) | `node --version` |
| NPM | >= 3.10 | `npm --version` |
| Git | Must be present | `git --version` |
| Salesforce MCP (config) | `.mcp.json` and required proxy bundle present | Plugin root `.mcp.json` check + `sf-mcp-proxy.bundled.js` presence |
| Salesforce MCP (metadata-experts) | The required server active and reachable in the target org | Live per-server proxy `--probe`; optional grounding and Headless 360 are reported separately |
| Salesforce MCP (metadata-grounding) | Optional; needs Salesforce Catalog and an activated server | Live proxy `--probe` on demand; cached readings are labeled. Not connected warns, never blocks |
| Salesforce MCP (Headless 360) | Optional local setup and endpoint status | Known-enabled opt-in permits an on-demand probe; disabled/unknown does not probe. Cached readings are labeled; host tools are verified separately |
| Salesforce MCP (process) | INFO informational — not verifiable here | Confirm with `/mcp` or `/doctor` |
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
reports READY with the pinned version and a note that it auto-installs on first use.
Only a plugin that is neither installed nor JIT-registered is CRITICAL critical.

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
- **SF CLI outdated → WARN in the readiness scan:** readiness means *latest*. When the CLI's cached update check reports a newer release, `check-tools` reports the Salesforce CLI as WARN (installed but outdated) with the correct update command, rather than READY. Unlike the session-start notice below, this warning ignores the per-version no-nag gate — an explicit readiness scan always reports the factual state — but it still honors the hard opt-out `SFDX_SKIP_CLI_UPDATE_CHECK=1`.
- **SF CLI update notice at session start:** when the CLI reports an available update, the `sf-context detect` SessionStart hook surfaces it once and asks the agent to offer the update (`sf update`, or `npm install --global @salesforce/cli@latest` for npm-global installs). Declining or a failed update records a **per-version** no-nag gate (`.sf/sf-cli-update-state.json`) so the same version won't nag again, but a newer release will re-prompt. Set `SFDX_SKIP_CLI_UPDATE_CHECK=1` to disable the check entirely.
