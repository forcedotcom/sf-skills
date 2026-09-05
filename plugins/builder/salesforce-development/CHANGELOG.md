# Changelog

All notable changes to this plugin are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this plugin adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

- We're working to trim down the number of skills in the salesforce-development plugin
  to provide more context for additional plugins and skills. As part of this effort, we're
  also reducing the size of skill descriptions without sacrificing effectiveness.

- We're working on an easy way to provide feedback on this plugin to continually improve the
  development experience.

## [2.1.1] — 2026-09-04

### Fixed

- Accepting a plugin recommendation is now less fussy, without loosening what actually installs.
  If you pick an install option from a structured question, or say "yes"/"install it" on your very
  next message after the original suggestion scrolls off, we now act on it — as long as exactly one
  plugin was waiting on your answer. Suggesting more than one still asks you to name the one you
  mean, and declining still sticks (a later bare "yes" won't undo it). A non-trusted external plugin
  still shows its source and asks for confirmation before anything is installed.
- `setup`'s Source Tracking check no longer suggests running `sf org enable tracking` on an org
  where that can never work — source tracking is only available on scratch orgs and Developer or
  Developer Pro sandboxes. On any other edition (Enterprise, Developer Edition, trial/signup, Dev
  Hub), it now reports the org's edition as informational context instead of a dead-end warning.

## [2.1.0] — 2026-09-02

### Added

- **A new companion plugin: `salesforce-test-drive`.** Install it alongside this plugin to pick a
  curated, end-to-end build from a menu and watch it run start to finish against your own org —
  built for running a live demo and for learning the platform by watching the real thing get
  built. The first drive, **Service help agent**, builds an Agentforce service agent that answers
  customer questions, manages support cases, and hands off to a human, then deploys it as a
  website chat widget. The engine checks your setup, helps you connect or provision an org
  (including a free Agentforce Developer Edition if you need one), and only pauses for the choices
  that matter — then choreographs this plugin's skills to do the build. If you start a drive and
  come back later, it offers to resume where you left off instead of starting over.

  Try it out with:

  ```text
  /salesforce-test-drive:start
  ```

  Not sure where to start? This plugin's capability overview and welcome screen now point you at a
  test drive directly.

### Changed

- The `discovery` command is now `/salesforce-development:discover`. If you had
  `/salesforce-development:discovery` memorized, use `/salesforce-development:discover` going
  forward — the old token now returns a usage error. The underlying `discovery` concept and its
  natural-language triggers (`what can I do here?`, `where am I?`) are unchanged.
- Plugin recommendations now only ever suggest a plugin you haven't already installed — a match
  against something you already have no longer surfaces a recommendation.
- Refreshed the SessionStart banner: the ASCII-art lockup now spells **SALESFORCE**, with
  **headless · 360** as the wordmark underneath.

### Fixed

- The session-start summary of your discovery journey no longer claims you're currently at a stage
  you haven't actually reached — it now reports the last stage you completed as current, and
  separately calls out the next stage when there's a gap.

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
