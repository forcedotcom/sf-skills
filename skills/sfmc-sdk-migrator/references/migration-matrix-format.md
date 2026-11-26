# Migration Matrix Format

The migration matrix is the single source of truth for every rewrite. It is a JSON file your team owns and updates as the SDK evolves — this is how you feed your "Breaking Changes Log" into the skill. The skill **only** rewrites code it can back with a matrix entry; anything not in the matrix gets flagged for human review instead of guessed.

There is one matrix per platform: `migration-matrix-android.json`, `migration-matrix-ios.json`, etc. All share this schema.

## Top-level shape

```jsonc
{
  "platform": "android",
  "sourceApiEra": "legacy-MarketingCloudSdk",   // human label for the OLD world
  "targetApiEra": "unified-SFMCSdk",             // human label for the NEW world
  "targetVersion": "11.0.1",                     // latest version this matrix targets
  "targetRelease": 260,                          // optional product release number
  "detection": { ... },                          // how to recognize the old SDK / its version
  "dependencies": { ... },                       // Gradle/Pod/SPM coordinate changes
  "manifest": { ... },                           // AndroidManifest / Info.plist changes
  "mappings": [ ... ]                            // the heart: old symbol → new symbol
}
```

## `detection`

Tells the scanner how to find the SDK and infer the version era.

```jsonc
"detection": {
  "packageRoots": ["com.salesforce.marketingcloud"],   // import prefixes that mean "SDK in use"
  "legacyArtifacts": ["marketingcloudsdk"],            // old Gradle artifact ids
  "modernArtifacts": ["sfmcsdk", "pushfeaturemodule"], // new artifact ids (already migrated)
  "versionFiles": ["gradle.properties", "gradle/libs.versions.toml", "build.gradle"],
  "versionRegexes": [                                   // patterns to extract a version string
    "marketingcloudsdk:([0-9]+\\.[0-9]+\\.[0-9]+)",
    "sfmcsdk:([0-9]+\\.[0-9]+\\.[0-9]+)"
  ]
}
```

## `dependencies`

What Phase 4 applies to build files. `remove` coordinates that are gone; `add` the modern set. Mark feature modules `conditional` so they're only added when the scan finds that feature actually used.

```jsonc
"dependencies": {
  "group": "com.salesforce.marketingcloud",
  "remove": [{ "artifact": "marketingcloudsdk", "note": "monolith replaced by sfmcsdk + feature modules" }],
  "add": [
    { "artifact": "sfmcsdk", "version": "11.0.1", "conditional": false },
    { "artifact": "pushfeaturemodule", "version": "11.0.1", "conditional": "push", "feature": "push" },
    { "artifact": "inappmessagingfeaturemodule", "version": "11.0.1", "conditional": "iam", "feature": "in-app-messaging" }
  ]
}
```

## `manifest`

```jsonc
"manifest": {
  "autoProvided": [        // merged in automatically by the new modules — REMOVE manual copies, don't add
    "com.salesforce.marketingcloud.sfmcsdk.SFMCSdkInitContentProvider",
    "com.salesforce.marketingcloud.pushfeature.push.PushMessagingService"
  ],
  "appMustOwn": [          // things the customer app still has to declare itself
    { "item": "POST_NOTIFICATIONS permission", "when": "push used && targetSdk>=33" }
  ],
  "removeLegacy": [        // legacy components that should be deleted
    "com.salesforce.marketingcloud.notifications.NotificationManager$..."
  ]
}
```

## `mappings` — the core

Each entry maps one OLD symbol to its NEW equivalent. Fields:

| Field | Required | Meaning |
|---|---|---|
| `id` | yes | Stable slug, e.g. `init-sdk`. Used in reports. |
| `area` | yes | One of `init`, `push`, `identity`, `events`, `iam`, `notifications`, `other`. Groups the report. |
| `old` | yes | The old symbol/pattern to detect — fully-qualified where possible. |
| `oldRegex` | no | Optional regex the scanner uses to find call sites (when a literal string isn't enough). |
| `new` | yes | The modern symbol/snippet to write. Use `null` if the API was removed (then `note` must explain the alternative). |
| `kind` | yes | `method`, `class`, `import`, `config`, or `gradle`. |
| `async` | no | `true` if the new API is only reachable inside `SFMCSdk.requestSdk { sdk -> ... }`. Forces callback-wrapping, not a rename. |
| `feature` | no | Tags the mapping to a feature (`push`, `iam`) so dependency/manifest steps can be conditional. |
| `before` / `after` | no | Short code snippets showing the rewrite. Strongly recommended for anything non-trivial. |
| `caveat` | no | What can go subtly wrong. Surfaced in the report when this mapping is applied. |
| `manualReview` | no | `true` means: detect it, but DON'T auto-rewrite — always flag for a human (e.g. custom subclasses). |

### Example entry

```jsonc
{
  "id": "registration-contact-key",
  "area": "identity",
  "old": "RegistrationManager.edit().setContactKey(...)",
  "oldRegex": "setContactKey\\s*\\(",
  "new": "SFMCSdk.requestSdk { it.identity.setProfileId(...) }",
  "kind": "method",
  "async": true,
  "before": "MarketingCloudSdk.getInstance().getRegistrationManager()\n    .edit().setContactKey(\"user@example.com\").commit()",
  "after": "SFMCSdk.requestSdk { sdk ->\n    sdk.identity.setProfileId(\"user@example.com\")\n}",
  "caveat": "Contact key is now 'profileId'. The set is async (inside requestSdk); any code that previously ran right after commit() and depended on it must move inside the callback."
}
```

## How to extend it

When the SDK releases a new version with breaking changes, append/adjust `mappings` entries and bump `targetVersion`. You never touch the skill's prose or scripts — the matrix is the knob. Keep `before`/`after` accurate against the real SDK; those snippets are what the skill pattern-matches against.

## iOS-specific fields

The iOS matrix (`migration-matrix-ios.json`) follows the same top-level shape but a few fields carry extra structure because iOS has three package managers and per-target build files.

### Artifact entries carry package-manager slots

Each entry in `dependencies.keep` / `dependencies.add` names the artifact three ways so Phase 3 can rewrite whichever manager the customer uses:

```jsonc
{
  "artifact": "SFMCSDK",              // logical name used in reports + detection
  "podName": "SFMCSDK",               // CocoaPods pod name (Podfile / Podfile.lock)
  "spmProduct": "SFMCSDK",            // SPM product name (.product(name: ...))
  "spmPackage": "SFMCSDK-iOS",        // SPM package repo slug (git host / owner / repo)
  "carthageName": "SFMCSDK",          // optional — Carthage binary spec, legacy projects only
  "seedVersion": "4.0.0",
  "conditional": false,
  "feature": null,
  "note": "..."
}
```

Which slots are present tells the resolver which backends can install this artifact. An artifact with only `podName` is CocoaPods-only.

### Per-target manifest entries

Unlike AndroidManifest.xml (one file per app), iOS has one Info.plist and one .entitlements per target — main app, Notification Service Extension, Share Extension, etc. Every entry under `manifest.autoProvided` / `appMustOwn` / `removeLegacy` may carry an optional `target` field:

```jsonc
{
  "item": "App Group entitlement",
  "target": "main-app | notification-service-extension",   // pipe-separated, or "any"
  "when": "push used && rich-media notifications used",
  "note": "Both targets must carry the same App Group entitlement..."
}
```

Phase 3 keys manifest changes off the target directory (finds the pbxproj target the file belongs to), not the file name alone.

### Mapping variants: `objcOnly` and `swiftOnly`

Real iOS apps mix Swift and Obj-C. A single `mappings` entry ships snippets for both languages via the `beforeObjc` / `afterObjc` fields alongside `before` / `after` (Swift). When a rewrite is language-specific — e.g. an Obj-C-only bridging shim — mark the entry:

```jsonc
{
  "id": "objc-only-selectors",
  "objcOnly": true,      // scanner fires this ONLY in .m / .h / .mm files
  ...
}
{
  "id": "swift-async-await-lift",
  "swiftOnly": true,     // scanner fires this ONLY in .swift files
  ...
}
```

The scanner honours the flag by consulting the file extension of the current match before recording the finding. Neither flag defaults to true; when both are absent the entry applies to all iOS source extensions.

### Shipped-artifact bugs carry a `verify` block

Known shipped-artifact defects (packaging bugs no app-code fix can address — the swiftinterface bug in `SFInAppMessagingFeatureSDK 1.0.0` is the seeded example) are documented in two coordinated places:

- `version-catalog-*.json`: each `version` entry may carry a `knownIssues` array. Each issue has `id`, `affects`, `symptom`, `cause`, `workaround`, and — critically — a `verify` block.
- `migration-matrix-*.json`: the affected artifact's entry (under `dependencies.keep` / `dependencies.add`) may carry a `shippedArtifactBug` block pointing at the same `id`, with a longer `fallback` narrative and its own `verify` block.

Every `verify` block MUST have the same shape:

```jsonc
"verify": {
  "script": "scripts/verify_known_issue.py",
  "cli": "python3 scripts/verify_known_issue.py --project <project> --issue-id <issue-id>",
  "requiresResolver": "cocoapods:pod install --repo-update  |  spm:xcodebuild -resolvePackageDependencies",
  "emitPolicy": "reproduces -> emit warning verbatim; patched -> suppress + note the observation; not-materialized -> run resolver + re-verify, else emit tagged 'unverified'; inconclusive -> emit tagged 'unverified'."
}
```

The verifier is a dispatcher keyed on `issueId`; each id maps to a Python function that inspects the actual shipped artifact on disk (unpacking the xcframework, reading the swiftinterface, whatever the defect requires) and returns one of four verdicts: `reproduces`, `patched`, `not-materialized`, `inconclusive`. Phase 5 runs the verifier AFTER the resolver step (`pod install` / `xcodebuild -resolvePackageDependencies`) and gates warning emission on the verdict. When adding a new known issue, add its verifier to `scripts/verify_known_issue.py`'s `VERIFIERS` registry — otherwise the workflow can't gate on it and the warning becomes noise.

### Version detection across FOUR pin sites

`detection.versionArtifactRegexes` on iOS has to handle four pin locations in one regex per artifact (the scanner treats each artifact regex as a single pattern that must find a version in any of them):

- `Podfile` — `pod 'MarketingCloudSDK', '~> 11.0.0'`
- `Podfile.lock` — `MarketingCloudSDK (11.0.0)`
- `Package.resolved` — `"identity": "marketingcloudsdk", ..., "version": "11.0.0"` (identity is lowercased)
- `project.pbxproj` — via an `XCRemoteSwiftPackageReference` block

Because Package.resolved lowercases identities and Podfile keeps CamelCase, compile these regexes with case-insensitivity at scan time.
