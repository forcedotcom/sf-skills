# Changelog

All notable changes to this plugin are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this plugin adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.0] — 2026-11-06

### Changed

- Updated skills: `experience-cms-content-type-generate`.

### Removed

- Removed skills: `experience-content-media-stock-image-search`.

## [0.2.1] — 2026-10-02

### Changed

- The bundled skills now match the standalone versions published in this repository.

## [0.2.0] — 2026-09-21

### Added

- Render CMS content (`experience-cms-content-render`).
- Generate CMS content types (`experience-cms-content-type-generate`).

### Changed

- Stock image search (`experience-content-media-stock-image-search`) now searches for and
  downloads ethically licensed stock images through Salesforce media-management tooling.

### Removed

- `experience-content-media-search` is retired and no longer bundled. To search existing
  Salesforce CMS content and media, use the standalone `experience-search-coordinate` skill from
  [sf-skills](https://github.com/forcedotcom/sf-skills).

### Fixed

- Accessibility gaps in the CMS media renderer, including the React audio control losing its
  accessible name when alt text is absent.

## [0.1.0] — 2026-08-24

### Added

- Initial release. Apply CMS branding (`experience-cms-brand-apply`), generate CMS content
  (`experience-cms-content-generate`), search Salesforce CMS media
  (`experience-content-media-search`), and find stock imagery
  (`experience-content-media-stock-image-search`).
