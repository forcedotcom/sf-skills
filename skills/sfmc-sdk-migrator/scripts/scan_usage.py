#!/usr/bin/env python3
"""
scan_usage.py — Deterministic inventory of SFMC SDK usage in a customer repo.

Why this exists: grepping by hand is slow and misses call sites in files you
didn't think to open. This walks the repo once, matches against the migration
matrix's detection rules + per-mapping regexes, and prints a structured worklist
so the migration is driven by data, not by memory.

Usage:
    python3 scan_usage.py <repo-path> [--platform android] [--matrix PATH] [--json]

  <repo-path>     Root of the customer app to scan.
  --platform      android (default). Selects the bundled matrix + file globs.
  --matrix PATH   Override the matrix file (use the customer's own Breaking
                  Changes Log if they have one). Defaults to the bundled
                  references/migration-matrix-<platform>.json.
  --json          Emit raw JSON only (for piping). Default prints JSON plus a
                  short human summary to stderr.

Exit code is 0 even when nothing is found — "no SDK usage" is a valid answer,
not an error. Output always includes a `detected` block (version/era) and a
`findings` list (file, line, matched mapping id, the matched text).

The script reads ONLY the matrix for symbol knowledge — it has no hardcoded SDK
API names beyond the detection bootstrap. Update the matrix, not this script,
when the SDK changes.

--------------------------------------------------------------------------------
ERA IS DECIDED BY ARTIFACTS, NOT BY FINDINGS

The one subtle trap this script exists to avoid: in v11 the engagement module is
STILL published as `marketingcloudsdk` and still ships legacy-shaped symbols
(Inbox/Region/Analytics/tags/sdkState). A correctly-migrated unified project
therefore produces plenty of matrix findings — so inferring "legacy" from the
presence of findings would mislabel a healthy v11 app as needing the full
architecture migration. Era is instead keyed off the matrix's detection rules
(`detection.eraDisambiguation`): the presence of a unified-core artifact
(`sfmcsdk`) means UNIFIED, regardless of how many engagement symbols appear.
Findings are a worklist signal, never an era signal. Legacy *entry points*
(`MarketingCloudSdk.init` / `.getInstance`, which have no unified equivalent)
distinguish a still-to-migrate / in-progress project from one whose engagement
call sites are legitimately preserved.

VERSION DETECTION IS DETERMINISTIC AND ARTIFACT-AWARE

`currentVersion` is read from the UMBRELLA artifact (`marketingcloudsdk`), which
carries the changelog version in BOTH eras (legacy 8.x/9.x, unified 11.0.1) — it
is NOT read from `sfmcsdk`, whose independent 3.x stream would make an
already-unified project look like major<10 and get misclassified as legacy.
Matches are collected across ALL files and resolved deterministically (highest
by SemVer precedence, with a conflict flag), never "first file os.walk happens
to visit wins".
"""
import argparse
import json
import os
import re
import sys

import semver  # shared, precedence-correct version math (scripts/semver.py)

# File extensions worth scanning per platform. Kept here (not the matrix)
# because they're about the language, not the SDK version.
PLATFORM_GLOBS = {
    "android": (".kt", ".java", ".gradle", ".kts", ".xml", ".toml", ".properties"),
    "ios": (".swift", ".m", ".mm", ".h", ".plist", ".pbxproj", ".resolved",
            ".xcconfig", ".entitlements"),
}

# iOS pins live in files with no extension (Podfile, Package.swift is technically
# a .swift file we already catch, but Podfile / Podfile.lock / Cartfile need
# exact-name matching). Extend platform detection to match by filename in addition
# to extension.
PLATFORM_EXACT_FILENAMES = {
    "android": (),
    "ios": ("Podfile", "Podfile.lock", "Package.swift", "Package.resolved",
            "Cartfile", "Cartfile.resolved"),
}

# Directories that never contain customer source worth rewriting.
SKIP_DIRS = {".git", "build", ".gradle", ".idea", "node_modules", "Pods",
             "DerivedData", ".cxx", "captures", "out", "dist",
             "xcuserdata", ".swiftpm"}

# File extensions per language, used by mapping-level objcOnly / swiftOnly gates.
SWIFT_EXTS = (".swift",)
OBJC_EXTS = (".m", ".mm", ".h")

DEFAULT_MATRIX_REL = os.path.join("..", "references", "migration-matrix-{platform}.json")


def load_matrix(platform, override):
    if override:
        path = override
    else:
        here = os.path.dirname(os.path.abspath(__file__))
        path = os.path.normpath(os.path.join(here, DEFAULT_MATRIX_REL.format(platform=platform)))
    if not os.path.isfile(path):
        sys.exit(f"error: matrix not found at {path}. Pass --matrix to point at one.")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f), path


def iter_files(root, exts, exact_names=()):
    """Yield source files worth scanning.

    `exts` matches by suffix (`.swift`, `.plist`, etc). `exact_names` matches
    by full filename — used for iOS files that carry no extension (`Podfile`,
    `Package.resolved`, `Cartfile`).
    """
    exact_set = set(exact_names)
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            if name.endswith(exts) or name in exact_set:
                yield os.path.join(dirpath, name)


def collect_artifact_versions(text, artifact_regexes):
    """Return {artifact: set(version_strings)} for every artifact match in `text`.

    Collects ALL matches (a project can pin the same artifact in more than one
    file, and occasionally at conflicting versions) so the caller can resolve
    deterministically rather than taking whatever os.walk saw first.

    `artifact_regexes` values must already be compiled patterns — the caller
    controls flags (e.g. IGNORECASE for iOS).
    """
    hits = {}
    for artifact, rx in artifact_regexes.items():
        for m in rx.finditer(text):
            hits.setdefault(artifact, set()).add(m.group(1))
    return hits


def resolve_current_version(versions_by_artifact, umbrella_artifacts):
    """Pick the reported currentVersion deterministically and artifact-aware.

    The changelog/umbrella version lives on `marketingcloudsdk` in BOTH eras
    (legacy 8.x/9.x, unified 11.0.1), so that's what we report — NOT `sfmcsdk`,
    whose separate 3.x stream would make a unified project look pre-boundary.
    When several versions are pinned for the umbrella artifact, we take the
    highest by SemVer precedence and flag the conflict; when the umbrella
    artifact is absent, currentVersion is genuinely undeterminable from pins and
    we return None rather than borrowing a core-stream number.

    Returns (version_str_or_None, conflict_bool).
    """
    for artifact in umbrella_artifacts:
        found = sorted(versions_by_artifact.get(artifact, ()))
        if found:
            best = max(found, key=semver.key)
            return best, len(found) > 1
    return None, False


def build_matchers(matrix, regex_flags=0):
    """Compile (mapping_id, area, feature, manualReview, compiled_regex) tuples.

    `regex_flags` is passed to `re.compile` so callers can turn on
    IGNORECASE for platforms that need it (iOS Package.resolved lowercases
    identities while Podfile keeps CamelCase).
    """
    matchers = []
    for mp in matrix.get("mappings", []):
        rx = mp.get("oldRegex")
        if not rx:
            # Fall back to a loosened literal of `old` if no explicit regex.
            literal = re.escape(mp["old"].split("(")[0].strip())
            rx = literal
        try:
            compiled = re.compile(rx, regex_flags)
        except re.error:
            compiled = re.compile(re.escape(mp.get("old", "")), regex_flags)
        matchers.append({
            "id": mp.get("id"),
            "area": mp.get("area"),
            "feature": mp.get("feature"),
            "async": mp.get("async", False),
            "manualReview": mp.get("manualReview", False),
            "objcOnly": mp.get("objcOnly", False),
            "swiftOnly": mp.get("swiftOnly", False),
            "regex": compiled,
        })
    return matchers


def main():
    ap = argparse.ArgumentParser(description="Scan a repo for SFMC SDK usage.")
    ap.add_argument("repo")
    ap.add_argument("--platform", default="android", choices=sorted(PLATFORM_GLOBS))
    ap.add_argument("--matrix", default=None)
    ap.add_argument("--json", action="store_true", help="Emit JSON only.")
    args = ap.parse_args()

    if not os.path.isdir(args.repo):
        sys.exit(f"error: not a directory: {args.repo}")

    matrix, matrix_path = load_matrix(args.platform, args.matrix)
    detection = matrix.get("detection", {})
    pkg_roots = detection.get("packageRoots", [])
    legacy_arts = detection.get("legacyArtifacts", [])
    modern_arts = detection.get("modernArtifacts", [])
    # Era is keyed off the unified CORE artifact, not any modern artifact and
    # not the presence of findings — see detection.eraDisambiguation. Default to
    # sfmcsdk if the matrix predates the field.
    unified_core_arts = detection.get("unifiedCoreArtifacts", ["sfmcsdk"])
    # The changelog/umbrella version lives on these artifacts in both eras.
    umbrella_arts = detection.get("umbrellaVersionArtifacts", ["marketingcloudsdk"])
    # iOS pins the same identity in Podfile (CamelCase) and Package.resolved
    # (lowercased) — case-insensitive matching keeps ONE regex viable across
    # both, and doesn't hurt Android where names are canonical.
    regex_flags = re.IGNORECASE if args.platform == "ios" else 0
    # Legacy entry points have NO unified equivalent, so their presence alongside
    # a unified core means the migration is partial/in-progress.
    entry_point_regexes = [re.compile(rx, regex_flags)
                           for rx in detection.get("legacyEntryPointRegexes", [])]
    # iOS-only: transitional 9.x-only symbols. Presence distinguishes the
    # 9.x transitional era (era 2) from pure-legacy 8.x (era 1) when the
    # umbrella version alone is ambiguous (e.g. missing lockfile). Absent on
    # Android — the block will just be empty there.
    transitional_regexes = [re.compile(rx, regex_flags)
                            for rx in detection.get("transitionalEntryPointRegexes", [])]
    # Prefer the artifact-keyed regex map; fall back to the flat list if a matrix
    # predates it (loses artifact attribution but stays deterministic).
    artifact_regexes_src = detection.get("versionArtifactRegexes")
    if not artifact_regexes_src:
        artifact_regexes_src = {f"_regex{i}": rx for i, rx in enumerate(detection.get("versionRegexes", []))}
        umbrella_arts = list(artifact_regexes_src)  # can't attribute; treat all as umbrella
    artifact_regexes = {a: re.compile(rx, regex_flags) for a, rx in artifact_regexes_src.items()}
    matchers = build_matchers(matrix, regex_flags=regex_flags)
    exts = PLATFORM_GLOBS[args.platform]
    exact_names = PLATFORM_EXACT_FILENAMES.get(args.platform, ())

    findings = []
    files_touching_sdk = set()
    feature_hits = set()
    area_counts = {}
    symbol_counts = {}
    versions_by_artifact = {}   # artifact -> set(version strings), collected across ALL files
    saw_legacy_artifact = False
    saw_modern_artifact = False
    saw_unified_core = False
    saw_legacy_entry_point = False
    saw_transitional_symbol = False

    for path in iter_files(args.repo, exts, exact_names):
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
        except OSError:
            continue
        text = "".join(lines)
        # Language gates for objcOnly / swiftOnly matchers — resolved per file,
        # not per line, since the extension is the same for every line.
        path_lower = path.lower()
        is_swift_file = path_lower.endswith(SWIFT_EXTS)
        is_objc_file = path_lower.endswith(OBJC_EXTS)

        # Version / artifact detection on build & config files. Collect from
        # EVERY file (not first-match-wins) so the result doesn't depend on
        # os.walk order; resolve deterministically after the walk.
        for artifact, found in collect_artifact_versions(text, artifact_regexes).items():
            versions_by_artifact.setdefault(artifact, set()).update(found)
        if any(a in text for a in legacy_arts):
            saw_legacy_artifact = True
        if any(a in text for a in modern_arts):
            saw_modern_artifact = True
        if any(a in text for a in unified_core_arts):
            saw_unified_core = True
        if any(rx.search(text) for rx in entry_point_regexes):
            saw_legacy_entry_point = True
        if any(rx.search(text) for rx in transitional_regexes):
            saw_transitional_symbol = True

        touches_sdk = any(root in text for root in pkg_roots)

        # Per-line mapping matches.
        for lineno, line in enumerate(lines, 1):
            for m in matchers:
                # objcOnly mappings only fire in Obj-C files; swiftOnly only in
                # Swift files. When neither flag is set, apply to all source.
                if m["objcOnly"] and not is_objc_file:
                    continue
                if m["swiftOnly"] and not is_swift_file:
                    continue
                if m["regex"].search(line):
                    rel = os.path.relpath(path, args.repo)
                    findings.append({
                        "file": rel,
                        "line": lineno,
                        "mappingId": m["id"],
                        "area": m["area"],
                        "feature": m["feature"],
                        "async": m["async"],
                        "manualReview": m["manualReview"],
                        "text": line.strip()[:200],
                    })
                    files_touching_sdk.add(rel)
                    area_counts[m["area"]] = area_counts.get(m["area"], 0) + 1
                    symbol_counts[m["id"]] = symbol_counts.get(m["id"], 0) + 1
                    if m["feature"]:
                        feature_hits.add(m["feature"])

        if touches_sdk:
            files_touching_sdk.add(os.path.relpath(path, args.repo))

    # Resolve the reported current version deterministically from the umbrella
    # artifact (see resolve_current_version — never from the sfmcsdk core stream).
    detected_version, version_conflict = resolve_current_version(versions_by_artifact, umbrella_arts)

    # Infer API era from ARTIFACTS and versions, per detection.eraDisambiguation
    # — NOT from whether findings exist. A correctly-migrated v11 project still
    # produces findings against engagement APIs it legitimately keeps, so
    # findings can't decide era.
    #
    # iOS has THREE eras — the umbrella major version disambiguates:
    #   • MarketingCloudSDK <9   ⇒ legacy-pure 8.x        (era 1)
    #   • MarketingCloudSDK ==9  ⇒ legacy-transitional    (era 2, the SFMCSdk
    #                                                     façade exists but
    #                                                     wraps the monolith)
    #   • MarketingCloudSDK >=10 ⇒ unified v10+/v11       (era 3)
    #   • Unified feature-modules present (PushFeatureSDK / IAM feature module)
    #                            ⇒ unified even if the umbrella can't be read
    #
    # Android keeps two eras — sfmcsdk presence flips to unified, otherwise
    # legacy. The version-based branch only fires when the matrix declares three
    # eras via `detection.transitionalEntryPointRegexes`.
    umbrella_major = None
    if detected_version:
        try:
            umbrella_major = semver.release_tuple(detected_version)[0]
        except Exception:
            umbrella_major = None

    three_era_platform = bool(detection.get("transitionalEntryPointRegexes"))

    if three_era_platform:
        # iOS: era keyed off the umbrella major, then adjusted by symbol presence.
        if saw_unified_core or (umbrella_major is not None and umbrella_major >= 10):
            era = matrix.get("targetApiEra", "unified-SFMCSDK")
            # In v11 (era 3), legacy entry points OR transitional symbols in code
            # mean the main app is not yet fully migrated. Sample apps often
            # have already-migrated NSE/Content Extension targets alongside a
            # still-legacy main app — the scanner surfaces that as partial.
            if saw_legacy_entry_point or saw_transitional_symbol:
                migration_status = "partial-migration"
            else:
                migration_status = "already-modern"
        elif umbrella_major == 9 or saw_transitional_symbol:
            era = "legacy-transitional-SFMCSDK"
            migration_status = "not-started"
        elif saw_legacy_artifact or saw_legacy_entry_point or findings:
            era = matrix.get("sourceApiEra", "legacy-MarketingCloudSDK")
            migration_status = "not-started"
        else:
            era = "unknown"
            migration_status = "no-sdk"
    else:
        # Android (two eras): unified-core artifact decides.
        if saw_unified_core:
            era = matrix.get("targetApiEra", "unified")
            migration_status = "partial-migration" if saw_legacy_entry_point else "already-modern"
        elif saw_legacy_artifact or saw_legacy_entry_point or findings:
            era = matrix.get("sourceApiEra", "legacy")
            migration_status = "not-started"
        else:
            era = "unknown"
            migration_status = "no-sdk"

    report = {
        "repo": os.path.abspath(args.repo),
        "platform": args.platform,
        "matrixPath": matrix_path,
        "detected": {
            "currentVersion": detected_version,
            "targetVersion": matrix.get("targetVersion"),
            "apiEra": era,
            "migrationStatus": migration_status,
            "sdkIntegrated": saw_legacy_artifact or saw_modern_artifact,
            "sawLegacyArtifact": saw_legacy_artifact,
            "sawModernArtifact": saw_modern_artifact,
            "sawUnifiedCore": saw_unified_core,
            "sawLegacyEntryPoint": saw_legacy_entry_point,
            "sawTransitionalSymbol": saw_transitional_symbol,
            "umbrellaMajor": umbrella_major,
            "versionConflict": version_conflict,
            "versionsByArtifact": {a: sorted(vs) for a, vs in sorted(versions_by_artifact.items())},
        },
        "featuresInUse": sorted(feature_hits),
        "filesTouchingSdk": sorted(files_touching_sdk),
        "areaCounts": area_counts,
        "symbolCounts": symbol_counts,
        "findings": findings,
        "manualReviewCount": sum(1 for f in findings if f["manualReview"]),
    }

    print(json.dumps(report, indent=2))

    if not args.json:
        d = report["detected"]
        print("", file=sys.stderr)
        print("=== SFMC SDK scan summary ===", file=sys.stderr)
        print(f"  sdk integrated  : {'yes' if d['sdkIntegrated'] else 'NO — no com.salesforce.marketingcloud artifact found'}", file=sys.stderr)
        cv = d['currentVersion'] or 'unknown'
        if d['versionConflict']:
            cv += " (⚠ multiple umbrella versions pinned — highest shown; reconcile before migrating)"
        print(f"  current version : {cv}", file=sys.stderr)
        print(f"  target version  : {d['targetVersion']}", file=sys.stderr)
        print(f"  API era         : {d['apiEra']}", file=sys.stderr)
        print(f"  migration status: {d['migrationStatus']}", file=sys.stderr)
        if d['migrationStatus'] == 'already-modern':
            print("    → unified core present, no legacy entry points — likely nothing to migrate; "
                  "confirm before rewriting working code.", file=sys.stderr)
        elif d['migrationStatus'] == 'partial-migration':
            print("    → unified core present BUT legacy/transitional call sites still exist — "
                  "migration is in progress; finish the entry-point rewrite.", file=sys.stderr)
        elif d['apiEra'] == 'legacy-transitional-SFMCSDK':
            print("    → iOS 9.x transitional era: `SFMCSdk` façade over the monolith. "
                  "v11 removes `SFMCSdk.mp` / `.requestPushSdk` — expect API-shape rewrites, "
                  "not just a pod bump.", file=sys.stderr)
        print(f"  features in use : {', '.join(report['featuresInUse']) or 'none detected'}", file=sys.stderr)
        print(f"  files w/ usage  : {len(report['filesTouchingSdk'])}", file=sys.stderr)
        print(f"  call sites      : {len(findings)} "
              f"({report['manualReviewCount']} need manual review)", file=sys.stderr)
        if area_counts:
            print("  by area         : "
                  + ", ".join(f"{k}={v}" for k, v in sorted(area_counts.items())),
                  file=sys.stderr)


if __name__ == "__main__":
    main()
