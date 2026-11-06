# Changelog

All notable changes to this plugin are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this plugin adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.4.0] — 2026-11-06

### Changed

- Updated skills: `service-digital-engagement-channel-configure`.

## [0.3.0] — 2026-10-30

### Changed

- Updated skills: `service-agentforce-channel-configure`, `service-agentforce-human-escalation-configure`, `service-de-channel-routing-configure`, `service-digital-engagement-channel-configure`, `service-digital-engagement-deployment-configure`, `service-email-to-case-configure`.

## [0.2.1] — 2026-10-02

### Changed

- The bundled skills now match the standalone versions published in this repository.

### Removed

- Help Agent setup no longer runs the plugin-only Agentforce dependency preflight that was added
  in 0.2.0. It uses the same advisory skills check as the standalone `service-helpagent-coordinate`
  skill.

## [0.2.0] — 2026-09-21

### Added

- Enhanced Messaging channels: create (`service-de-channel-create`), activate
  (`service-de-channel-activate`), configure routing (`service-de-channel-routing-configure`) and
  settings (`service-de-channel-settings-configure`), and set up a channel end to end without the
  provider setup popups (`service-de-headless-channel-configure`).
- Confirm a WhatsApp Business Account is shared with Salesforce (`service-de-waba-integrate`).
- Configure Email-to-Case (`service-email-to-case-configure`).
- Configure and verify Agentforce agent-to-human escalation, including a staffed fallback queue
  (`service-agentforce-human-escalation-configure`).
- Before authoring, Help Agent setup checks that the `agentforce-adlc` plugin is available and that
  the target org supports Agentforce authoring, and tells you how to install or enable the plugin
  if it is missing.

### Fixed

- Help Agent channel discovery and routing.

## [0.1.0] — 2026-08-24

### Added

- Initial release. Set up messaging and chat channels
  (`service-digital-engagement-channel-configure`), configure channel deployments
  (`service-digital-engagement-deployment-configure`), integrate a messaging site
  (`service-digital-engagement-messaging-site-integrate`), wire an Agentforce channel to an
  existing agent (`service-agentforce-channel-configure`), and coordinate a Help Agent from setup to
  go-live (`service-helpagent-coordinate`).
