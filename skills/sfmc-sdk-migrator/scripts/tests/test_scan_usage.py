"""Regression tests for scripts/scan_usage.py.

Two bugs are guarded here:

1. Era misclassification. In v11 the engagement module is still published as
   `marketingcloudsdk` and still ships legacy-shaped symbols, so a correctly
   migrated project produces matrix findings. The old code inferred "legacy" the
   moment any finding existed, mislabeling a healthy v11 app as needing the full
   architecture migration. Era must key off the unified-core artifact (sfmcsdk),
   per detection.eraDisambiguation — NOT off the presence of findings.

2. Version-detection nondeterminism. The old code took the first version any
   file happened to match under os.walk order, and could pick sfmcsdk's separate
   3.x stream as the "current version" of a unified project — which would then
   read as major<10 and get misclassified as pre-boundary legacy downstream. The
   version must come from the umbrella artifact (marketingcloudsdk) and be
   resolved deterministically.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

import _bootstrap  # noqa: F401
import scan_usage

SCRIPT = os.path.join(_bootstrap.SCRIPTS_DIR, "scan_usage.py")


def _write(root, relpath, content):
    path = os.path.join(root, relpath)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def _scan(root, platform="android"):
    """Run scan_usage.py as a subprocess and return the parsed JSON report."""
    out = subprocess.run(
        [sys.executable, SCRIPT, root, "--platform", platform, "--json"],
        capture_output=True, text=True, check=True,
    )
    return json.loads(out.stdout)


class TestVersionResolutionHelpers(unittest.TestCase):
    def test_umbrella_version_preferred_over_core_stream(self):
        # Both artifacts pinned. currentVersion must be the umbrella (11.0.1),
        # never the core stream (3.1.1) that would look pre-boundary.
        by_artifact = {"marketingcloudsdk": {"11.0.1"}, "sfmcsdk": {"3.1.1"}}
        v, conflict = scan_usage.resolve_current_version(by_artifact, ["marketingcloudsdk"])
        self.assertEqual(v, "11.0.1")
        self.assertFalse(conflict)

    def test_absent_umbrella_yields_none_not_core_number(self):
        # Push-only unified project: no engagement module. Rather than borrow the
        # 3.x core number (which would misclassify), report undeterminable.
        by_artifact = {"sfmcsdk": {"3.1.1"}}
        v, conflict = scan_usage.resolve_current_version(by_artifact, ["marketingcloudsdk"])
        self.assertIsNone(v)
        self.assertFalse(conflict)

    def test_multiple_umbrella_pins_take_highest_and_flag(self):
        by_artifact = {"marketingcloudsdk": {"11.0.0", "11.0.1", "8.1.0"}}
        v, conflict = scan_usage.resolve_current_version(by_artifact, ["marketingcloudsdk"])
        self.assertEqual(v, "11.0.1")
        self.assertTrue(conflict)

    def test_collect_handles_groovy_and_kotlin_coordinate_forms(self):
        # The regex targets the Gradle dependency-coordinate string; check the
        # Groovy (implementation "g:a:v") and Kotlin (implementation("g:a:v"))
        # spellings both yield the same version regardless of quote style.
        rx = {"marketingcloudsdk": scan_usage.re.compile(
            r"marketingcloudsdk[:\"']\s*[:=]?\s*[\"']?([0-9][0-9A-Za-z.\-]*)")}
        groovy = scan_usage.collect_artifact_versions(
            'implementation "com.salesforce.marketingcloud:marketingcloudsdk:11.0.1"', rx)
        kotlin = scan_usage.collect_artifact_versions(
            "implementation('com.salesforce.marketingcloud:marketingcloudsdk:11.0.1')", rx)
        self.assertEqual(groovy["marketingcloudsdk"], {"11.0.1"})
        self.assertEqual(kotlin["marketingcloudsdk"], {"11.0.1"})

    def test_collect_unions_multiple_versions(self):
        # Determinism across files depends on collecting ALL matches (a union),
        # not first-match-wins. Two different pins in one blob must both surface.
        rx = {"marketingcloudsdk": scan_usage.re.compile(
            r"marketingcloudsdk[:\"']\s*[:=]?\s*[\"']?([0-9][0-9A-Za-z.\-]*)")}
        blob = ('"com.salesforce.marketingcloud:marketingcloudsdk:11.0.1"\n'
                '"com.salesforce.marketingcloud:marketingcloudsdk:8.1.0"\n')
        got = scan_usage.collect_artifact_versions(blob, rx)
        self.assertEqual(got["marketingcloudsdk"], {"11.0.1", "8.1.0"})


class TestEraClassification(unittest.TestCase):
    def _project(self, root, gradle, code_rel, code):
        _write(root, "app/build.gradle", gradle)
        _write(root, code_rel, code)

    def test_migrated_v11_with_findings_is_not_legacy(self):
        """The headline bug: findings present, but era must be unified."""
        with tempfile.TemporaryDirectory() as root:
            self._project(
                root,
                gradle=(
                    'dependencies {\n'
                    '  implementation "com.salesforce.marketingcloud:sfmcsdk:3.1.1"\n'
                    '  implementation "com.salesforce.marketingcloud:marketingcloudsdk:11.0.1"\n'
                    '}\n'
                ),
                code_rel="app/src/Main.kt",
                code=(
                    "import com.salesforce.marketingcloud.sfmcsdk.SFMCSdk\n"
                    "fun f() {\n"
                    "  MarketingCloudSdk.requestSdk { mc -> mc.inboxMessageManager.getMessages() }\n"
                    "  mc.analyticsManager.trackPageView(\"x\")\n"
                    "}\n"
                ),
            )
            r = _scan(root)
            d = r["detected"]
            self.assertGreater(len(r["findings"]), 0, "fixture should produce findings")
            self.assertEqual(d["apiEra"], "unified-SFMCSdk")
            self.assertEqual(d["migrationStatus"], "already-modern")
            self.assertTrue(d["sawUnifiedCore"])
            self.assertFalse(d["sawLegacyEntryPoint"])
            # Version came from the umbrella artifact, not the 3.x core stream.
            self.assertEqual(d["currentVersion"], "11.0.1")

    def test_pure_legacy_is_legacy(self):
        with tempfile.TemporaryDirectory() as root:
            self._project(
                root,
                gradle='dependencies { implementation "com.salesforce.marketingcloud:marketingcloudsdk:8.1.0" }\n',
                code_rel="app/src/Main.java",
                code=("import com.salesforce.marketingcloud.MarketingCloudSdk;\n"
                      "class M { void g() { MarketingCloudSdk.init(this, cfg, l); } }\n"),
            )
            r = _scan(root)
            d = r["detected"]
            self.assertEqual(d["apiEra"], "legacy-MarketingCloudSdk")
            self.assertEqual(d["migrationStatus"], "not-started")
            self.assertFalse(d["sawUnifiedCore"])
            self.assertTrue(d["sawLegacyEntryPoint"])
            self.assertEqual(d["currentVersion"], "8.1.0")

    def test_partial_migration_flagged(self):
        """Unified core present BUT legacy init still called => partial."""
        with tempfile.TemporaryDirectory() as root:
            self._project(
                root,
                gradle=(
                    'dependencies {\n'
                    '  implementation "com.salesforce.marketingcloud:sfmcsdk:3.1.1"\n'
                    '  implementation "com.salesforce.marketingcloud:marketingcloudsdk:11.0.1"\n'
                    '}\n'
                ),
                code_rel="app/src/Main.kt",
                code="fun f() { MarketingCloudSdk.init(ctx, cfg) { } }\n",
            )
            r = _scan(root)
            d = r["detected"]
            self.assertEqual(d["apiEra"], "unified-SFMCSdk")
            self.assertEqual(d["migrationStatus"], "partial-migration")
            self.assertTrue(d["sawLegacyEntryPoint"])

    def test_no_sdk_is_unknown(self):
        with tempfile.TemporaryDirectory() as root:
            _write(root, "app/src/Main.kt", "fun f() { println(\"hi\") }\n")
            r = _scan(root)
            d = r["detected"]
            self.assertEqual(d["apiEra"], "unknown")
            self.assertEqual(d["migrationStatus"], "no-sdk")
            self.assertIsNone(d["currentVersion"])

    def test_version_detection_is_deterministic_across_runs(self):
        with tempfile.TemporaryDirectory() as root:
            # Same version pinned in several files; result must be stable.
            self._project(
                root,
                gradle='implementation "com.salesforce.marketingcloud:marketingcloudsdk:11.0.1"\n',
                code_rel="app/src/Main.kt",
                code="// com.salesforce.marketingcloud usage\n",
            )
            _write(root, "libs.versions.toml",
                   'marketingcloudsdk = "11.0.1"\nsfmcsdk = "3.1.1"\n')
            first = _scan(root)["detected"]["currentVersion"]
            second = _scan(root)["detected"]["currentVersion"]
            self.assertEqual(first, "11.0.1")
            self.assertEqual(first, second)


class TestIosDetection(unittest.TestCase):
    """iOS parallels of the Android era-classification tests.

    Guards the iOS-specific bits that don't apply on Android:

    - Podfile.lock, Podfile, and Package.resolved all pin the umbrella version
      with different casing and syntax; the same regex must catch all three
      under re.IGNORECASE.
    - Package.resolved identity is derived from the git repo slug, so the
      MarketingCloudSDK entry can appear as `marketingcloudsdk-ios-sdk` — not
      just the bare pod name. Detection must not miss it.
    - Era is keyed off the SFMCSDK unified core in Podfile.lock, NOT off the
      MarketingCloudSDK engagement module (which is kept in v11+).
    - Case-insensitive matching must ALSO catch the CamelCase Podfile line, so
      one regex covers both forms without double bookkeeping.
    """

    def _project(self, root, files):
        for rel, content in files.items():
            _write(root, rel, content)

    def test_legacy_podfile_only(self):
        with tempfile.TemporaryDirectory() as root:
            self._project(root, {
                "Podfile": (
                    "platform :ios, '13.0'\n"
                    "target 'App' do\n"
                    "  pod 'MarketingCloudSDK', '~> 8.1.1'\n"
                    "end\n"
                ),
                "App/AppDelegate.swift": (
                    "import MarketingCloudSDK\n"
                    "class AppDelegate {\n"
                    "  func boot() {\n"
                    "    _ = MarketingCloudSDK.sharedInstance().sfmc_configure(with: [:])\n"
                    "  }\n"
                    "}\n"
                ),
            })
            r = _scan(root, platform="ios")
            d = r["detected"]
            self.assertEqual(d["apiEra"], "legacy-MarketingCloudSDK")
            self.assertEqual(d["migrationStatus"], "not-started")
            self.assertTrue(d["sawLegacyEntryPoint"])
            self.assertFalse(d["sawUnifiedCore"])
            self.assertEqual(d["currentVersion"], "8.1.1")

    def test_unified_podfile_is_already_modern(self):
        # v11 fully-migrated app: umbrella MarketingCloudSDK 11.0.0 +
        # feature modules (PushFeatureSDK) + real v11 API surface. NO
        # `SFMCSdk.mp` / `SFMCSdk.requestPushSdk` — those were removed in v11
        # (they were 9.x transitional). Engagement is reached via
        # `MarketingCloudSdk.requestSdk { mp in ... }`; push token via
        # `PushFeature.requestSdk { pf in ... }`. Presence of the unified
        # feature module pod + absence of legacy/transitional entry points ⇒
        # already-modern.
        with tempfile.TemporaryDirectory() as root:
            self._project(root, {
                "Podfile.lock": (
                    "PODS:\n"
                    "  - MarketingCloudSDK (11.0.0)\n"
                    "  - MarketingCloud-SFMCSdk (4.0.0)\n"
                    "  - SFPushFeatureSDK (2.0.0)\n"
                    "COCOAPODS: 1.15.2\n"
                ),
                "Podfile": (
                    "pod 'MarketingCloud-SFMCSdk', '~> 4.0.0'\n"
                    "pod 'MarketingCloudSDK', '~> 11.0.0'\n"
                    "pod 'SFPushFeatureSDK', '~> 2.0.0'\n"
                ),
                "App/AppDelegate.swift": (
                    "import SFMCSDK\n"
                    "import MarketingCloudSDK\n"
                    "import PushFeatureSDK\n"
                    "class AppDelegate {\n"
                    "  func boot() {\n"
                    "    SFMCSdk.initializeSdk(ConfigBuilder().build())\n"
                    "    PushFeature.requestSdk { pf in pf?.setDeviceToken(data) }\n"
                    "    MarketingCloudSdk.requestSdk { mp in mp?.startWatchingLocation() }\n"
                    "  }\n"
                    "}\n"
                ),
            })
            r = _scan(root, platform="ios")
            d = r["detected"]
            self.assertEqual(d["apiEra"], "unified-SFMCSDK")
            self.assertEqual(d["migrationStatus"], "already-modern")
            self.assertTrue(d["sawUnifiedCore"])
            self.assertFalse(d["sawLegacyEntryPoint"])
            self.assertFalse(d["sawTransitionalSymbol"])
            self.assertEqual(d["currentVersion"], "11.0.0")

    def test_spm_package_resolved_with_repo_slug_identity(self):
        # SPM derives Package.resolved's `identity` from the repo slug — so the
        # MarketingCloudSDK entry appears as `marketingcloudsdk-ios-sdk`. The
        # regex must accept the -ios-sdk suffix or version detection will
        # silently fall through to None (this exact bug regressed once).
        with tempfile.TemporaryDirectory() as root:
            self._project(root, {
                "Package.swift": (
                    'let package = Package(\n'
                    '  dependencies: [\n'
                    '    .package(url: "https://github.com/salesforce-marketingcloud/MarketingCloudSDK-iOS-SDK.git", exact: "8.1.1"),\n'
                    '  ])\n'
                ),
                "Package.resolved": json.dumps({
                    "pins": [
                        {
                            "identity": "marketingcloudsdk-ios-sdk",
                            "kind": "remoteSourceControl",
                            "location": "https://github.com/salesforce-marketingcloud/MarketingCloudSDK-iOS-SDK.git",
                            "state": {"revision": "abc", "version": "8.1.1"},
                        }
                    ]
                }),
                "App/AppDelegate.swift": (
                    "import MarketingCloudSDK\n"
                    "MarketingCloudSDK.sharedInstance().sfmc_configure(with: [:])\n"
                ),
            })
            r = _scan(root, platform="ios")
            d = r["detected"]
            self.assertEqual(d["currentVersion"], "8.1.1",
                             "the -ios-sdk suffix in Package.resolved identity must not defeat version detection")
            self.assertEqual(d["apiEra"], "legacy-MarketingCloudSDK")

    def test_case_insensitive_matches_podfile_camelcase_and_lock_lowercase(self):
        # Podfile keeps CamelCase 'MarketingCloudSDK'; Podfile.lock's PODS list
        # preserves the same casing but SPM lowercases identities. All three
        # must be found by the ONE case-insensitive regex.
        with tempfile.TemporaryDirectory() as root:
            self._project(root, {
                "Podfile": "pod 'MarketingCloudSDK', '~> 9.0.2'\n",
                "Podfile.lock": (
                    "PODS:\n"
                    "  - MarketingCloudSDK (9.0.2)\n"
                ),
                "App/AppDelegate.swift": (
                    "import MarketingCloudSDK\n"
                    "MarketingCloudSDK.sharedInstance().sfmc_configure(with: [:])\n"
                ),
            })
            r = _scan(root, platform="ios")
            d = r["detected"]
            # Union of matches: same version, single element.
            self.assertEqual(d["versionsByArtifact"].get("MarketingCloudSDK"), ["9.0.2"])
            self.assertEqual(d["currentVersion"], "9.0.2")

    def test_no_ios_sdk_is_unknown(self):
        with tempfile.TemporaryDirectory() as root:
            _write(root, "App/AppDelegate.swift", "import UIKit\nclass A {}\n")
            r = _scan(root, platform="ios")
            d = r["detected"]
            self.assertEqual(d["apiEra"], "unknown")
            self.assertEqual(d["migrationStatus"], "no-sdk")
            self.assertIsNone(d["currentVersion"])

    def test_legacy_transitional_9x_is_distinct_from_pure_legacy(self):
        # iOS has THREE eras, not two. The 9.x transitional era introduced
        # the SFMCSdk façade but kept the monolithic MarketingCloudSDK 9.x
        # underneath. It uses `SFMCSdk.requestPushSdk { mp in ... }` and
        # `SFMCSdkConfigBuilder()` — both REMOVED in v11. The scanner must
        # classify this as `legacy-transitional-SFMCSDK`, NOT unified,
        # because `SFMCSdk` symbols appear here without a v10+ major.
        with tempfile.TemporaryDirectory() as root:
            _write(root, "Podfile.lock",
                   "PODS:\n"
                   "  - MarketingCloudSDK (9.0.3)\n"
                   "  - MarketingCloud-SFMCSdk (2.0.1)\n"
                   "  - MarketingCloud-ExtensionSDK (1.0.2)\n"
                   "COCOAPODS: 1.15.2\n")
            _write(root, "Podfile",
                   "pod 'MarketingCloudSDK', '~> 9.0.3'\n"
                   "pod 'MarketingCloud-SFMCSdk', '~> 2.0.1'\n")
            _write(root, "App/AppDelegate.swift",
                   "import SFMCSdk\n"
                   "class AppDelegate {\n"
                   "  func boot(deviceToken: Data) {\n"
                   "    let pushConfig = PushConfigBuilder(appId: \"x\").build()\n"
                   "    let cfg = SFMCSdkConfigBuilder()\n"
                   "        .setPush(config: pushConfig, onCompletion: { _ in })\n"
                   "        .build()\n"
                   "    SFMCSdk.initializeSdk(cfg)\n"
                   "    SFMCSdk.requestPushSdk { mp in mp.setDeviceToken(deviceToken) }\n"
                   "  }\n"
                   "}\n")
            r = _scan(root, platform="ios")
            d = r["detected"]
            self.assertEqual(d["apiEra"], "legacy-transitional-SFMCSDK")
            self.assertEqual(d["migrationStatus"], "not-started")
            self.assertEqual(d["currentVersion"], "9.0.3")
            self.assertEqual(d["umbrellaMajor"], 9)
            self.assertTrue(d["sawTransitionalSymbol"],
                            "SFMCSdk.requestPushSdk / SFMCSdkConfigBuilder / PushConfigBuilder are 9.x-only")
            # No unified feature module → NOT unified.
            self.assertFalse(d["sawUnifiedCore"])

    def test_partial_migration_v11_pods_with_transitional_call_sites(self):
        # A common LearningApp-style state: main app bumped some pods but
        # kept 9.x-transitional API in code. The scanner should flag this as
        # unified-with-partial-migration so the finisher rewrites the call
        # sites — NOT already-modern (which would say nothing to do).
        with tempfile.TemporaryDirectory() as root:
            _write(root, "Podfile.lock",
                   "PODS:\n"
                   "  - MarketingCloudSDK (11.0.1)\n"
                   "  - MarketingCloud-SFMCSdk (4.0.1)\n"
                   "  - SFPushFeatureSDK (2.0.0)\n"
                   "COCOAPODS: 1.15.2\n")
            _write(root, "App/AppDelegate.swift",
                   "import SFMCSdk\n"
                   "func boot(token: Data) {\n"
                   "  // still on 9.x transitional API — should be rewritten\n"
                   "  SFMCSdk.requestPushSdk { mp in mp.setDeviceToken(token) }\n"
                   "}\n")
            r = _scan(root, platform="ios")
            d = r["detected"]
            self.assertEqual(d["apiEra"], "unified-SFMCSDK")
            self.assertEqual(d["migrationStatus"], "partial-migration",
                             "transitional call sites in v11 project ⇒ partial, not already-modern")
            self.assertEqual(d["currentVersion"], "11.0.1")
            self.assertTrue(d["sawTransitionalSymbol"])


if __name__ == "__main__":
    unittest.main()
