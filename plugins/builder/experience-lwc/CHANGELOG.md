# Changelog

All notable changes to this plugin are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this plugin adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.4.0] — 2026-11-20

### Changed

- Updated skills: `experience-lwc-accessibility-jest-run`.

## [0.3.0] — 2026-10-16

### Added

- Native Codex plugin packaging and advisory post-edit checks for contained LWC files in an
  SFDX project. Automatic checks use bundled Python SLDS/template validators only; optional
  SLDS Linter and Code Analyzer require explicit validation. Claude registration is unchanged.

## [0.2.0] — 2026-09-21

### Added

- The plugin now bundles the full Lightning Web Components skill set:
  - Accessibility: accessibility Jest test runs (`experience-lwc-accessibility-jest-run`).
  - Migration: Aura to LWC (`experience-aura-lwc-migrate`), Aura-to-LWC completeness checks and
    Lightning Out Beta to Lightning Out 2.0 (`experience-lwc-legacy-migrate`), and JavaScript to
    TypeScript (`experience-lwc-typescript-migrate`).
  - Lightning Data Service: best practices (`experience-lds-best-practices-apply`), data
    requirements (`experience-lds-data-requirements-generate`), and GraphQL queries and
    mutations (`experience-lds-graphql-generate`).
  - Base component integration (`experience-lwc-base-components-integrate`), RTL validation
    (`experience-lwc-rtl-validate`), runtime observation (`experience-lwc-runtime-observe`), and
    security validation (`experience-lwc-security-validate`).

### Changed

- `experience-lwc-accessibility-validate` is renamed to `experience-accessibility-validate`. The
  WCAG/ARIA accessibility checks for LWC are unchanged.

### Fixed

- `experience-lwc-design-generate` no longer points to a skill that doesn't exist.

## [0.1.0] — 2026-08-21

### Added

- Initial release. Generate Lightning Web Components with the PICKLES methodology and 165-point
  scoring (`experience-lwc-generate`), scaffold a new LWC from a Figma design or a PRD
  (`experience-lwc-design-generate`), and validate LWC accessibility
  (`experience-lwc-accessibility-validate`).
