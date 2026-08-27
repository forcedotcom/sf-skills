# Changelog

All notable changes to this plugin are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this plugin adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Support for the Codex agent, alongside Claude Code.

- A "test-drive" plugin to help demonstrate the possibilities of developing and interacting
  with Salesforce orgs.

## [2.0.0] — 2026-08-26

### Added

- **Plugin discovery, recommendation, and installation.** Capability matching now works
  with a curated list of Salesforce marketplace plugins. When a task doesn't match any
  skill you already have installed, this plugin can suggest a marketplace plugin that
  does — at the start of a session, as you type a prompt, or when you explicitly ask with
  `discovery plugins <text>`. Accepting a suggestion walks you through a guarded install: a
  plugin from this same marketplace installs with one confirmation, while a plugin from
  outside this repo (e.g., agentforce-adlc) shows you its source and a trust warning and
  asks you to confirm it before installing.

  Control how readily plugins get suggested with
  `/salesforce-development:plugin-recommendations on|off|status|set <level-or-number>` (or
  the `plugin_match_sensitivity` install-level setting). `off` turns suggestions off
  entirely. `low` (6.0), `standard` (3.5; the default), and `high` (3.0) run from least to
  most likely to suggest a plugin — `high` suggests more often, `low` holds back for more
  obvious matches. You can also set a precise number from `1.0` to `10.0`, which runs the
  opposite direction: `10.0` sets a very high bar and needs a very strong match before suggesting
  anything, while numbers closer to `1.0` suggest more readily.

  See [`.claude-plugin/marketplace.json`](https://github.com/forcedotcom/sf-skills/blob/main/.claude-plugin/marketplace.json)
  in the `forcedotcom/sf-skills` repo for the current list of plugins eligible for
  recommendation.

### Removed

- The `agentforce-generate`, `agentforce-observe`, and `agentforce-test` skills, and the
  `adlc-author`, `adlc-engineer`, `adlc-orchestrator`, and `adlc-qa` agents, are no longer
  bundled with this plugin. Agentforce ADLC assistance now comes from the separate
  `agentforce-adlc` plugin, discoverable through Salesforce plugin suggestions.

- Individual Salesforce skill discovery and installation has been replaced with Salesforce plugin
  discovery, suggestion, and installation.

## [1.12.0] — 2026-08-21

### Changed

- Refreshed the capability catalog against the latest public skill release, so `overview`,
  `domain`, and `index` now show 26 more skills you can add.

### Security

- Telemetry now only reports error information from a fixed, recognized set of categories —
  anything else is reported as `"unknown"`, so it can't leak unexpected data.
- Telemetry's on-disk files (org cache, buffers, transmit log, machine ID) are now restricted to
  owner-only access.
- Turning telemetry off now also purges any telemetry data that was already buffered or logged,
  instead of leaving it behind.
- The `telemetry on|off|status` command now reports failure instead of silently succeeding if it
  can't actually read or change telemetry state, so a hard-off you request can be trusted to have
  taken effect.

## [1.11.0] — 2026-08-14

### Added

- Usage telemetry to help us improve the plugin. On by default and disclosed on first use, it
  never collects source code, org contents, file paths, credentials, or org names. Manage it
  with `/salesforce-development:telemetry on|off|status`, or `SF_DISABLE_TELEMETRY` /
  `DO_NOT_TRACK` for a permanent opt-out.
- Service Cloud is now its own domain in the capability catalog — help agents, digital
  engagement, and ITSM/CMDB setup now show up alongside the other domains when you run
  `overview` or `domain`.

### Changed

- Refreshed the capability catalog against the latest public skill release, so `overview`,
  `domain`, and `index` now show 34 more skills you can add.
- Four common operations — SOQL queries, metadata retrieve, running Apex tests, and generating
  deploy manifests — now always route through their owning skill instead of just suggesting it,
  so you consistently get the validated workflow, governor-limit/FLS guardrails, and error
  recovery those skills provide.

### Fixed

- The plugin's Salesforce agents (`salesforce-dev`, the `adlc-*` agents, and
  `architecture-review`) can now actually check for and dispatch a matching skill before falling
  back to raw Salesforce CLI commands, closing a gap where they silently bypassed your installed
  skills. ([forcedotcom/sf-skills#325](https://github.com/forcedotcom/sf-skills/issues/325))
- The plugin no longer leaves stray `.sf/` scratch folders behind in whatever directory a
  session happens to run from — its internal skill-dispatch tracking now lives outside your
  project folders entirely, including in directories with no Salesforce project at all.
  ([forcedotcom/sf-skills#326](https://github.com/forcedotcom/sf-skills/issues/326))

## [1.10.0] — 2026-08-05

### Added

- New ambient UI modes — `full`, `compact`, `plain`, or `off` — so you can match the plugin's
  visual style to your terminal or accessibility needs.
- A status line option that shows your current Salesforce project context at a glance.
- Friendlier progress messages while the plugin loads your project context at the start of a
  session.

### Changed

- Session startup is faster and now works from local project context first, so you see relevant
  information sooner.
- This plugin now requires Claude Code 2.1.222 or later.

### Fixed

- Your discovery journey (Connect → Project → Build → Test → Deploy → Observe) now only marks the
  Test stage complete after a real, successful Apex test run, so your progress reflects genuine
  outcomes. You can review or reset this history at any time.

### Security

- Descriptions of skills you haven't installed are no longer shown through capability discovery —
  only skills verified as installed and unmodified reveal their descriptions.
