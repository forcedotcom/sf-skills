#!/usr/bin/env python3
"""
resolve_versions.py — Resolve the ACTUAL published versions of the SFMC SDK
feature modules at runtime, instead of trusting the versions hardcoded in the
migration matrix.

Why this exists: the unified SDK ships as several artifacts on INDEPENDENT
version streams (sfmcsdk, marketingcloudsdk, pushfeaturemodule,
inappmessagingfeaturemodule, ...). The umbrella "v11.0.1" release maps to a set
of module versions (e.g. sfmcsdk 3.1.1) that you cannot derive arithmetically
and that change on every point release. A version string pinned in
migration-matrix-android.json is a snapshot that rots — and a stale version
produces a Gradle resolution failure at build time. So the matrix versions are
a *fallback seed*, and this script checks reality against the Maven repo.

What it CAN determine from Maven metadata:
  • which versions of each artifact actually exist (catches a rotted pin),
  • the newest released version of each artifact (for "get me current").

What it CANNOT determine (and doesn't pretend to): which module versions were
released *together* as one coherent bundle. No public metadata encodes that.
The authoritative coherence check is letting Gradle resolve the set — this
skill does that in Phase 5 (the compile). Treat this script's output as
"these versions exist / are newest", and let the build confirm they cohere.

--------------------------------------------------------------------------------
FINDING THE REPO

SFMC artifacts are not on Maven Central; they're served from a Salesforce Maven
repo the app declares itself. Rather than guess, this script scrapes
`maven { url "..." }` / `maven(url = "...")` declarations out of the project's
Gradle files (settings.gradle[.kts], build.gradle[.kts]) and tries each that
looks like an SFMC/Salesforce repo. Pass --repo to override, or --project to
point at the app root to scrape. A known default is tried last.

--------------------------------------------------------------------------------
USAGE

  # Verify the matrix's pinned versions still exist (rot check):
  python3 resolve_versions.py --project /path/to/app \
      --verify sfmcsdk=3.1.1,marketingcloudsdk=11.0.1,pushfeaturemodule=2.0.1

  # Discover the newest released version of each module:
  python3 resolve_versions.py --project /path/to/app --latest \
      --artifacts sfmcsdk,marketingcloudsdk,pushfeaturemodule,inappmessagingfeaturemodule

  # Explicit repo, JSON only:
  python3 resolve_versions.py --repo https://.../repository --latest --artifacts sfmcsdk --json

Network: uses only the Python stdlib (urllib). It distinguishes two failure
modes that earlier versions wrongly collapsed into one:
  • UNREACHABLE (offline / firewalled / DNS / connection refused / timeout) —
    no HTTP response at all. Reports networkReachable=false. THIS is the only
    case that justifies falling back to the matrix seed, and the caller must say
    so in the report.
  • REACHABLE-BUT-MISSING (HTTP 404/403, or a version simply not on the repo) —
    the server answered, so the network is fine; the URL or the pinned version
    is wrong. Reports networkReachable=true with the artifact unresolved. The fix
    is a corrected URL/version, NOT a seed fallback — pretending "offline" here
    would hide a real rotted pin behind a stale seed.
HTTPError is a subclass of URLError, so it is caught first; otherwise a clean
404 would be misread as offline.

Security: scraped repo URLs (from the customer's Gradle files) are fetched only
if their host is on an SFMC allowlist (see ALLOWED_REPO_HOST_SUFFIXES); off-list
URLs are recorded in reposRejected and never fetched. Explicit --repo values
bypass this and are the escape hatch for a legitimately non-standard host.

Exit codes: 0 = reachable AND every requested artifact resolved (and, in
--verify mode, every pinned version exists). Non-zero = offline, a version is
missing, or an artifact wasn't found — the report/stderr say which, because the
remedy differs.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

import semver  # shared, precedence-correct version math (scripts/semver.py)

GROUP = "com.salesforce.marketingcloud"
GROUP_PATH = GROUP.replace(".", "/")

# Tried LAST, only if the project declares no scrapable SFMC repo. Kept as a
# fallback, NOT a hardcoded truth — the project's own declaration wins.
DEFAULT_REPO_FALLBACK = "https://salesforce-marketingcloud.github.io/MarketingCloudSDK-Android/repository"

# iOS backends. Endpoints exist on public infrastructure; SFMC pods and SPM
# packages are all downstream of these.
COCOAPODS_TRUNK_BASE = "https://trunk.cocoapods.org/api/v1/pods/"
# CocoaPods no longer resolves through a git repo — trunk is the JSON authority.
# SFMC's SPM packages live on github.com/salesforce-marketingcloud/. The scraper
# falls back to whichever host the customer's Package.swift declares (subject to
# the allowlist below); non-standard hosts can be unblocked with an explicit
# --repo override.

# SSRF guard. We scrape URLs out of the CUSTOMER's build files (Gradle, Podfile,
# Package.swift) and then fetch them. An attacker (or an honest mistake) who
# lands a URL in a build file could point this script at an internal metadata
# endpoint, a cloud credential service, etc. So a scraped URL is only fetched if
# its host is on this allowlist. The list is host SUFFIXES: a URL's host must
# equal an entry or end with "." + entry, which prevents
# "salesforce.com.evil.example" from matching "salesforce.com". Anything scraped
# and rejected is recorded in `reposRejected` so the caller can see we skipped
# it rather than silently trusting it. Explicit --repo overrides bypass scraping
# and are the escape hatch for a legitimately non-standard host.
ALLOWED_REPO_HOST_SUFFIXES = (
    # Android / Maven
    "salesforce.com",
    "salesforce-marketingcloud.github.io",
    "marketingcloud.com",
    "exacttarget.com",
    # iOS: CocoaPods trunk (JSON metadata) + CDN (all-versions text files).
    "cocoapods.org",
    # iOS: SPM package host. github.com covers the public
    # salesforce-marketingcloud org, which is where the SFMC iOS
    # unified/legacy repositories are published.
    "github.com",
    "githubusercontent.com",
)
# Only these schemes are ever fetched — a scraped file:// or gopher:// URL is a
# classic SSRF/local-file vector and has no business here.
ALLOWED_REPO_SCHEMES = ("https", "http")

# SPM repos are also passed to `git ls-remote`. Restrict git subprocess targets
# to git+ssh / https URLs on the allowlist. Non-allowlisted repos are never
# handed to git — the customer must pass --repo to unblock.
GIT_SCHEMES = ("https", "http", "ssh", "git")


def host_allowed(url):
    """True if `url` is an http(s) URL whose host is on the allowlist."""
    try:
        parts = urllib.parse.urlparse(url)
    except ValueError:
        return False
    if parts.scheme.lower() not in ALLOWED_REPO_SCHEMES:
        return False
    host = (parts.hostname or "").lower()
    if not host:
        return False
    return any(host == s or host.endswith("." + s) for s in ALLOWED_REPO_HOST_SUFFIXES)

GRADLE_FILES = (
    "settings.gradle", "settings.gradle.kts",
    "build.gradle", "build.gradle.kts",
)

# Covers the common Gradle repo-declaration forms:
#   url "x" | url = "x" | url("x") | url = uri("x") | url(uri("x")) | setUrl("x")
# The optional `uri(` wrapper is the Kotlin-DSL idiom and must be skipped to
# reach the quote. `url` may be followed by `=`, `(`, and/or `uri(` in any of
# these combos, then whitespace, then the quoted URL.
REPO_URL_RE = re.compile(
    r"""(?:url|setUrl)\s*[=(]?\s*(?:uri\s*\()?\s*["']([^"']+)["']""",
    re.IGNORECASE,
)
# maven("x") / maven(uri("x")) — the URL as the direct maven(...) argument.
BARE_MAVEN_RE = re.compile(
    r"""maven\s*\(\s*(?:uri\s*\()?\s*["']([^"']+)["']""",
    re.IGNORECASE,
)


def scrape_repos(project_root):
    """Pull candidate Maven repo URLs out of the project's Gradle files."""
    found = []
    for dirpath, dirnames, filenames in os.walk(project_root):
        # don't descend into build output / vcs
        dirnames[:] = [d for d in dirnames if d not in {".git", "build", ".gradle", ".idea"}]
        for name in filenames:
            if name not in GRADLE_FILES:
                continue
            try:
                with open(os.path.join(dirpath, name), "r", encoding="utf-8", errors="replace") as f:
                    text = f.read()
            except OSError:
                continue
            for rx in (REPO_URL_RE, BARE_MAVEN_RE):
                for m in rx.finditer(text):
                    url = m.group(1).strip()
                    if url.startswith("http") and url not in found:
                        found.append(url)
    # Prefer repos that look like Salesforce/marketing-cloud ones.
    def score(u):
        lu = u.lower()
        return (("salesforce" in lu or "marketingcloud" in lu or "marketing-cloud" in lu), )
    found.sort(key=score, reverse=True)
    return found


def fetch_metadata(repo, artifact, timeout):
    """Fetch and parse maven-metadata.xml for one artifact from one repo.
    Returns (versions:list, release:str|None, latest:str|None) or raises."""
    base = repo.rstrip("/")
    url = f"{base}/{GROUP_PATH}/{artifact}/maven-metadata.xml"
    req = urllib.request.Request(url, headers={"User-Agent": "sfmc-sdk-migrator/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
    root = ET.fromstring(raw)
    versioning = root.find("versioning")
    versions, release, latest = [], None, None
    if versioning is not None:
        vs = versioning.find("versions")
        if vs is not None:
            versions = [e.text.strip() for e in vs.findall("version") if e.text]
        rel = versioning.find("release")
        lat = versioning.find("latest")
        release = rel.text.strip() if rel is not None and rel.text else None
        latest = lat.text.strip() if lat is not None and lat.text else None
    return versions, release, latest


def newest(versions):
    """Newest STABLE version; fall back to any if only pre-releases exist.

    `is_prerelease()` from the shared util treats ANY qualifier (-beta/-rc/
    -alpha/-SNAPSHOT/...) as a pre-release, so we don't need a per-keyword regex
    that would silently miss a new qualifier SFMC introduces. Precedence — and
    therefore "which is newest" — comes from semver.key so 11.0.0 correctly
    outranks 11.0.0-rc1 instead of tying with it.
    """
    parsed = [semver.parse(v) for v in versions]
    stable = [v for v in parsed if not v.is_prerelease()]
    pool = stable or parsed
    return max(pool, key=semver.key).raw if pool else None


def parse_verify(spec):
    """'sfmcsdk=3.1.1,pushfeaturemodule=2.0.1' -> {artifact: version}."""
    out = {}
    for chunk in spec.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "=" not in chunk:
            sys.exit(f"error: --verify entry '{chunk}' must be artifact=version")
        art, ver = chunk.split("=", 1)
        out[art.strip()] = ver.strip()
    return out


# --- iOS: CocoaPods resolver ---

def fetch_cocoapods_versions(pod_name, timeout):
    """Return the list of published versions for `pod_name` from CocoaPods trunk.

    Trunk's `/api/v1/pods/<name>` endpoint returns JSON containing a `versions`
    array (each entry has `name` = the version string). Raises the same
    HTTPError / URLError types as Maven fetching so the reachable-vs-offline
    distinction downstream is uniform across backends.
    """
    url = f"{COCOAPODS_TRUNK_BASE}{urllib.parse.quote(pod_name, safe='')}"
    req = urllib.request.Request(url, headers={
        "User-Agent": "sfmc-sdk-migrator/1.0",
        "Accept": "application/json",
    })
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
    data = json.loads(raw)
    versions = [v.get("name") for v in data.get("versions", []) if v.get("name")]
    return versions


# --- iOS: SPM resolver ---

# Podfile line:   pod 'MarketingCloudSDK', '~> 8.1.1'  or  pod "MarketingCloudSDK"
PODFILE_POD_RE = re.compile(
    r"""pod\s+["']([A-Za-z0-9_./-]+)["']""",
    re.IGNORECASE,
)
# Podfile source line: source 'https://cdn.cocoapods.org'
PODFILE_SOURCE_RE = re.compile(
    r"""source\s+["']([^"']+)["']""",
    re.IGNORECASE,
)
# Package.swift line: .package(url: "https://...", ...)  (Kotlin-style spread etc all irrelevant)
SPM_PACKAGE_URL_RE = re.compile(
    r"""\.package\s*\(\s*(?:name\s*:\s*["'][^"']*["']\s*,\s*)?url\s*:\s*["']([^"']+)["']""",
    re.IGNORECASE,
)
# pbxproj remote-package block:  repositoryURL = "https://..."
PBXPROJ_REMOTE_URL_RE = re.compile(
    r"""repositoryURL\s*=\s*["']([^"']+)["']""",
)


def scrape_ios_pods(project_root):
    """Return the sorted list of unique pod names declared in every Podfile."""
    pods = []
    for dirpath, dirnames, filenames in os.walk(project_root):
        dirnames[:] = [d for d in dirnames if d not in {".git", "Pods", "DerivedData",
                                                        ".swiftpm", "build", "xcuserdata"}]
        for name in filenames:
            if name != "Podfile":
                continue
            try:
                with open(os.path.join(dirpath, name), "r", encoding="utf-8", errors="replace") as f:
                    text = f.read()
            except OSError:
                continue
            for m in PODFILE_POD_RE.finditer(text):
                pod = m.group(1)
                if pod not in pods:
                    pods.append(pod)
    return pods


def scrape_ios_spm_urls(project_root):
    """Return the sorted list of unique SPM package repository URLs declared."""
    urls = []
    for dirpath, dirnames, filenames in os.walk(project_root):
        dirnames[:] = [d for d in dirnames if d not in {".git", "Pods", "DerivedData",
                                                        ".swiftpm", "build", "xcuserdata"}]
        for name in filenames:
            path = os.path.join(dirpath, name)
            try:
                text = None
                if name == "Package.swift":
                    with open(path, "r", encoding="utf-8", errors="replace") as f:
                        text = f.read()
                    for m in SPM_PACKAGE_URL_RE.finditer(text):
                        u = m.group(1).strip()
                        if u and u not in urls:
                            urls.append(u)
                elif name.endswith(".pbxproj"):
                    with open(path, "r", encoding="utf-8", errors="replace") as f:
                        text = f.read()
                    for m in PBXPROJ_REMOTE_URL_RE.finditer(text):
                        u = m.group(1).strip()
                        if u and u not in urls:
                            urls.append(u)
            except OSError:
                continue
    return urls


def _git_ls_remote_tags(repo_url, timeout):
    """Return the list of tag names on `repo_url` via `git ls-remote --tags`.

    Uses the local `git` binary if available. Raises RuntimeError on any
    unexpected failure so the caller can distinguish "no tags found" (empty
    list) from "couldn't reach the repo" (RuntimeError → offline).
    """
    try:
        proc = subprocess.run(
            ["git", "ls-remote", "--tags", "--refs", repo_url],
            capture_output=True, text=True, timeout=timeout,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(f"git binary not available: {exc}") from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"git ls-remote timed out: {exc}") from exc
    if proc.returncode != 0:
        stderr = proc.stderr.strip()
        raise RuntimeError(f"git ls-remote exit {proc.returncode}: {stderr}")
    tags = []
    for line in proc.stdout.splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        ref = parts[1]
        if not ref.startswith("refs/tags/"):
            continue
        # Strip refs/tags/ prefix; drop the ^{} peeled-tag suffix if present.
        tag = ref[len("refs/tags/"):].removesuffix("^{}")
        # SPM tag names are usually plain version strings; strip a leading 'v'
        # so `newest()` sees canonical SemVer form.
        clean = tag.lstrip("vV")
        if clean and clean not in tags:
            tags.append(clean)
    return tags


def fetch_spm_versions(repo_url, timeout):
    """Return the list of SPM-published versions (git tags) for a repo URL.

    SPM has no metadata server: version discovery IS `git ls-remote --tags`.
    Distinguishes reachable-but-empty (returns []) from unreachable (raises
    URLError so the caller can classify offline).
    """
    try:
        parts = urllib.parse.urlparse(repo_url)
    except ValueError as exc:
        raise urllib.error.URLError(f"invalid URL {repo_url}: {exc}") from exc
    if parts.scheme.lower() not in GIT_SCHEMES:
        raise urllib.error.URLError(f"disallowed git scheme in {repo_url}")
    try:
        return _git_ls_remote_tags(repo_url, timeout)
    except RuntimeError as exc:
        # Map the git-level failure onto the same URLError shape the Maven path
        # uses so `network_reachable` classification stays uniform.
        raise urllib.error.URLError(str(exc)) from exc


# --- iOS: matrix-driven artifact→SPM-repo-slug binding ---
#
# Historical bug: the SPM path swept every scraped repo URL against every
# artifact and picked the first that returned tags. Since every SFMC repo
# returns tags for *itself*, every artifact ended up bound to whichever URL was
# scraped first (uniform version bug — pushfeaturemodule reported as 11.0.1
# because MarketingCloudSDK-iOS was first in the list). Fix: each SFMC module
# lives in its OWN GitHub repo, so binding is by-slug. The matrix carries the
# authoritative slug in `spmRepoSlug`; here we build both an artifact→slug
# index (multi-keyed by every alias we know) and a URL matcher that says
# "this URL's final path segment matches this artifact's slug".
MATRIX_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "references", "migration-matrix-ios.json",
)


def _load_ios_matrix():
    """Load references/migration-matrix-ios.json. Missing/malformed → {}.

    Callers still work without the matrix (they just can't slug-match); a
    missing file must not crash the resolver.
    """
    try:
        with open(MATRIX_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def _build_artifact_slug_index(matrix):
    """Return {alias_lower: slug} for every SFMC iOS module in the matrix.

    Callers pass artifact names in whichever style they know — matrix
    `artifact` (e.g. `MarketingCloud-SFMCSdk`), `spmProduct` (`SFMCSDK`),
    `importModule` (`SFMCSDK`), or `podName` (`MarketingCloud-SFMCSdk`). All
    aliases for the same module resolve to the same repo slug.
    """
    idx = {}
    deps = ((matrix.get("dependencies") or {}))
    for section in ("keep", "add"):
        for entry in (deps.get(section) or []):
            slug = entry.get("spmRepoSlug")
            if not slug:
                continue
            for key in ("artifact", "spmProduct", "importModule",
                        "podName", "spmPackage"):
                v = entry.get(key)
                if isinstance(v, str) and v:
                    idx.setdefault(v.lower(), slug)
    return idx


def _url_final_slug(url):
    """Return the last non-empty path segment of a URL, .git suffix stripped.

    https://github.com/salesforce-marketingcloud/sfmc-sdk-ios.git → sfmc-sdk-ios
    """
    try:
        path = urllib.parse.urlparse(url).path or ""
    except ValueError:
        return ""
    seg = path.rstrip("/").rsplit("/", 1)[-1]
    if seg.endswith(".git"):
        seg = seg[:-4]
    return seg


def main():
    ap = argparse.ArgumentParser(description="Resolve SFMC SDK module versions from Maven (Android), CocoaPods trunk, or SPM (iOS).")
    ap.add_argument("--project", help="App root to scrape for repo URLs / pod names.")
    ap.add_argument("--repo", action="append", help="Explicit repo base URL (repeatable). Meaning depends on --backend: maven repo, SPM git URL, or ignored for CocoaPods (trunk is fixed).")
    ap.add_argument("--verify", help="Comma list artifact=version to confirm each version still exists.")
    ap.add_argument("--latest", action="store_true", help="Report the newest released version of each artifact.")
    ap.add_argument("--artifacts", help="Comma list of artifacts for --latest (defaults to a platform-specific standard set).")
    ap.add_argument("--backend", choices=("maven", "cocoapods", "spm"), default="maven",
                    help="Backend to resolve against. maven=Android; cocoapods=iOS via CocoaPods trunk; spm=iOS via git tags. Default: maven.")
    ap.add_argument("--timeout", type=float, default=10.0)
    ap.add_argument("--json", action="store_true", help="Emit JSON only.")
    args = ap.parse_args()

    if not args.verify and not args.latest:
        sys.exit("error: pass --verify <spec> and/or --latest")

    verify_map = parse_verify(args.verify) if args.verify else {}

    # Decide which artifacts we care about. Defaults depend on backend, since
    # the iOS module names differ from the Android ones.
    if args.latest:
        if args.artifacts:
            latest_artifacts = [a.strip() for a in args.artifacts.split(",") if a.strip()]
        elif args.backend in ("cocoapods", "spm"):
            latest_artifacts = ["MarketingCloudSDK", "MarketingCloud-SFMCSdk",
                                "SFPushFeatureSDK", "SFInAppMessagingFeatureSDK",
                                "MarketingCloud-ExtensionSDK"]
        else:
            latest_artifacts = ["sfmcsdk", "marketingcloudsdk",
                                "pushfeaturemodule", "inappmessagingfeaturemodule"]
    else:
        latest_artifacts = []
    all_artifacts = list(dict.fromkeys(list(verify_map) + latest_artifacts))

    # iOS backends never touch Maven; delegate the entire resolve to a
    # backend-specific path that shares the reachable-vs-offline classification.
    if args.backend in ("cocoapods", "spm"):
        report = _resolve_ios(args, verify_map, latest_artifacts, all_artifacts)
        print(json.dumps(report, indent=2))
        if not args.json:
            _print_ios_summary(report, args.backend)
        ok = (report["networkReachable"]
              and (report.get("verifyAllOk", True))
              and (report.get("latestAllOk", True)))
        sys.exit(0 if ok else 1)

    # Build the repo candidate list.
    #
    # Explicit --repo values are trusted as-is: the operator typed them, so they
    # are the intended escape hatch for a non-standard host. SCRAPED URLs are
    # different — they come from files we don't control, so each must pass the
    # host allowlist before we ever fetch it (SSRF guard). Rejected scrapes are
    # recorded so the report shows we skipped them rather than silently trusting.
    repos = list(args.repo or [])
    scraped = []
    scraped_rejected = []
    if not repos and args.project:
        if not os.path.isdir(args.project):
            sys.exit(f"error: --project not a directory: {args.project}")
        for url in scrape_repos(args.project):
            if host_allowed(url):
                scraped.append(url)
            else:
                scraped_rejected.append(url)
        repos.extend(scraped)
    if DEFAULT_REPO_FALLBACK not in repos:
        repos.append(DEFAULT_REPO_FALLBACK)

    # For each artifact, walk repos until one serves its metadata.
    #
    # Two DIFFERENT facts get tracked, because conflating them is the bug that
    # made this the highest-risk script:
    #   • network_reachable — did we get ANY HTTP response, even a 404/403? An
    #     HTTP status is proof the network worked and the server answered; the
    #     URL or artifact was just wrong. This must NOT be read as "offline",
    #     because the caller uses "offline" to justify falling back to the stale
    #     matrix seed. A 404 is a wrong-URL problem, not a no-network problem.
    #   • per-artifact `resolved` — did we actually fetch + parse this artifact's
    #     metadata? That's the artifact-found signal, independent of reachability.
    # HTTPError is a SUBCLASS of URLError, so it must be caught FIRST, otherwise
    # a clean 404 falls into the generic URLError arm and is misread as offline.
    results = {}
    network_reachable = False
    repo_used = None
    errors = []
    for art in all_artifacts:
        entry = {"artifact": art, "resolved": False, "repo": None,
                 "versions": [], "release": None, "latest": None}
        for repo in repos:
            try:
                versions, release, latest = fetch_metadata(repo, art, args.timeout)
                network_reachable = True
                entry.update(resolved=True, repo=repo, versions=versions,
                             release=release, latest=latest)
                repo_used = repo_used or repo
                break
            except urllib.error.HTTPError as e:
                # We reached the server and it answered with a status (404/403/500).
                # Network is fine; this repo just doesn't serve this artifact.
                network_reachable = True
                errors.append(f"{art} @ {repo}: HTTP {e.code} {getattr(e, 'reason', '')}".strip())
            except urllib.error.URLError as e:
                # No HTTP response at all: DNS failure, connection refused, timeout.
                # THIS is the genuine offline/unreachable case.
                errors.append(f"{art} @ {repo}: unreachable ({getattr(e, 'reason', e)})")
            except (ET.ParseError, ValueError) as e:
                # A response arrived but wasn't valid metadata — network was fine.
                network_reachable = True
                errors.append(f"{art} @ {repo}: bad metadata ({e})")
        results[art] = entry

    # Compose the answer per mode.
    verify_out = {}
    verify_all_ok = True
    for art, want in verify_map.items():
        r = results[art]
        exists = want in r["versions"]
        if not exists:
            verify_all_ok = False
        verify_out[art] = {
            "pinned": want,
            "exists": exists,
            "resolved": r["resolved"],
            "suggestedLatest": newest(r["versions"]) if r["versions"] else None,
        }

    latest_out = {}
    latest_all_ok = True
    for art in latest_artifacts:
        r = results[art]
        pick = r["release"] or newest(r["versions"])
        if not pick:
            latest_all_ok = False
        latest_out[art] = {
            "latest": pick,
            "resolved": r["resolved"],
            "release": r["release"],
        }

    # Every requested artifact resolved? (used to distinguish "all good" from
    # "reached the repo but some artifact/version was missing" — a wrong-URL or
    # rotted-pin problem, NOT an offline one.)
    all_resolved = all(results[a]["resolved"] for a in all_artifacts) if all_artifacts else True

    report = {
        "group": GROUP,
        # networkReachable is the honest signal: did the server answer at all
        # (even 404)? The offline fallback to the stale matrix seed is ONLY
        # justified when this is false. A 404/403 keeps this true — the fix for
        # that is a corrected URL/version, not a seed fallback.
        "networkReachable": network_reachable,
        # Kept for backwards compatibility with callers that read the old key.
        # It now tracks reachability, NOT resolution — see the note.
        "networkAvailable": network_reachable,
        "allArtifactsResolved": all_resolved,
        "repoUsed": repo_used,
        "reposTried": repos,
        "reposScraped": scraped,
        "reposRejected": scraped_rejected,   # scraped but off-allowlist (SSRF guard)
        "verify": verify_out,
        "latest": latest_out,
        "errors": errors,
        "note": ("Maven metadata confirms a version EXISTS / is NEWEST — not that a set of "
                 "module versions cohere. Let Gradle resolve the chosen set (Phase 5 compile) "
                 "to confirm the bundle. Fall back to the matrix seed ONLY when networkReachable "
                 "is false (genuinely offline). If networkReachable is true but an artifact/version "
                 "did not resolve (e.g. HTTP 404), that's a wrong-URL or rotted-pin problem — fix "
                 "the URL/version, do NOT pretend the seed was verified. reposRejected lists scraped "
                 "repo URLs skipped because their host is not on the SFMC allowlist."),
    }
    print(json.dumps(report, indent=2))

    if not args.json:
        e = sys.stderr
        print("", file=e)
        print("=== SFMC module version resolution ===", file=e)
        print(f"  network : {'reachable' if network_reachable else 'UNREACHABLE — offline, fall back to matrix seed'}", file=e)
        print(f"  repo    : {repo_used or '(none served metadata)'}", file=e)
        if scraped_rejected:
            print(f"  ⚠ skipped {len(scraped_rejected)} scraped repo URL(s) off the SFMC allowlist: "
                  f"{', '.join(scraped_rejected)}", file=e)
        if verify_out:
            print("  verify (matrix pins still on the repo?):", file=e)
            for art, v in verify_out.items():
                mark = "✓" if v["exists"] else ("✗ MISSING" if v["resolved"] else "? unresolved")
                sug = f" (latest {v['suggestedLatest']})" if v["suggestedLatest"] and not v["exists"] else ""
                print(f"    {mark:<11} {art} = {v['pinned']}{sug}", file=e)
        if latest_out:
            print("  latest (newest released per module):", file=e)
            for art, v in latest_out.items():
                print(f"    {art} -> {v['latest'] or '? unresolved'}", file=e)
        if not network_reachable:
            print("  ⚠ Could not reach the Maven repo (offline). Use matrix seed versions and note it.", file=e)
        elif not all_resolved:
            print("  ⚠ Reached the repo but some artifact/version did not resolve — this is a "
                  "wrong-URL / rotted-pin issue, NOT offline. Fix the URL or version; do not fall "
                  "back to the seed as if verified.", file=e)

    # Exit non-zero if anything the caller asked for wasn't satisfied. But the
    # MEANING differs by cause, which the report/stderr make explicit: offline
    # (fall back to seed) vs. reachable-but-missing (fix the URL/version).
    ok = network_reachable and (verify_all_ok if verify_map else True) and (latest_all_ok if latest_artifacts else True)
    sys.exit(0 if ok else 1)


def _resolve_ios(args, verify_map, latest_artifacts, all_artifacts):
    """Resolve iOS artifacts via CocoaPods trunk or SPM git tags.

    Same reachable-vs-offline classification as the Maven path so the report
    shape stays uniform. Two backend-specific rules:
      • CocoaPods: `--repo` is ignored (trunk endpoint is fixed).
      • SPM: each artifact must map to a repo URL. We take explicit --repo values
        first, then scrape Package.swift / pbxproj files for --project. If an
        artifact has no repo URL, it's marked unresolved with "no SPM repo URL
        supplied" — NOT a network problem.
    """
    network_reachable = False
    errors = []
    scraped = []
    scraped_rejected = []
    results = {}

    if args.backend == "cocoapods":
        # Trunk is a fixed public endpoint; there is nothing to scrape or reject.
        for pod in all_artifacts:
            entry = {"artifact": pod, "resolved": False, "backend": "cocoapods",
                     "repo": COCOAPODS_TRUNK_BASE, "versions": []}
            try:
                versions = fetch_cocoapods_versions(pod, args.timeout)
                network_reachable = True
                entry.update(resolved=True, versions=versions)
            except urllib.error.HTTPError as e:
                # Reached trunk; this pod just isn't there. Network is fine.
                network_reachable = True
                errors.append(f"{pod} @ cocoapods: HTTP {e.code} {getattr(e, 'reason', '')}".strip())
            except urllib.error.URLError as e:
                errors.append(f"{pod} @ cocoapods: unreachable ({getattr(e, 'reason', e)})")
            except (json.JSONDecodeError, ValueError) as e:
                network_reachable = True
                errors.append(f"{pod} @ cocoapods: bad JSON ({e})")
            results[pod] = entry
    else:  # spm
        # SPM: each SFMC module lives in its OWN GitHub repo, so an artifact
        # binds to exactly one repo URL — the one whose final path segment
        # matches its `spmRepoSlug` from the migration matrix. Historical bug:
        # we used to sweep every candidate URL for every artifact and take the
        # first that returned tags, which meant every artifact got whichever
        # URL was scraped first (uniform version bug — the "11.0.1 for
        # push-feature" symptom). Now:
        #   1. Load the matrix and build an artifact→slug index.
        #   2. Scrape candidate URLs from the project (+ explicit --repo).
        #   3. For each artifact, pick the ONE candidate whose slug matches.
        #   4. If nothing matches, the artifact is unresolved with a clear
        #      "no matching repo URL for slug 'X'" — NOT an offline error.
        candidates = list(args.repo or [])
        if args.project:
            if not os.path.isdir(args.project):
                sys.exit(f"error: --project not a directory: {args.project}")
            for u in scrape_ios_spm_urls(args.project):
                if host_allowed(u):
                    if u not in candidates:
                        candidates.append(u)
                        scraped.append(u)
                else:
                    scraped_rejected.append(u)
        matrix = _load_ios_matrix()
        slug_index = _build_artifact_slug_index(matrix)
        # Map each candidate URL to its final slug ONCE — reused per artifact.
        url_slug_map = {u: _url_final_slug(u).lower() for u in candidates}
        if not candidates:
            errors.append("no SPM repo URLs supplied (pass --repo, or --project with a Package.swift/pbxproj that declares one)")
        for art in all_artifacts:
            entry = {"artifact": art, "resolved": False, "backend": "spm",
                     "repo": None, "versions": []}
            want_slug = slug_index.get(art.lower())
            if not want_slug:
                # No matrix entry for this artifact name — fall back to the old
                # sweep so a caller passing a non-matrix artifact still works.
                # This is the escape hatch for artifacts the matrix hasn't
                # catalogued yet (e.g. an in-development feature module).
                errors.append(
                    f"{art}: no spmRepoSlug in matrix; falling back to first "
                    f"candidate that answers (may bind to the wrong repo)"
                )
                for repo_url in candidates:
                    try:
                        tags = fetch_spm_versions(repo_url, args.timeout)
                        network_reachable = True
                        entry.update(resolved=True, repo=repo_url, versions=tags)
                        break
                    except urllib.error.URLError as e:
                        errors.append(f"{art} @ {repo_url}: unreachable ({getattr(e, 'reason', e)})")
                results[art] = entry
                continue
            # Slug-based binding: exactly one candidate should match.
            matched_url = next(
                (u for u, s in url_slug_map.items() if s == want_slug.lower()),
                None,
            )
            if not matched_url:
                errors.append(
                    f"{art}: no candidate repo URL matches slug '{want_slug}' "
                    f"(candidates: {', '.join(url_slug_map.values()) or '(none)'})"
                )
                results[art] = entry
                continue
            try:
                tags = fetch_spm_versions(matched_url, args.timeout)
                network_reachable = True
                entry.update(resolved=True, repo=matched_url, versions=tags)
            except urllib.error.URLError as e:
                # A git failure or an unreachable host — treat like Maven's
                # URLError arm (the offline branch).
                errors.append(f"{art} @ {matched_url}: unreachable ({getattr(e, 'reason', e)})")
            results[art] = entry

    # verify + latest reduce identically to the Maven path.
    verify_out = {}
    verify_all_ok = True
    for art, want in verify_map.items():
        r = results[art]
        exists = want in r["versions"]
        if not exists:
            verify_all_ok = False
        verify_out[art] = {
            "pinned": want,
            "exists": exists,
            "resolved": r["resolved"],
            "suggestedLatest": newest(r["versions"]) if r["versions"] else None,
        }
    latest_out = {}
    latest_all_ok = True
    for art in latest_artifacts:
        r = results[art]
        pick = newest(r["versions"]) if r["versions"] else None
        if not pick:
            latest_all_ok = False
        latest_out[art] = {"latest": pick, "resolved": r["resolved"]}

    all_resolved = all(results[a]["resolved"] for a in all_artifacts) if all_artifacts else True

    # Coherence-check hint — iOS has no single-command equivalent of Gradle's
    # resolve, so the report names the command Phase 5 must run to prove the
    # chosen set actually installs together.
    if args.backend == "cocoapods":
        coherence_hint = "pod install --repo-update  # from the directory containing Podfile"
    else:
        coherence_hint = "xcodebuild -resolvePackageDependencies -project <YourApp>.xcodeproj  # or `swift package resolve` for a pure SPM project"

    return {
        "backend": args.backend,
        "networkReachable": network_reachable,
        "networkAvailable": network_reachable,   # legacy alias
        "allArtifactsResolved": all_resolved,
        "reposScraped": scraped,
        "reposRejected": scraped_rejected,
        "verify": verify_out,
        "latest": latest_out,
        "verifyAllOk": verify_all_ok,
        "latestAllOk": latest_all_ok,
        "errors": errors,
        "coherenceCheckHint": coherence_hint,
        "note": ("A version EXISTING in trunk / as a git tag is not proof that the module set installs "
                 "coherently. iOS has no single-command equivalent of Gradle's resolve — Phase 5 must "
                 "run the coherenceCheckHint above to confirm. Fall back to the matrix seed ONLY when "
                 "networkReachable is false. If networkReachable is true but an artifact/version did "
                 "not resolve, that's a wrong-name / rotted-pin / missing-repo-URL problem — fix the "
                 "input, do NOT pretend the seed was verified."),
    }


def _print_ios_summary(report, backend):
    e = sys.stderr
    print("", file=e)
    print(f"=== SFMC iOS ({backend}) version resolution ===", file=e)
    print(f"  network : {'reachable' if report['networkReachable'] else 'UNREACHABLE — offline, fall back to matrix seed'}", file=e)
    if report["reposRejected"]:
        print(f"  ⚠ skipped {len(report['reposRejected'])} scraped repo URL(s) off the SFMC allowlist: "
              f"{', '.join(report['reposRejected'])}", file=e)
    if report["verify"]:
        print("  verify (matrix pins still resolvable?):", file=e)
        for art, v in report["verify"].items():
            mark = "✓" if v["exists"] else ("✗ MISSING" if v["resolved"] else "? unresolved")
            sug = f" (latest {v['suggestedLatest']})" if v["suggestedLatest"] and not v["exists"] else ""
            print(f"    {mark:<11} {art} = {v['pinned']}{sug}", file=e)
    if report["latest"]:
        print("  latest (newest published per module):", file=e)
        for art, v in report["latest"].items():
            print(f"    {art} -> {v['latest'] or '? unresolved'}", file=e)
    print(f"  coherence check: run `{report['coherenceCheckHint']}` in Phase 5.", file=e)
    if not report["networkReachable"]:
        print("  ⚠ Could not reach the backend (offline). Use matrix seed versions and note it.", file=e)
    elif not report["allArtifactsResolved"]:
        print("  ⚠ Reached the backend but some artifact/version did not resolve — this is a "
              "wrong-name / rotted-pin issue, NOT offline. Fix the input; do not fall "
              "back to the seed as if verified.", file=e)


if __name__ == "__main__":
    main()
