# Detailed migration workflow

Paths and commands in this reference are relative to the installed skill directory, not this reference file or the customer project. Read the sections relevant to the current platform and phase.

## The cardinal rule: never guess a mapping

Every rewrite you make must come from an explicit entry in a **migration matrix** — a data file that says "old symbol X → new symbol Y, with these caveats." You do not invent modern API shapes from memory, because getting an SDK call subtly wrong (a renamed parameter, a now-async call, a dropped method) produces code that compiles-but-misbehaves, which is worse than an honest "needs review" flag.

Seed matrices live in `references/migration-matrix-android.json` and `references/migration-matrix-ios.json`, both documented in `references/migration-matrix-format.md`. Read the format doc once so you understand the fields, then load the matrix that matches the detected platform (see the *Platform routing* section below). If the user has their own/newer matrix (a "Breaking Changes Log"), prefer theirs — ask for the path, or look for `*migration-matrix*.json` / `MIGRATION*.md` in their repo first.

If you hit an old API that has **no matrix entry**, do not rewrite it. Leave it untouched and record it under "Needs manual review" with the file:line and what you saw. A surfaced gap is a feature, not a failure.

**When the matrix isn't enough, the authoritative source is the shipped bytecode, not the docs.** Docs and change logs describe intended API surface but lag or omit details: nested type positions, whether a getter is synthesized as a Kotlin property, whether a Builder constructor is `internal`, exact package moves, added listener-callback parameters. Every "compiles-but-wrong" trap this skill has hit came from trusting docs over the artifact — `sdk.mp {}` invented from a docs draft, `PushFeatureConfig.Builder()` hitting an internal constructor, `pushFeature.pushMessageManager` reading an unsynthesized property, `setProfileId(...)` on the wrong receiver, `didCloseMessage` with the wrong arity. **When in doubt, unpack the AAR and read the class:**

```bash
# The AARs live in the Gradle cache after any build. Unpack once per session:
mkdir -p /tmp/sfmc-inspect/<mod> && \
  (cd /tmp/sfmc-inspect/<mod> && \
   unzip -o ~/.gradle/caches/modules-2/files-2.1/com.salesforce.marketingcloud/<mod>/<ver>/*/*.aar >/dev/null && \
   unzip -o classes.jar -d classes >/dev/null)

# Then inspect the class you care about:
(cd /tmp/sfmc-inspect/<mod>/classes && javap -p <fully.qualified.ClassName>)
```

Do this for `sfmcsdk`, `marketingcloudsdk`, `pushfeaturemodule`, `inappmessagingfeaturemodule`, `pushmodelsmodule` (transitive) whenever a mapping isn't obvious. The `-p` flag on `javap` shows package-private + private members so you can see whether a constructor is `internal`. `javap -v` shows Kotlin metadata annotations so you can see property/method mappings. If a symbol you're about to emit isn't in the bytecode, don't emit it — flag it, add a matrix entry, or search for the correct symbol.

**iOS equivalent — the shipped framework, not the docs.** The same rule applies on iOS but the artifact is a `.xcframework` (or `.framework` inside CocoaPods' `Pods/` directory). Use `nm -gU <BinaryName>` to list exported Obj-C symbols and `swift-symbolgraph-extract` (or `swift-symbolgraph`) against the module to see the Swift API surface. For Obj-C headers the source of truth is the framework's `Headers/*.h`. Every "compiles-but-wrong" iOS trap on record — a missing `if let` around `CustomEvent(name:attributes:)` (a failable initializer that returns `nil` on validation reject), the one-argument `didClose(message:)` IAM delegate override that silently never fires because the real signature grew a `closeAction:` parameter, an Obj-C selector emitted without the `NS_SWIFT_NAME` on the actual method — came from trusting docs over headers. When in doubt, read the framework's headers and Swift interface.

The change log — https://developer.salesforce.com/docs/marketing/mobile-unified-sdk/guide/change-log.html — remains a useful secondary source for the *what changed* narrative on both platforms. Read it for the storyline, verify against the AAR (Android) or `.xcframework` (iOS) for the shape.

## Platform routing

Both Android and iOS are supported. Decide the platform *from the files on disk*, not the user's phrasing — a request that mentions "iOS" but points at an Android-only repo should still resolve to Android, and vice versa. Look for these signals at the repo root (or in the customer-supplied subdirectory):

- **Android**: `AndroidManifest.xml`, `build.gradle` / `build.gradle.kts`, `settings.gradle`, `gradle/libs.versions.toml`, `app/src/main/kotlin` or `app/src/main/java`.
- **iOS**: `Podfile` / `Podfile.lock`, `Package.swift` / `Package.resolved`, `*.xcodeproj/project.pbxproj`, `*.xcworkspace`, `Info.plist`, `*.entitlements`, `*.swift` / `*.m` / `*.h`.
- **Both** (rare, monorepos): treat as two projects — scan each half separately, produce one report with two sections.

Pass the resolved platform to every script — `scan_usage.py`, `target_options.py`, and `resolve_versions.py` all take `--platform android` or `--platform ios` (and, for `resolve_versions.py`, a `--backend {maven,cocoapods,spm}` matching the iOS package manager). The matrices, catalogs, and reference docs are platform-scoped:

| Platform | Matrix | Refactor patterns | Version catalog | Scanner backend |
|---|---|---|---|---|
| Android | `references/migration-matrix-android.json` | `references/refactoring-patterns-android.md` | `references/version-catalog-android.json` | Maven (`--backend maven`) |
| iOS | `references/migration-matrix-ios.json` | `references/refactoring-patterns-ios.md` | `references/version-catalog-ios.json` | CocoaPods trunk (`--backend cocoapods`) or SPM git-tags (`--backend spm`) |

**iOS-specific traps to know before you rewrite anything:**

- **`MarketingCloudSDK` is kept.** Just like on Android, in v10+/v11 the pod named `MarketingCloudSDK` is still shipped — as the engagement module reached via `SFMCSdk.mp` (push/inbox/tag/region). Do NOT delete it from the Podfile. `SFMCSDK` is the *unified core* that gets added.
- **The Notification Service Extension is a separate build target** with its own `Info.plist` / entitlements. In v10+ it uses `MCExtensionSDK`, not the main-app SDK. It also needs an App Group entitlement shared with the main app so rich-push analytics can flow back. Always flag NSE migration for manual review — a wrong rewrite silently drops push-open reporting.
- **`CustomEvent(name:attributes:)` is a failable initializer.** Any rewrite must `if let` — a force-unwrap crashes on invalid names/keys (blank, leading `$`, newlines, dots in attribute keys), which v11 rejects where legacy was permissive.
- **`didClose(message:closeAction:)` on the IAM delegate.** The single-argument override silently never fires — the real signature grew a `closeAction:` parameter. Rewriting an IAM delegate without updating the arity is a compile-clean regression.
- **SPM `branch:` pins are a red flag.** A `branch: "main"` or `branch: "develop"` pin means the customer is chasing HEAD; converting them to `exact:` or `.upToNextMajor(from:)` is part of the migration. Never introduce a `branch:` pin yourself.
- **Case-insensitive identity matching.** Podfile keeps CamelCase (`MarketingCloudSDK`); `Package.resolved` lowercases the identity and derives it from the git repo slug (so it may appear as `marketingcloudsdk-ios-sdk`). The scanner handles both — do not "correct" what looks like a mismatch.
- **Xcode silently drops uncompilable `.m` files from the Sources phase.** A `.m` file whose `#import` cannot resolve (e.g. a removed legacy v9 header like `SFMCNotificationConstants.h` or `SFMCDateNumberFormatters.h`) will NOT appear in the compile schedule — no CompileC line in the build log — and the failure surfaces later as `Undefined symbols for architecture arm64: _OBJC_CLASS_$_<ClassInThatFile>` referenced by whichever *other* .m uses that class. This looks IDENTICAL to a target-membership problem, which is a red herring. Before editing pbxproj to add the file, grep its `#import`s and confirm each header resolves — a missing header is the more likely fix (remove the import + inline what was used; matrix entries `removed-private-header-notifications` and `removed-private-header-date-formatters` document the pattern).
- **Multi-target pbxproj: edit the target the failing scheme actually builds.** Xcode projects with dev/prod/archive variants have one PBXSourcesBuildPhase *per target*. Adding a .m to `SDKExplorer_Dev`'s Sources phase does NOTHING for a build of `SDKExplorer`. Follow the chain: the scheme's build entry → the PBXNativeTarget's `buildPhases` → the `PBXSourcesBuildPhase` id → its `files = ( ... )` list. Confirm the phase id in the target you're touching before adding a new `PBXBuildFile` entry — accidentally patching the wrong target's Sources phase gives the exact same linker error before and after the "fix", which reads as if the pbxproj edit didn't take.

**Android-specific traps** (unchanged): see the "cardinal rule" section above and the async-wrapping notes in *Phase 4*.

## Workflow

Work through these phases in order. Don't skip the scan — acting before you understand the blast radius is how business logic gets broken.

**Scale the fan-out to the work.** A handful of call sites in two files: just edit inline. When delegation is permitted, a large app with call sites across many modules: Phase 4 is embarrassingly parallel — fan it out to background subagents behind a liveness-gated observer so no unit can stall silently or go unreported. That pattern (ledger protocol, `observe_workers.py` gate, restart/demote rules) lives in `references/parallel-refactor.md`; read it before dispatching workers.

### Phase 1 — Confirm the SDK is integrated, then scan & detect

**Before anything else, verify the app actually depends on an SFMC SDK module — start with the build files at the `project` path supplied under SKILL.md, Required context.** This matters regardless of how the request is phrased ("upgrade the MarketingCloud SDK", "bump SFMC Sdk to latest", "update our MAM SDK", "upgrade MCE") because the SDK ships as several differently-named artifacts, and a user may *believe* it's integrated when it isn't (or it's only in one flavor/module). Acting on that assumption is how you end up "upgrading" a dependency that was never there.

On **Android**, look in `build.gradle` / `build.gradle.kts` / `gradle/libs.versions.toml` (and `settings.gradle`) for any artifact in the `com.salesforce.marketingcloud` group. The relevant module names map to how people talk about them:

- **`marketingcloudsdk`** — the legacy monolith on ≤ 9.x, the engagement feature module on v10+ (people call this "the MarketingCloud SDK" / "MCE SDK", since Marketing Cloud Engagement was its product name).
- **`sfmcsdk`** — the unified core ("SFMC SDK").
- **`mobileappmessagingsdk`** — Mobile App Messaging ("MAM SDK").
- **`pushfeaturemodule`, `inappmessagingfeaturemodule`** — unified feature modules.

On **iOS**, look at the Podfile / `Podfile.lock` / `Package.swift` / `Package.resolved` / `*.xcodeproj/project.pbxproj` for these pod names / SPM products:

- **`MarketingCloudSDK`** — the legacy monolith on ≤ 9.x, the engagement module on v10+ (still shipped; still `SFMCSdk.mp`).
- **`SFMCSDK`** — the unified core (pod name capitalized; `Package.resolved` identity is lowercased and derived from the repo slug, so it may appear as `sfmcsdk` or `sfmcsdk-ios-sdk`).
- **`MCExtensionSDK`** — the Notification Service Extension helper (separate build target).
- **`InAppMessaging`** — the v11+ in-app messaging feature module.

The scanner does this detection for both platforms — pass `--platform` and the `project` path from SKILL.md, Required context:

```bash
# Android
python3 scripts/scan_usage.py <project> --platform android
# iOS
python3 scripts/scan_usage.py <project> --platform ios
```

It prints a JSON report: the detected current version + API era (legacy vs unified), `sawLegacyArtifact` / `sawModernArtifact` / `sawUnifiedCore` flags, every file touching the SDK, which old symbols appear, and a per-symbol count. Read `scripts/scan_usage.py`'s header comment for flags (`--platform`, `--json`, `--matrix`). Use this as your worklist — it's faster and more complete than grepping by hand, and it won't miss a call site in a file you didn't think to open.

Use this scan to establish `from` as described in SKILL.md. If you're re-entering Phase 1 for any reason and see a fresh mismatch between the scanner's `detected.currentVersion` and the current `from`, stop and re-confirm rather than silently preferring either side — a mismatch usually means wrong project path, a monorepo subdirectory, or a stale local checkout.

**Branch on what the build files say (same three-way rule for both platforms):**

- **No SFMC SDK dependency anywhere** → the SDK isn't integrated. Don't invent a migration. Tell the user plainly ("I don't see any SFMC SDK module in your build files at `<project>`") and ask whether they meant a different module, a different project path, or a fresh integration (which is out of scope — this skill upgrades existing integrations, it doesn't add new ones).
- **Already on a unified `sfmcsdk` / `SFMCSDK` setup** → there may be nothing to migrate, or only a version bump. Confirm before rewriting (see the already-modern handling — don't churn working code).
- **Legacy `marketingcloudsdk` / `MarketingCloudSDK` only (or a mix)** → this is the real migration case; continue to Phase 2.

If the scanner finds nothing but the user insists the SDK is present, fall back to searching for the package roots (`com.salesforce.marketingcloud` on Android; `import MarketingCloudSDK` / `import SFMCSdk` / `import MCExtensionSDK` on iOS) and the artifact ids in the platform's `migration-matrix-*.json`, and reconcile — the dependency may be declared in a non-standard place (a `buildSrc` constant, a platform BOM, a transitive wrapper module; on iOS a Podfile in a nested target directory, or a version-file loaded by Package.swift).

### Phase 2 — Resolve the target version (from SKILL.md, Required context, don't ask again)

Use the `to` parameter resolved under SKILL.md, Required context. Don't recompute a menu or ask them to choose; just resolve `to` against the catalog and confirm it's a valid forward step from `from`. `target_options.py` still does the resolution (partial expansion, downgrade guard, migration-kind tagging) — the only difference is you feed it `from` and `to` from SKILL.md, Required context verbatim, no interactive prompting:

```bash
python3 scripts/target_options.py --current <from> --target <to> --platform <android|ios>
```

Feed `--target` exactly what the user typed in `to` (`v10`, `10`, `10.x`, `10.1`, or a full `10.0.0`) and let the script apply one consistent rule instead of eyeballing it:

- **Partial spec** (bare major or major.minor) → *"newest release in that line"*: `v10` becomes the highest catalogued `10.x.y`, `10.1` the highest `10.1.z`. This is what "upgrade to v10" almost always means — current-and-greatest within 10, not literally `10.0.0`.
- **Exact spec** (all three components) → hard pin, returned untouched even if a newer patch exists.

The script reports a partial expansion in `targetResolutionNote` (e.g. *"Interpreted target 'v10' as the 10.x line → newest available is 10.0.0"*) — surface it verbatim so the jump is never silent, and use the `resolvedTarget` it returns for every downstream phase. A partial that matches nothing exits `3` with `{"error": "unresolvable target"}`: relay it and stop, don't guess. The catalog is only a seed — the actual published minor/patch is pinned at runtime in Phase 3 via `resolve_versions.py`.

The script also tags the resolved target with its `migrationKind`, which decides the shape of the rest of the run:

- **`version-config-bump`** — target stays within the customer's current architecture era. No API rewrites; just dependency/config changes plus any per-version breaking notes. Do Phase 3, skip Phase 4, then validate and report in Phase 5.
- **`full-code-migration`** — target crosses the **architecture boundary** (legacy `MarketingCloudSdk` / `MarketingCloudSDK` ≤ 9.x → unified `SFMCSdk` / `SFMCSDK` ≥ 10.x on both platforms). This is the call-site rewrite the rest of this skill performs.

The matrix targets the unified era; if the resolved target is a *within-legacy* bump (e.g. `from=8.1.0 to=9.0.5`), that's `version-config-bump` — do the dependency/config update in Phase 3 and skip the call-site rewrite entirely; say so plainly rather than pretending the call-site pass is a no-op.

This skill only moves a project *forward*. `to` **lower** than `from` exits non-zero with `{"error": "cant downgrade the sdk"}` — stop, report it verbatim ("Can't downgrade — you supplied `from=<from>`, newer than `to=<to>`"), and touch nothing; a backwards "upgrade" is almost always a typo, and stepping the SDK back would break their app. `to` *equal* to `from` means there's nothing to do — say so and stop. Proceed to Phase 3+ only when the resolved target is strictly newer than `from`.

Once the target is resolved, state the gap in one line, e.g. "You're on legacy 8.x `MarketingCloudSdk`; you've chosen unified SFMCSdk 11.0.1 — this crosses the architecture boundary, so initialization, push access, identity, and event tracking all get rewritten." Then load the matrix sections for the symbols the scan actually found (don't load mappings you won't use).

> **Targeting a version other than the matrix's `targetVersion`?** The seed matrix's symbol mappings describe the legacy→unified shift and are valid for any unified target (10.x/11.x), but the exact dependency *version string* and any version-specific API tweaks (e.g. the 11.0.0 In-App Messaging access change) differ. Use the chosen version's number for the Gradle coordinates, and consult the per-version `notes` in the version catalog (and the linked migration guide) for deltas the matrix doesn't yet encode. When in doubt, flag rather than guess.

### Phase 3 — Dependency & config updates

Do this **before** rewriting call sites. The reason is mechanical: once the new artifacts are on the classpath, the modern `SFMCSdk` symbols resolve and every un-migrated legacy call site turns into a compile error — which hands you an exact, tool-verified worklist for Phase 4. Refactor-first has the opposite problem: your rewritten code references classes that aren't on the classpath yet, so nothing compiles mid-migration and you can't tell a real mistake from a not-yet-added dependency.

**The single biggest way this migration goes wrong:** removing `marketingcloudsdk` / `MarketingCloudSDK` on the intuition that it's legacy. In v10+/v11 it is **not** removed — it becomes the *engagement feature module* and still ships `MarketingCloudSdk`/`MarketingCloudSDK`, `RegistrationManager`, `InboxMessageManager`, `AnalyticsManager`, `RegionMessageManager`, `sdkState` (or the equivalent Obj-C selectors on iOS reached via `SFMCSdk.mp`). Delete it and you get 50+ unresolved-reference errors with no unified replacement. Keep it in the Podfile / Gradle dependencies (the matrix `dependencies.keep` block reflects this on both platforms); most engagement call sites then need only async-callback wrapping or a `SFMCSdk.mp` prefix, no rewrite.

The v11 umbrella "11.x" maps to **multiple independent module versions** on both platforms (e.g. `sfmcsdk`/`SFMCSDK`, `pushfeaturemodule`, and `MCExtensionSDK` are on their own streams — `sfmcsdk:11.0.1` doesn't exist on Maven, and `SFMCSDK 11.0.0` doesn't exist on CocoaPods trunk). You cannot derive them from the umbrella number, and the matrix's `seedVersion` values are a dated snapshot that goes stale on every SFMC point release. So **resolve the real versions at runtime instead of trusting the matrix**:

```bash
# Android — verify or discover via the SFMC Maven repo.
python3 scripts/resolve_versions.py --project <project> --backend maven \
  --verify sfmcsdk=3.1.1,marketingcloudsdk=11.0.1,pushfeaturemodule=2.0.1
python3 scripts/resolve_versions.py --project <project> --backend maven --latest \
  --artifacts sfmcsdk,marketingcloudsdk,pushfeaturemodule,inappmessagingfeaturemodule

# iOS via CocoaPods trunk.
python3 scripts/resolve_versions.py --project <project> --backend cocoapods --latest \
  --artifacts MarketingCloudSDK,SFMCSDK,MCExtensionSDK

# iOS via SPM (git tags on the package's remote).
python3 scripts/resolve_versions.py --project <project> --backend spm --latest
```

It scrapes the SFMC Maven repo URL / Podfile pod names / Package.swift SPM URLs out of the app's own build files and reads each artifact's release list (`maven-metadata.xml` for Maven, `/api/v1/pods/<name>` for CocoaPods trunk, `git ls-remote --tags` for SPM). Read its header for flags. Two honest limits: (1) Version-list checks prove a version *exists* / is *newest*, not that a set of module versions were *released together as a coherent bundle* — that final check is the Phase 5 build/resolve. (2) If `networkReachable` is `false` (offline/firewalled), fall back to the matrix `seedVersion`s **and state that plainly in the report** — never silently pretend you verified.

**Android** (once versions are resolved):

- **Gradle**: keep `marketingcloudsdk`, add `sfmcsdk` + the feature modules the scan found in use, using the **resolved** versions (matrix seed only as offline fallback). Update version refs in `build.gradle(.kts)`, `gradle/libs.versions.toml`, and any `ext`/`buildSrc` version constants.
- **Toolchain bumps** are often forced by v11: `compileSdk 34+/36`, `minSdk 26`, `targetSdk 33+/36`, Java 17, Kotlin 2.x, AGP 8.x, Gradle 8.x. Check the customer's `build.gradle` before assuming their toolchain can hold the newer SDK; if a hard constraint (e.g. `minSdk 21`) blocks the bump, surface it and offer a within-legacy target instead.
- **AndroidManifest.xml**: the modern modules auto-merge their own services/receivers/permissions via manifest merging, so usually you *remove* manually-declared legacy SDK components rather than add new ones. The matrix's `manifest` section lists what's auto-provided (don't duplicate it) and any entry the app must still own (e.g. a custom `FirebaseMessagingService`). **`POST_NOTIFICATIONS` for Android 13+** if push is used — v11 almost always trips this via the `targetSdk` bump; flag it if not already handled.
- Leave the customer's `google-services.json` / Firebase setup alone unless a mapping explicitly requires a change.

**iOS** (once versions are resolved):

- **Podfile / Package.swift**: keep `MarketingCloudSDK` (engagement module in v10+), add `SFMCSDK` (unified core). Add `MCExtensionSDK` if a Notification Service Extension is present, and `InAppMessaging` if the scan found IAM in use. On SPM, use `exact:` or `.upToNextMajor(from:)` — never a `branch:` pin. Run `pod install --repo-update` (CocoaPods) or `xcodebuild -resolvePackageDependencies` (SPM) as the coherence check hint the matrix supplies.
- **Toolchain bumps** forced by v11: `IPHONEOS_DEPLOYMENT_TARGET 12.0+` (v11 drops iOS 11 support), Swift 5.7+, Xcode 14+ (12.5+ minimum via 8.0.5). If the app targets iOS 11 or older, surface it and offer a within-legacy target instead.
- **Info.plist / entitlements**: main app needs `aps-environment` + `remote-notification` in `UIBackgroundModes`; the Notification Service Extension needs its own bundle-id and, for rich-push analytics, an **App Group entitlement shared with the main app**. The matrix's `manifest` entries carry a `target` field (`main-app` / `notification-service-extension`) so you can tell where each entry belongs. ATS (App Transport Security) may need an exception if the customer's `marketingCloudServerUrl` uses HTTP.
- **Notification Service Extension**: always flag for manual review. The NSE moves off `MarketingCloudSDK` (main-app pod) onto `MCExtensionSDK` (a separate pod scoped to the NSE target only). A wrong rewrite silently drops push-open reporting.
- Leave the customer's provisioning profiles / signing config / non-SFMC pods alone unless a mapping explicitly requires a change.

### Phase 4 — Refactor call sites

With the dependencies in place, rewrite each detected call site using its matrix entry. If the toolchain is available, a compile now points you straight at the un-migrated legacy references. If delegation is permitted and the worklist is large, fan this phase out to background subagents behind an observer gate — see `references/parallel-refactor.md`. Principles that keep you from breaking their app:

- **Preserve business logic, change only the SDK surface.** Their notification-channel logic, their analytics event names, their conditional flows are theirs. You're swapping the API verbs, not rethinking the app. If a value was passed to the old call (a contact key, an event name, attributes), thread that same value into the new call.
- **Honor semantic shifts the matrix flags.** The biggest one on Android: old code often reads SDK state synchronously (`MarketingCloudSdk.getInstance().getRegistrationManager()...`), but the modern API hands you the SDK through an async callback (`SFMCSdk.requestSdk { sdk -> ... }`). When a mapping is marked async, you must wrap the dependent code in the callback — not just rename the symbol — or it won't compile. On iOS the shift is comparable but shallower: `MarketingCloudSDK.sharedInstance().sfmc_...` becomes direct calls on `SFMCSdk` / `SFMCSdk.mp` / `SFMCSdk.identity` — synchronous, but with a completion handler on the initial `SFMCSdk.initializeSdk` for readiness. The matrix marks these; `references/refactoring-patterns-<platform>.md` shows the before/after shapes.
- **Init config must cover every feature in use, not just push.** On Android, `SFMCSdk.configure(...)` takes an additive `SFMCSdkModuleConfig.build {}`. On iOS, `SFMCSdkConfigBuilder().setPush(config:onCompletion:)` (and, in v11+, `.setInAppMessagingConfig(...)`) is the equivalent chain. Wire in a module config for **each** feature the scan reported (`featuresInUse`) — if `iam` is present, the in-app module config goes in the *same* config builder as push, or in-app messaging silently never initializes despite its artifact being on the classpath. The set of module configs must match the feature modules you added in Phase 3. See the init section of the platform's refactoring patterns doc.
- **Audit dynamically-built event names and attribute keys.** v11 validates them at track time and *silently* drops invalid input (WARN only) where legacy was permissive — so a name/key built by concatenation, templates, reflection, or `enum.toString()` / Swift interpolation can't be statically proven clean; flag it for manual review rather than assume telemetry survives. On Android, the `?.let { SFMCSdk.track(it) }` guard is load-bearing because `EventManager.customEvent` returns `null` on rejection. On iOS, `CustomEvent(name:attributes:)` is a **failable initializer** returning `nil` — the `if let event = CustomEvent(...) else { … }` guard is equally load-bearing. Never force-unwrap. Same rules: blank, leading `$`, newlines, and (attribute keys only) dots are rejected.
- **iOS-only: NSE and IAM delegates.** Always flag the Notification Service Extension for manual review — the wrong rewrite drops push-open reporting silently. When migrating an IAM delegate, verify the arity — `didClose(message:closeAction:)` has two parameters in v11+; a one-arg override compiles but never fires.
- **One symbol at a time, smallest correct edit.** Don't reformat surrounding code. Match the file's existing style (indentation, Kotlin vs Java on Android; Swift vs Obj-C on iOS; import grouping).
- **When unsure, flag — don't fudge.** Ambiguous overloads, custom subclasses of SDK types, reflection on SDK classes (or KVC / Obj-C runtime tricks on iOS), or anything the matrix doesn't cover → leave as-is, add to the review list.

`references/refactoring-patterns-android.md` and `references/refactoring-patterns-ios.md` have the canonical before/after for each major area (init, push/token, identity/contact key, event tracking, in-app messaging; on iOS also NSE migration and Obj-C bridging edge cases). Read the platform's doc before rewriting — it'll save you from re-deriving the async-wrapping shape per file.

### Phase 5 — Validate & report

**Gate first.** If Phase 4 was fanned out, do not begin this phase until `scripts/observe_workers.py` exits `0` (every planned unit terminal) — see `references/parallel-refactor.md`. A non-zero exit means a unit is stalled, missing, or unaccounted; resolve it (restart, or demote to manual review) before validating. Reporting on a migration whose workers never reported back is exactly the silent-gap failure this skill exists to prevent.

Try to compile if the toolchain is available and capture the result honestly — if it fails, show the errors; don't claim success you didn't verify. A migration that doesn't compile isn't done. **This build is also the authoritative confirmation that the resolved module versions cohere** — the version-list check in Phase 3 told you each version exists, but only a successful build proves the chosen set works together. A resolution error here (not a code error) means a version needs re-resolving, not a call-site fix.

- **Android**: `./gradlew assembleDebug` (or `compileDebugKotlin` for a focused module).
- **iOS**: `pod install --repo-update` (CocoaPods) or `xcodebuild -resolvePackageDependencies` (SPM) first to prove version coherence, then `xcodebuild -workspace <app>.xcworkspace -scheme <scheme> -sdk iphonesimulator build` for the compile check. There's no single-command Gradle-resolve equivalent, so run both the dependency resolver AND the build — the matrix's `coherenceCheckHint` field records which command to use for the pod/SPM resolver.

**Reproduce shipped-artifact bugs against what's on disk before warning about them.** The iOS matrix and version catalog carry a list of shipped-artifact defects (e.g. `iam-1.0.0-swiftinterface-nodoc`) with a `verify` block pointing at `scripts/verify_known_issue.py`. Every known issue whose `affects` version matches a module in the resolved dependency set gets one verifier run after the resolver step above — never before, since the artifact must be on disk. Interpret the verdict as the `emitPolicy` in the `verify` block prescribes:

- **`reproduces`** — emit the warning's `workaround` / `fallback` text verbatim in *Needs manual review*.
- **`patched`** — SUPPRESS the warning; add a one-line observation under *Needs manual review* (`"Known issue <id> did not reproduce against the shipped <module> on disk — Salesforce appears to have silently republished since the skill's seed date"`) so a future regression is visible.
- **`not-materialized`** — the resolver step failed to produce the module. Fix the resolver first (that's a separate class of problem), then re-verify. If the resolver ran cleanly but the module isn't in the graph, the pod/product isn't being used and the warning does not apply.
- **`inconclusive`** — emit the warning tagged *"unverified — could not read the shipped interface"* and record the reason.

Never emit a shipped-artifact warning without running its verifier — the seed data is a snapshot, not a live check, and unconditional emission produces false positives on healthy builds.

Then produce the report (template: `assets/report-template.md`). Always include:

```
# SFMC SDK Migration Report
## Summary          — from version → to version, files changed, call sites rewritten
## Changes by area  — init / push / identity / events / IAM / gradle / manifest, with file:line
## Needs manual review — every flagged item, why, and a suggested next step
## Verification      — build result (real output), then steps for the dev: run app, send a test push, confirm a tracked event lands
```

Be specific and honest in "Needs manual review" — it's the part a senior dev will actually read. Vague reports erode trust; "left `CustomPushReceiver` (extends legacy `MCPushReceiver`) untouched at `App.kt:42` — no matrix entry for custom receiver subclasses, confirm intended behavior" is what earns it.

