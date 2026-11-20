# Changelog

All notable changes to this plugin are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this plugin adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.4.0] — 2026-11-20

### Changed

- Updated skills: `experience-ui-bundle-custom-app-generate`, `experience-ui-bundle-mfa-configure`, `experience-ui-bundle-site-generate`.

## [0.3.0] — 2026-10-30

### Changed

- Updated skills: `experience-ui-bundle-2gp-deploy`, `experience-ui-bundle-features-generate`, `experience-ui-bundle-mfa-configure`, `experience-ui-bundle-project-generate`.

## [0.2.1] — 2026-10-02

### Changed

- Most of the UI bundle skills' helper scripts are now cross-platform Node.js scripts instead of
  shell scripts, so more of the workflow runs on Windows.

## [0.2.0] — 2026-09-21

### Added

- The plugin now bundles the full UI bundle skill set: app coordination
  (`experience-ui-bundle-app-coordinate`), custom apps (`experience-ui-bundle-custom-app-generate`),
  features (`experience-ui-bundle-features-generate`), file upload
  (`experience-ui-bundle-file-upload-generate`), metadata (`experience-ui-bundle-metadata-generate`),
  Salesforce data access (`experience-ui-bundle-salesforce-data-access`), an Agentforce client
  (`experience-ui-bundle-agentforce-client-generate`), MFA (`experience-ui-bundle-mfa-configure`),
  localization (`experience-ui-bundle-localize`), and deployment, including second-generation
  packaging (`experience-ui-bundle-deploy`, `experience-ui-bundle-2gp-deploy`).
- Project generation and localization now support Angular in addition to React. Localization
  covers B2C sites, including route language and the initial-language override.
- Deploying a UI bundle to a site can now also set the site's logout URL.

## [0.1.0] — 2026-08-21

### Added

- Initial release. Scaffold a React UI bundle SFDX starter project
  (`experience-ui-bundle-project-generate`), generate and edit pages, components, layout, styling,
  navigation, and branding with shadcn/ui and Tailwind CSS (`experience-ui-bundle-frontend-generate`),
  and host the app on a Digital Experience site (`experience-ui-bundle-site-generate`).
