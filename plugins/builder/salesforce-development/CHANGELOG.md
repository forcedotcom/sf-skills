# Changelog

All notable changes to this plugin are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this plugin adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
