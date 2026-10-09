# Changelog

All notable changes to this plugin are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this plugin adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.4.0] — 2026-10-09

### Added

- **Education Cloud and Omni-Channel are now recommended companion plugins.** The new
  `education-cloud` and `service-omni` plugins are publicly available. Plugin recommendations
  can suggest them, and `/salesforce-development:plugin-install` can install them, when you work
  on Education Cloud or Omni-Channel routing tasks.
- Plugin recommendation telemetry now includes matched keywords from the plugin's curated catalog
  and a fixed project category to help improve suggestions. Only catalog-approved terms and
  predefined category codes are collected.

### Changed

- Added related-skill hints: `platform-apex-logs-debug` now points to `platform-soql-query` for slow SOQL, and `platform-metadata-deploy` and `platform-soql-query` point to `platform-apex-test-run` for post-deploy and query test runs.

### Fixed

- English catalog requests with emoji presentation selectors (such as `✔️` or `❤️`) remain
  eligible for recommendations. Selectors attached to catalog words also preserve matching.
  Accented and mixed-script requests still abstain. (W-24445750)

- Filtered prompts now preserve UTF-8 within the existing byte limit without splitting characters.
  Catalog tokens retain whole Unicode words with consistent NFC/case folding. Requests containing
  non-ASCII letters or combining marks abstain from catalog matching, including accented Latin
  requests and non-English instructions mixed with English logs, so incomplete language evidence
  cannot block tool calls. Host/incidental filtering and installed-skill routing are unchanged.
  This adds lexical consistency, not translation or multilingual semantic understanding.
  (W-24445750; [sf-skills#354 comment](https://github.com/forcedotcom/sf-skills/issues/354#issuecomment-6037899821))

- Plugin suggestions now match only the user's own words. IDE file and selection notices, task
  notifications, system reminders, URLs, file paths, slash-command names, and `UPPER_SNAKE`
  identifiers no longer trigger suggestions or block unrelated tool calls, and text inside a notice
  can no longer confirm a pending install. Prompts written mostly in a non-Latin script no longer
  trigger suggestions from their few English fragments.
  ([forcedotcom/sf-skills#354](https://github.com/forcedotcom/sf-skills/issues/354), reported by
  [@Z-kondokazuhiro](https://github.com/Z-kondokazuhiro))
- Once Claude loads the skill that owns SOQL queries, metadata retrieves, Apex test runs, or
  manifest generation, its raw `sf` commands (and, for `platform-manifest-generate`, `package.xml`
  writes) stay allowed for the rest of the session instead of only until the next message. This
  resets when a session starts, resumes, is cleared, or is compacted. Only the
  `salesforce-development:`-qualified skill name counts for the session, and a skill loaded by
  typing its slash command does not count yet.
  ([forcedotcom/sf-skills#355](https://github.com/forcedotcom/sf-skills/issues/355), reported by
  [@jvbeat](https://github.com/jvbeat))
- The `ui_mode` setting now also applies to plain-language questions such as "where am I?" or
  "what's the status of this project?". With `off`, these questions and "what can I do here?" show
  nothing. With `plain`, status and "where am I?" get the short plain-text summary. A
  `discover journey` that Claude runs on its own follows the mode too, and plain summaries now show
  the latest stage with evidence as "Current stage". Slash commands still work in every mode.
  ([forcedotcom/sf-skills#340](https://github.com/forcedotcom/sf-skills/issues/340), reported by
  [@rob-alexa](https://github.com/rob-alexa))

## [2.3.0] — 2026-10-02

### Added

- **Agentforce agent development is now a recommended companion plugin.** The `agentforce-adlc`
  plugin, which authors, tests, deploys, and observes Agentforce agents, is now publicly
  available. Plugin recommendations can suggest it, and `/salesforce-development:plugin-install`
  can install it, when you work on Agentforce agents.
- Changing a setting with `/salesforce-development:plugin-recommendations` now sends a
  privacy-preserving telemetry signal for the choice you made: disable, reset to default, a named
  sensitivity, or a custom sensitivity. The exact custom threshold and the command text are never
  collected.

### Changed

- The Apex generation and SOQL query skills now get Salesforce language-server guidance from the
  plugin at the moment the skill runs, instead of from extra text inside the skills. Apex gets
  early compile diagnostics, followed by the usual Salesforce CLI validation. SOQL queries get a
  syntax check before they run. If the language server is unavailable, both skills go straight to
  the Salesforce CLI workflow and don't stop to search for or retry the language server.

### Removed

- Plugin recommendations and `/salesforce-development:plugin-install` only install plugins from
  the Salesforce marketplace. The unused path for installing a recommended plugin from an external
  source is gone. No recommended plugin was ever hosted elsewhere, so nothing you could install
  before is affected.

### Fixed

- Salesforce MCP tools no longer stop working when an org's access token expires mid-session. The
  gateway can report an expired token as "not found"; when that happens, the plugin now gets a
  fresh token and retries once. A server that is genuinely inactive is retried again after a
  cooldown, a limited number of times, instead of staying disconnected for the rest of the session.
- Hooks no longer check the connection status of every authenticated org when they look up org
  details (on prompt submit, after Bash commands, and in status output). That check sent one token
  refresh per org, which could trip Salesforce login-anomaly detection and lock users with many
  orgs out of client orgs. The org list is now read locally; only the target org is contacted.
  The `/set-default` and `/logout` commands skip the same per-org check.
  Also fixed org details silently going missing when Claude Code forced colored CLI output.
  ([forcedotcom/sf-skills#349](https://github.com/forcedotcom/sf-skills/issues/349), reported by
  [@matt-ascendably](https://github.com/matt-ascendably))
- The deploy safety gate now recognizes Salesforce Demo Orgs (SDOs) and other active trial orgs on
  a plain My Domain as non-production, so deploys to them are no longer blocked. Production orgs
  are also classified more conservatively: a Dev Hub counts as production unless it is a sandbox,
  scratch org, or active trial, and a trial expiration date in the past no longer marks an org as a
  trial. Production orgs are now also reliably detected under Claude Code, where colored CLI output
  could previously leave an org unclassified and let the deploy through. The quick-deploy,
  destructive-deploy, and deploy-validate skills now use the same classification as the gate.
  ([forcedotcom/sf-skills#356](https://github.com/forcedotcom/sf-skills/issues/356), reported by
  [@brunoraraujo](https://github.com/brunoraraujo))

## [2.2.0] — 2026-09-21

### Added

- **Four new development capabilities:** create Custom Metadata Types and Custom Settings with
  the correct metadata shapes, manage org data from record creation through bulk import/export
  and cleanup, and verify standard-object and Tooling API fields against a bundled schema
  reference before writing queries or Apex.
- **In-chat plugin feedback.** Run `/salesforce-development:feedback` to record a 1–5 satisfaction
  rating. The command checks whether telemetry is enabled before asking, records only the numeric
  rating, and always points to GitHub Issues for detailed feedback.

### Changed

- The session journey display now chooses one actionable, confidence-ranked hint instead of
  drawing the former glyph rail. Hints distinguish urgent fixes, risks, useful next steps, and
  optional cleanup; account for scratch-org expiry, project templates, test failures, and recent
  scaffolding; and avoid repeating unchanged guidance during the same session.
- Presentation mode and plugin-recommendation settings now appear as selectable configuration
  options. Presentation modes are `full`, accessible semantic `plain`, and `off`; the former
  `compact` mode has been retired.
- Reduced the core plugin's eagerly loaded context by moving specialized skills into companion
  plugins and shortening skill descriptions while preserving their discovery effectiveness.

### Fixed

- Freshly scaffolded projects now receive framework-aware build guidance instead of premature
  deploy or test advice, including support for composed shell commands and the canonical
  `sf template generate project` command.
- Salesforce CLI update notices now compare against the version actually running, so a completed
  auto-update is no longer reported as still pending.
- A temporarily unreachable org remains visible as a connectivity warning even after the project
  journey has advanced beyond the Connect stage.

### Removed

- **Code-quality capabilities moved to a new `salesforce-code-quality` plugin.** The Code
  Analyzer skills (`dx-code-analyzer-run`, `dx-code-analyzer-configure`,
  `dx-code-analyzer-custom-rule-create`), the `platform-architecture-analyze`
  Well-Architected review skill, and the read-only `architecture-review` agent are no longer
  part of this plugin — they now ship in the standalone `salesforce-code-quality` plugin.
  Install that plugin to keep static analysis, custom-rule authoring, and Well-Architected
  review available. This is a packaging move rather than the end of support for those
  capabilities, so it ships as part of this minor release while trimming the eagerly-loaded
  skill-listing footprint of the core plugin.

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
