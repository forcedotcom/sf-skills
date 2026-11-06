# Configuration Reference

Advanced configuration for the `salesforce-development` plugin: ambient UI modes and
deploy/delete guard rails. Everyday usage only needs the [Quick
Start](../README.md#quick-start) — start here if you want to customize the experience or
understand a safety prompt.

## Ambient UI Modes

Ambient output is configured by plugin `userConfig.ui_mode` (transported to hooks as
`CLAUDE_PLUGIN_OPTION_UI_MODE`). It covers the SessionStart banner, wayfinding, and the answers the
plugin paints when you ask a natural-language status, orientation, or capability question ("what's
the status of this project?", "where am I?", "what can I do here?"):

| Mode | Ambient SessionStart and wayfinding | Natural-language status / orientation / capability questions |
|---|---|---|
| `full` (default) | signature banner and graded nudge | full status surface, welcome, or capability overview |
| `plain` | accessible semantic text, without ANSI color or journey glyphs | the same plain project / stage / next-step text (capability overview unchanged) |
| `off` | hidden | nothing painted and no guidance added to Claude's reply; Claude answers on its own |

The retired `compact` mode maps to `plain` (the nearest surviving reduced-chrome surface), so a
saved `compact` preference keeps reduced output rather than reverting to the full banner.

`NO_COLOR` removes ANSI without changing mode. Explicit status, setup, and discovery slash
commands (such as `/salesforce-development:status` and `/salesforce-development:discover`), safety
advisories/gates, failures, and install guidance remain available in every mode.

## Codex configuration and activation

Codex uses the packaged `hooks/codex-hooks.json` and fourteen command projections.
Review installed hooks through `/hooks`; an installed package alone does not establish
trusted hooks or active skills. Restart in a fresh session after installation or updates,
resubmit the request, and verify the refreshed skill inventory before continuing.

Set `SF_PLUGIN_UI_MODE=full|plain|off` in the Codex launch environment. This takes precedence
over the existing Claude UI option; Codex does not require Claude `userConfig` transport.
Turning presentation off does not disable primary-session routing instructions or safety
gates. Existing runtime environment controls, including `SFDX_LSP_DEPLOY_GATE` and telemetry
opt-outs (`DO_NOT_TRACK=true` or `SF_DISABLE_TELEMETRY=true`), remain available. Do not assume
that a setting accepted by Claude’s configuration UI is transported by Codex.

### Plugin recommendation sensitivity in Codex

Codex has no install-time plugin options, so the Claude "Plugin recommendation" install choice has
no Codex equivalent. Choose one of these instead:

- Set `SF_PLUGIN_MATCH_SENSITIVITY=off|low|standard|high|<1.0-10.0>` in the environment you
  launch the Codex CLI from. Codex passes its process environment to plugin hooks, so the setting
  applies to recommendations. This variable takes precedence over saved preferences. An invalid
  value is silently ignored: the plugin falls back to the next source, with no warning.
- Or save a preference with the plugin-recommendations command, for example
  `plugin-recommendations --project set high`. Saved preferences live under `~/.sf/` and apply in
  Claude Code and Codex alike.

In Codex, `plugin-recommendations` `set`, `on`, `off`, and `prune` write `~/.sf` outside the
workspace sandbox, so the Codex sandbox may block the write. If it does, the command asks you to
re-run it with escalation, and Codex asks you to approve that run. `status` only reads.

When the setting is not `standard`, session start shows it with its source and how to reset
it. A resumed Codex session shows the notice as it was when the session started; start a new
session to see a change.

For the `plugin default (userConfig)` source, the hint
`/salesforce-development:plugin-recommendations set standard` saves an all-projects preference. That
saved preference then takes precedence over later changes to the userConfig default, and the banner
reports it as "your saved preference for all projects".

The plugin treats a session as Codex when `SF_AGENT_CLIENT=codex` is set. Otherwise it infers the
host: Codex session markers (`CODEX_THREAD_ID`, `CODEX_SESSION_ID`, or the plugin installed under
Codex's plugin cache) mean Codex, unless Claude markers are also present (then the host is
unclear). With no Codex or Claude marker, a set `CODEX_HOME` means Codex. `SF_AGENT_CLIENT=claude`
together with a Codex marker also leaves the host unclear. With no Codex or Claude signal at
all, the host defaults to Claude.

Packaged canonical skills remain authoritative. Resolve their package-relative commands
against the owning installed plugin and supply `SF_AGENT_CLIENT=codex` on Salesforce
Development runtime calls; a hook cannot export that environment into later shell tools.
If a required child skill is missing, use supported discovery/install with consent, then
stop for fresh-session activation and verify it. Do not replace the missing workflow with
an invented implementation.

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

This option applies to Claude hooks. Codex automatic deployment after file edits stays
disabled, including when `SFDX_AUTO_DEPLOY=1` is present. Deploy through an explicit user
request and the normal safety gates.

Set `SFDX_AUTO_DEPLOY=1` to have `sf-deploy-gate auto-deploy` push a saved `force-app/**` edit
(`Write`/`Edit`/`MultiEdit`) to your default org automatically after each save. Off by default. It
refuses to run against orgs classified `production` or `unknown` regardless of the flag — the same
production guard rail above still applies.

## LSP Scope

This plugin vendors the Apex + SOQL language servers only. The LWC language server is
intentionally not bundled.
