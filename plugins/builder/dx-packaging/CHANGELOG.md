# Changelog

All notable changes to this plugin are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this plugin adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] — 2026-11-06

### Added

- Initial release. Automate managed-package setup in subscriber orgs after installation
  (`dx-pkg-post-install-configure`, previously bundled with `dx-org-lifecycle`); plan,
  schedule, monitor, or abort package push upgrades across subscriber orgs
  (`dx-packaging-push-upgrade-configure`); and check eligibility for, then finalize, the
  one-way move of a converted 1GP managed package to 2GP development
  (`dx-packaging-move-to-2gp-migrate`).
