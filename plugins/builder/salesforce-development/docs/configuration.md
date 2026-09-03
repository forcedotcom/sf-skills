# Configuration Reference

Advanced configuration for the `salesforce-development` plugin: ambient UI modes and
deploy/delete guard rails. Everyday usage only needs the [Quick
Start](../README.md#quick-start) — start here if you want to customize the experience or
understand a safety prompt.

## Ambient UI Modes

Ambient SessionStart output is configured by plugin `userConfig.ui_mode` (transported to hooks as
`CLAUDE_PLUGIN_OPTION_UI_MODE`):

| Mode | Ambient SessionStart and wayfinding |
|---|---|
| `full` (default) | signature banner and evidence rail |
| `compact` | one bounded project/stage/next line |
| `plain` | semantic text without ANSI or journey glyphs |
| `off` | hidden |

`NO_COLOR` removes ANSI without changing mode. Explicit status, setup, discovery, safety
advisories/gates, failures, and install guidance remain available in every mode.

## Guard Rails vs. Claude Code's Auto-Mode Classifier

This plugin's gates fire **only** on `sf project deploy`, `sf project delete`, and
destructive-changes deploys — they **never block read-only commands** (`sf org list/display`, `sf
data query`, `sf project retrieve`, source-tracking probes). Every gate emission is prefixed
`[salesforce-development · deploy-gate]`. A denial on a *read-only* command with **no such prefix**
is Claude Code's auto-mode classifier, not this plugin — a separate layer the plugin cannot
rewrite. If reads get gated, the fix is to retarget a **sandbox** (the classifier reclassifies
`production` → `sandbox` and the reads pass) or to allowlist them via `/permissions`. Routing
around a denial by re-shaping the command defeats the control while technically satisfying it —
don't.

## Opt-In Auto-Deploy

Set `SFDX_AUTO_DEPLOY=1` to have `sf-deploy-gate auto-deploy` push a saved `force-app/**` edit
(`Write`/`Edit`/`MultiEdit`) to your default org automatically after each save. Off by default. It
refuses to run against orgs classified `production` or `unknown` regardless of the flag — the same
production guard rail above still applies.

## LSP Scope

This plugin vendors the Apex + SOQL language servers only. The LWC language server is
intentionally not bundled.
