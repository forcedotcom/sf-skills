---
name: sfmc-sdk-migrator
description: >-
  Upgrade an existing Salesforce Marketing Cloud mobile SDK (SFMC, MCE, MAM,
  MarketingCloudSdk, MarketingCloudSDK, or SFMCSdk) integration on Android
  (Kotlin/Java, Gradle) or iOS (Swift/Objective-C, CocoaPods/Swift Package Manager).
  Use for SDK version bumps, legacy-to-unified migrations, deprecated API
  replacements, or SFMC dependency pin updates in build.gradle, libs.versions.toml,
  Podfile, or Package.swift. Scans usage, updates dependencies and mapped call
  sites, validates the app, and produces a migration report with manual review
  items. Excludes unrelated dependency upgrades, new SDK integrations, new
  application features, and server-side Marketing Cloud configuration.
---

# SFMC SDK Migrator

Upgrade the customer's existing mobile SDK integration while preserving business
logic. Deliver changes to dependencies, configuration, and mapped SDK call sites,
plus an evidence-based migration report.

Bundled scripts require Python 3.10+. Published version checks require network
access. App validation requires Gradle/JDK for Android or macOS/Xcode and
CocoaPods or Swift Package Manager for iOS.

## Required context

- **project**: existing app directory. Use the current workspace when it clearly
  contains the intended app; otherwise ask for the path. Resolve relative paths
  against the caller's working directory and verify the directory exists.
- **platform**: Android or iOS, inferred from the app's build files. In a repository
  containing both, scan each separately and clarify scope when needed.
- **from**: use the scanner's `detected.currentVersion`. Ask only if unresolved,
  `detected.versionConflict` is true, or it conflicts with a user-supplied version.
- **to**: use the requested version or version line. If missing, offer the target
  options from the catalog and ask which upgrade the user wants. Do not silently
  choose a target or present a seed catalog as current release information.

Use the client's available question mechanism or ordinary conversation; no
particular client's tool names or slash commands are required.

## Rules

- Every API rewrite must trace to an explicit migration-matrix entry. Leave
  uncovered or ambiguous APIs unchanged and record `file:line`, the reason, and a
  concrete next step under manual review. Prefer a user-provided newer matrix.
- Use only the chosen platform's references. Read the
  [matrix format](references/migration-matrix-format.md) before applying mappings.
  Consult [detailed mechanics](references/migration-workflow.md) for the relevant
  phase, platform traps, artifact inspection, and known-issue verification.
- Preserve contact keys, event names, attributes, notification handling, and
  surrounding application logic. Avoid unrelated formatting and dependency edits.
- `marketingcloudsdk` / `MarketingCloudSDK` remains an engagement module in the
  unified SDK; its presence alone does not mean the app needs a full migration.
- Bundled catalogs and matrix module versions are snapshots. Resolve published
  versions at runtime, honor exact user pins, and report offline fallbacks.
  Independent module versions must not be derived from the umbrella version.
- Work directly for small migrations. Use the optional
  [parallel refactor protocol](references/parallel-refactor.md) only when worker
  delegation is permitted and useful; otherwise complete the same work serially.

## Workflow

Commands below run from the **installed skill directory**. Pass the customer's
absolute project path; do not assume `scripts/` exists in their repository.

### 1. Scan the existing integration

```bash
python3 scripts/scan_usage.py <project> --platform <android|ios> --json
```

Read `detected.currentVersion`, `detected.apiEra`, `detected.migrationStatus`,
`detected.versionConflict`, `featuresInUse`, and `findings`. Inspect the relevant
build files to reconcile detection. No SDK dependency means there is nothing to
upgrade: report that finding and clarify the project or module. An already modern
app can still need a version bump; do not rewrite valid engagement APIs merely
because the scanner finds them.

### 2. Resolve the upgrade

```bash
# Offer choices if no target was supplied.
python3 scripts/target_options.py --current <from> --platform <android|ios>
# Resolve a chosen exact version or partial version line.
python3 scripts/target_options.py --current <from> --target <to> --platform <android|ios>
```

Report `resolvedTarget` and any `targetResolutionNote`; partials expand against
the bundled catalog. Stop on an unresolvable target or downgrade; equal versions
need no changes. Honor `migrationKind`: `version-config-bump` skips call-site
refactoring, while `full-code-migration` crosses the legacy/unified boundary.
Both paths require validation and a report. State project, platform, and versions
before editing.

### 3. Update dependencies and configuration

Load the relevant matrix and catalog:

| Platform | Mappings | Version notes | Refactoring examples |
| --- | --- | --- | --- |
| Android | [Matrix](references/migration-matrix-android.json) | [Catalog](references/version-catalog-android.json) | [Patterns](references/refactoring-patterns-android.md) |
| iOS | [Matrix](references/migration-matrix-ios.json) | [Catalog](references/version-catalog-ios.json) | [Patterns](references/refactoring-patterns-ios.md) |

Use `scripts/resolve_versions.py --help` for published-version verification via
Maven, CocoaPods, or SPM. Existence of each module version does not establish that
the set is compatible; dependency resolution and the app build provide that check.

Update only the required dependencies, manifests, entitlements, and toolchain
settings using the selected version's requirements. Surface blocking platform
constraints before changing supported OS versions. Keep the engagement module;
add only modules used by the app. Treat iOS Notification Service Extensions as
separate targets and flag their migration for manual review. See Phase 3 in
[detailed mechanics](references/migration-workflow.md) for platform-specific steps.

### 4. Refactor mapped call sites

For a full migration, read the platform's refactoring patterns and apply matching
matrix entries. Preserve async readiness and dependent control flow, configure
every detected feature, retain event validation guards, and verify delegate
signatures. Inspect shipped artifacts if a mapping's API shape is uncertain.
Record unsupported cases rather than inventing replacements.

### 5. Validate and report

Resolve dependencies and build with the customer's available toolchain:

- **Android**: `./gradlew assembleDebug`, or the app's appropriate module/variant.
- **iOS**: `pod install --repo-update` or `xcodebuild -resolvePackageDependencies`,
  then build the actual workspace/project and scheme for the simulator.

For applicable shipped-artifact issues with a matrix `verify` block, run
`scripts/verify_known_issue.py` after dependency resolution and apply its verdict
as described in Phase 5 of [detailed mechanics](references/migration-workflow.md).
Do not emit a known defect as confirmed without reproducing it.

Review the final diff for lost business logic and unexpected edits. Rescan and
account for remaining findings; engagement symbols may legitimately remain.
Record actual command results. A failed or unavailable build leaves validation
incomplete and must be reported that way.

Produce the [migration report](assets/report-template.md) with from/to versions,
exact module pins and their sources, changed files and call sites, manual review
items, build evidence, and runtime checks for initialization, push, and events.
Runtime checks are developer follow-ups unless actually performed; the migration
request alone does not authorize sending a test push.
