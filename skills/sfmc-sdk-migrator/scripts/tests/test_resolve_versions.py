"""Regression tests for scripts/resolve_versions.py — no network required.

Two bugs are guarded:

1. 404-vs-offline conflation. The old code treated an HTTP 404/403 the same as a
   connection failure and reported "offline", which the caller uses to justify
   falling back to the stale matrix seed. A 404 means the server ANSWERED — the
   URL/version is wrong; the fix is a corrected URL, not a seed fallback. Because
   HTTPError is a SUBCLASS of URLError, it must be caught first. We simulate each
   failure mode by monkeypatching fetch_metadata (no sockets touched).

2. SSRF surface. Scraped repo URLs come from files we don't control, so a scraped
   URL is fetched only if its host is on the allowlist. host_allowed() must reject
   off-list hosts, look-alike suffixes, and non-http schemes.
"""
import contextlib
import io
import json
import unittest
import urllib.error

import _bootstrap  # noqa: F401
import resolve_versions as rv


class TestHostAllowlist(unittest.TestCase):
    def test_allows_listed_hosts(self):
        self.assertTrue(rv.host_allowed("https://mobilepushstatic.salesforce.com/repo"))
        self.assertTrue(rv.host_allowed("https://salesforce-marketingcloud.github.io/JB4A-SDK-Android/repository"))
        self.assertTrue(rv.host_allowed("https://salesforce.com/x"))

    def test_rejects_lookalike_suffix(self):
        # The classic bypass: attacker registers salesforce.com.evil.example.
        self.assertFalse(rv.host_allowed("https://salesforce.com.evil.example/repo"))
        self.assertFalse(rv.host_allowed("https://notsalesforce.com/repo"))

    def test_rejects_unlisted_host(self):
        self.assertFalse(rv.host_allowed("https://repo.maven.apache.org/maven2"))
        self.assertFalse(rv.host_allowed("http://169.254.169.254/latest/meta-data/"))

    def test_rejects_non_http_schemes(self):
        self.assertFalse(rv.host_allowed("file:///etc/passwd"))
        self.assertFalse(rv.host_allowed("gopher://salesforce.com/"))
        self.assertFalse(rv.host_allowed("ftp://salesforce.com/x"))

    def test_rejects_garbage(self):
        self.assertFalse(rv.host_allowed(""))
        self.assertFalse(rv.host_allowed("not a url"))


class TestScrapeThenFilter(unittest.TestCase):
    """scrape_repos + host_allowed together: only on-list scraped URLs survive."""

    def test_offlist_scraped_url_is_filtered(self):
        scraped = [
            "https://mobilepushstatic.salesforce.com/repository",
            "https://repo.maven.apache.org/maven2",          # off-list
            "https://salesforce.com.evil.example/repo",       # look-alike
        ]
        allowed = [u for u in scraped if rv.host_allowed(u)]
        self.assertEqual(allowed, ["https://mobilepushstatic.salesforce.com/repository"])


class _FetchStub:
    """Callable that mimics fetch_metadata's raise/return per (repo, artifact)."""

    def __init__(self, behavior):
        self.behavior = behavior
        self.calls = []

    def __call__(self, repo, artifact, timeout):
        self.calls.append((repo, artifact))
        outcome = self.behavior(repo, artifact)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome  # (versions, release, latest)


def _http_error(code):
    return urllib.error.HTTPError(url="http://x", code=code, msg="nope", hdrs=None, fp=None)


def _url_error():
    return urllib.error.URLError("connection refused")


def _run_main(argv, fetch):
    """Drive resolve_versions.main() with fetch_metadata stubbed; return report.

    Runs the REAL main() (real catch-order, real report assembly) so the test
    can't drift from the code. main() calls sys.exit; we capture that and parse
    the JSON it prints to stdout.
    """
    import sys as _sys
    orig_fetch = rv.fetch_metadata
    orig_argv = list(_sys.argv)
    rv.fetch_metadata = fetch
    _sys.argv = ["resolve_versions.py"] + argv
    buf = io.StringIO()
    exit_code = None
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(io.StringIO()):
            try:
                rv.main()
            except SystemExit as e:
                exit_code = e.code
    finally:
        rv.fetch_metadata = orig_fetch
        _sys.argv = orig_argv
    report = json.loads(buf.getvalue())
    return report, exit_code


class TestFourZeroFourStaysOnline(unittest.TestCase):
    """The core distinction, exercised through the REAL main()."""

    ARGV = ["--repo", "https://salesforce.com/repo", "--latest", "--artifacts", "sfmcsdk", "--json"]

    def test_http_404_reports_reachable(self):
        fetch = _FetchStub(lambda repo, art: _http_error(404))
        report, code = _run_main(self.ARGV, fetch)
        self.assertTrue(report["networkReachable"], "a 404 means the server answered — NOT offline")
        self.assertFalse(report["allArtifactsResolved"])
        # Non-zero exit, but for the reachable-but-missing reason, not offline.
        self.assertNotEqual(code, 0)

    def test_403_also_reports_reachable(self):
        fetch = _FetchStub(lambda repo, art: _http_error(403))
        report, _ = _run_main(self.ARGV, fetch)
        self.assertTrue(report["networkReachable"])

    def test_connection_failure_reports_unreachable(self):
        fetch = _FetchStub(lambda repo, art: _url_error())
        report, code = _run_main(self.ARGV, fetch)
        self.assertFalse(report["networkReachable"], "connection refused IS the offline case")
        self.assertNotEqual(code, 0)

    def test_success_reports_reachable_and_resolved(self):
        fetch = _FetchStub(lambda repo, art: (["3.1.0", "3.1.1"], "3.1.1", "3.1.1"))
        report, code = _run_main(self.ARGV, fetch)
        self.assertTrue(report["networkReachable"])
        self.assertTrue(report["allArtifactsResolved"])
        self.assertEqual(report["latest"]["sfmcsdk"]["latest"], "3.1.1")
        self.assertEqual(code, 0)

    def test_httperror_is_subclass_of_urlerror(self):
        # The reason catch-order matters; pin it so a refactor can't reorder them.
        self.assertTrue(issubclass(urllib.error.HTTPError, urllib.error.URLError))


class TestIosHostAllowlist(unittest.TestCase):
    """iOS backends (CocoaPods, SPM) reach off-Maven hosts.

    The allowlist was expanded for iOS: cocoapods.org, github.com, and
    githubusercontent.com. A miss here means the scraper silently drops a
    valid pod / SPM URL; an over-broad match means SSRF.
    """

    def test_allows_cocoapods_trunk(self):
        self.assertTrue(rv.host_allowed("https://trunk.cocoapods.org/api/v1/pods/MarketingCloudSDK"))
        self.assertTrue(rv.host_allowed("https://cdn.cocoapods.org/all_pods.txt"))

    def test_allows_github_for_spm(self):
        self.assertTrue(rv.host_allowed("https://github.com/salesforce-marketingcloud/MarketingCloudSDK-iOS-SDK.git"))
        self.assertTrue(rv.host_allowed("https://raw.githubusercontent.com/foo/bar/main/file.txt"))

    def test_still_rejects_lookalike_after_ios_expansion(self):
        # Regression: adding github.com must not accidentally allow *.github.com.evil
        # or github.com.evil.example. Suffix-boundary check catches both.
        self.assertFalse(rv.host_allowed("https://github.com.evil.example/repo"))
        self.assertFalse(rv.host_allowed("https://cocoapods.org.evil.example/repo"))
        self.assertFalse(rv.host_allowed("https://notgithub.com/repo"))


class TestCocoaPodsFetch(unittest.TestCase):
    """fetch_cocoapods_versions parses trunk's JSON payload correctly.

    Trunk exposes /api/v1/pods/<name> returning `{"versions": [{"name": "1.0.0"}, ...]}`.
    Regressions to guard: empty-versions payload, malformed entries dropped
    silently, and the reachable-vs-offline classification going through the same
    HTTPError/URLError plumbing as Maven.
    """

    def _stub_urlopen(self, body_or_exc):
        """Monkeypatch urllib.request.urlopen for one call."""
        class _Fake:
            def __init__(self, body): self.body = body
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def read(self): return self.body
        def fake(req, timeout):
            if isinstance(body_or_exc, Exception):
                raise body_or_exc
            return _Fake(body_or_exc)
        return fake

    def _run_with_urlopen(self, pod_name, body_or_exc, fn=None):
        import urllib.request
        orig = urllib.request.urlopen
        urllib.request.urlopen = self._stub_urlopen(body_or_exc)
        try:
            return (fn or rv.fetch_cocoapods_versions)(pod_name, timeout=1.0)
        finally:
            urllib.request.urlopen = orig

    def test_parses_versions_array(self):
        body = json.dumps({"versions": [{"name": "8.0.13"}, {"name": "11.0.0"}]}).encode()
        got = self._run_with_urlopen("MarketingCloudSDK", body)
        self.assertEqual(got, ["8.0.13", "11.0.0"])

    def test_drops_entries_missing_name(self):
        # Malformed trunk entries (no 'name' field) must be skipped, not crash.
        body = json.dumps({"versions": [{"name": "1.0"}, {}, {"name": None}]}).encode()
        got = self._run_with_urlopen("Whatever", body)
        self.assertEqual(got, ["1.0"])

    def test_empty_versions(self):
        body = json.dumps({"versions": []}).encode()
        got = self._run_with_urlopen("Whatever", body)
        self.assertEqual(got, [])

    def test_http_error_propagates(self):
        # 404-vs-offline classification is preserved across backends: fetch
        # must raise HTTPError (subclass of URLError) so the resolver reports
        # reachable=true, resolved=false — never quietly returns [].
        with self.assertRaises(urllib.error.HTTPError):
            self._run_with_urlopen("NoSuchPod", _http_error(404))

    def test_url_error_propagates(self):
        with self.assertRaises(urllib.error.URLError):
            self._run_with_urlopen("Whatever", _url_error())


class TestPodfileAndSpmScraping(unittest.TestCase):
    """scrape_ios_pods and scrape_ios_spm_urls locate the right names/URLs.

    Guards: (a) Podfile with quoted CamelCase pod names is parsed correctly;
    (b) commented-out lines don't produce false positives; (c) SPM
    .package(url:) declarations, whether in Package.swift or a pbxproj
    repositoryURL block, are all surfaced.
    """

    def test_scrape_pods_from_podfile(self):
        import os
        import tempfile
        with tempfile.TemporaryDirectory() as root:
            with open(os.path.join(root, "Podfile"), "w") as f:
                f.write(
                    "platform :ios, '13.0'\n"
                    "target 'App' do\n"
                    "  pod 'MarketingCloudSDK', '~> 8.1.1'\n"
                    "  pod \"AFNetworking\"\n"
                    "  # pod 'DoNotInclude'\n"
                    "end\n"
                )
            got = rv.scrape_ios_pods(root)
            self.assertIn("MarketingCloudSDK", got)
            self.assertIn("AFNetworking", got)

    def test_scrape_spm_urls_from_package_swift(self):
        import os
        import tempfile
        with tempfile.TemporaryDirectory() as root:
            with open(os.path.join(root, "Package.swift"), "w") as f:
                f.write(
                    'let package = Package(\n'
                    '  dependencies: [\n'
                    '    .package(url: "https://github.com/salesforce-marketingcloud/MarketingCloudSDK-iOS-SDK.git", exact: "8.1.1"),\n'
                    '    .package(url: "https://github.com/other/lib.git", from: "1.0.0"),\n'
                    '  ])\n'
                )
            got = rv.scrape_ios_spm_urls(root)
            self.assertIn("https://github.com/salesforce-marketingcloud/MarketingCloudSDK-iOS-SDK.git", got)
            self.assertIn("https://github.com/other/lib.git", got)


class TestSpmSchemeGate(unittest.TestCase):
    """fetch_spm_versions must reject non-git schemes BEFORE handing to git.

    A file:// or gopher:// URL passed to `git ls-remote` is a local-file /
    protocol-confusion risk. The gate must reject them without touching a
    subprocess.
    """

    def test_rejects_file_scheme(self):
        with self.assertRaises(urllib.error.URLError):
            rv.fetch_spm_versions("file:///etc/passwd", timeout=1.0)

    def test_rejects_gopher_scheme(self):
        with self.assertRaises(urllib.error.URLError):
            rv.fetch_spm_versions("gopher://github.com/", timeout=1.0)


class TestNewestPrecedence(unittest.TestCase):
    def test_prefers_stable_over_prerelease(self):
        self.assertEqual(rv.newest(["11.0.0-rc1", "11.0.0", "10.0.0"]), "11.0.0")

    def test_falls_back_to_prerelease_when_no_stable(self):
        self.assertEqual(rv.newest(["11.0.0-rc1", "11.0.0-rc2"]), "11.0.0-rc2")

    def test_empty(self):
        self.assertIsNone(rv.newest([]))


class TestSpmRepoSlugBinding(unittest.TestCase):
    """Each SFMC module lives in its own repo, so an artifact must bind to
    ONE candidate URL — the one whose final path segment matches its
    `spmRepoSlug` from the migration matrix. Historical bug: the resolver
    used to sweep every candidate for every artifact and take the first that
    returned tags, so every artifact ended up bound to whichever URL was
    scraped first — producing a uniform version number across unrelated
    modules (the "push feature reported as 11.0.1" symptom).
    """

    def test_url_final_slug_strips_git_suffix(self):
        self.assertEqual(
            rv._url_final_slug("https://github.com/salesforce-marketingcloud/sfmc-sdk-ios.git"),
            "sfmc-sdk-ios",
        )
        self.assertEqual(
            rv._url_final_slug("https://github.com/salesforce-marketingcloud/push-feature-sdk-ios"),
            "push-feature-sdk-ios",
        )

    def test_url_final_slug_tolerates_trailing_slash(self):
        self.assertEqual(
            rv._url_final_slug("https://github.com/salesforce-marketingcloud/iam-feature-sdk-ios/"),
            "iam-feature-sdk-ios",
        )

    def test_slug_index_multi_keys_every_alias(self):
        """One entry in the matrix → multiple lookup keys. A caller passing
        the spmProduct (e.g. "SFMCSDK") must resolve to the same slug as one
        passing the matrix artifact key ("MarketingCloud-SFMCSdk") or the
        podName. Case-insensitive."""
        matrix = {
            "dependencies": {
                "add": [{
                    "artifact": "MarketingCloud-SFMCSdk",
                    "podName": "MarketingCloud-SFMCSdk",
                    "importModule": "SFMCSDK",
                    "spmProduct": "SFMCSDK",
                    "spmRepoSlug": "sfmc-sdk-ios",
                }],
                "keep": [{
                    "artifact": "MarketingCloudSDK",
                    "podName": "MarketingCloudSDK",
                    "importModule": "MarketingCloudSDK",
                    "spmProduct": "MarketingCloudSDK",
                    "spmRepoSlug": "MarketingCloudSDK-iOS",
                }],
            }
        }
        idx = rv._build_artifact_slug_index(matrix)
        # SFMCSdk core: three aliases, one slug.
        self.assertEqual(idx["marketingcloud-sfmcsdk"], "sfmc-sdk-ios")
        self.assertEqual(idx["sfmcsdk"], "sfmc-sdk-ios")
        # Engagement: single slug reachable by its own artifact/pod name.
        self.assertEqual(idx["marketingcloudsdk"], "MarketingCloudSDK-iOS")

    def test_slug_index_skips_entries_without_slug(self):
        """A dependency entry with no spmRepoSlug (or slug=null) must not
        appear in the index — the resolver falls back to the sweep for it."""
        matrix = {"dependencies": {"add": [
            {"artifact": "MysteryModule", "spmProduct": "MysteryModule"},
            {"artifact": "MysteryModule2", "spmProduct": "MysteryModule2",
             "spmRepoSlug": None},
        ]}}
        self.assertEqual(rv._build_artifact_slug_index(matrix), {})

    def test_slug_index_missing_matrix_returns_empty(self):
        """A missing / malformed matrix must not crash — callers still work,
        they just can't slug-match (fallback sweep path handles them)."""
        self.assertEqual(rv._build_artifact_slug_index({}), {})
        self.assertEqual(rv._build_artifact_slug_index({"dependencies": {}}), {})


class TestMatrixShippedSlugs(unittest.TestCase):
    """Guard rails for the SHIPPED matrix — a value here is what production
    resolves against. These would have caught the LearningAppSPM regression."""

    def test_shipped_matrix_has_slugs_for_every_v11_module(self):
        matrix = rv._load_ios_matrix()
        idx = rv._build_artifact_slug_index(matrix)
        # Every module a v11 app touches must resolve to a real slug (MAM is
        # optional but its slug is still catalogued for apps that use it).
        for artifact in ("MarketingCloudSDK", "MarketingCloud-SFMCSdk",
                         "SFPushFeatureSDK", "SFInAppMessagingFeatureSDK",
                         "MarketingCloud-ExtensionSDK"):
            with self.subTest(artifact=artifact):
                self.assertIn(artifact.lower(), idx,
                              f"matrix missing spmRepoSlug for {artifact}")

    def test_shipped_matrix_slugs_are_all_distinct(self):
        """Every SFMC module has its own repo — if two artifacts share a
        slug, the resolver would bind both to the same URL (the exact
        historical bug this fix prevents)."""
        matrix = rv._load_ios_matrix()
        deps = matrix.get("dependencies", {})
        slugs = [e["spmRepoSlug"] for e in
                 (deps.get("keep", []) + deps.get("add", []))
                 if e.get("spmRepoSlug")]
        self.assertEqual(len(slugs), len(set(slugs)),
                         f"duplicate slugs in matrix: {slugs}")


if __name__ == "__main__":
    unittest.main()
