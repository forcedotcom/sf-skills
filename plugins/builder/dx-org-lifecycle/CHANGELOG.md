# Changelog

All notable changes to this plugin are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this plugin adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] — 2026-09-28

### Removed

- Package post-install configuration (`dx-pkg-post-install-configure`) is no longer bundled with
  this plugin. It is moving to a separate Salesforce packaging plugin. This plugin now focuses on
  environment, Dev Hub, and sandbox lifecycle.

## [0.2.0] — 2026-09-21

### Added

- Dev Hub administration: enable Dev Hub and view scratch org allocation
  (`dx-org-devhub-configure`).

### Changed

- Sandbox configuration now asks you to confirm before every irreversible action, and shows the
  sandbox name, license, and status as a safety check.

### Fixed

- Refreshing a sandbox now sets the license type correctly.
- Corrected guidance on which sandbox fields can be set at creation but not on refresh.

## [0.1.0] — 2026-08-24

### Added

- Initial release. Configure and refresh sandboxes (`platform-sandbox-configure`), generate and run
  sandbox post-copy automation (`automation-sandbox-post-copy-config-generate`,
  `automation-sandbox-post-copy-configure`), create trial orgs (`platform-trial-org-create`), check
  trial expiration (`dx-org-trial-expiration-check`), assign permission sets
  (`dx-org-permission-set-assign`), set the default target org (`dx-org-switch`), and perform
  package post-install configuration (`dx-pkg-post-install-configure`).
