#!/usr/bin/env python3
"""
target_options.py — Given a current SDK version, compute the upgrade targets
worth offering the customer.

Why this exists: "always jump to latest" is the wrong default. A customer two
majors behind often wants a staged upgrade, and crossing the legacy->unified
architecture boundary (major 10) is a fundamentally bigger change than a bump
within an era. This script reads the scraped version catalog and produces a
small, meaningful menu so the skill can ask the user which target they want
instead of deciding for them.

Usage:
    python3 target_options.py --current 8.1.0 [--target 11.0.1] [--platform android] [--catalog PATH] [--json]

If --target is given and is lower than --current, the script refuses with
{"error": "cant downgrade the sdk"} and exit code 2 — this skill never downgrades.

Output (JSON): the current version's era, and a list of recommended targets,
each tagged with whether reaching it crosses the architecture boundary (i.e.
requires the full code migration vs. a version/config bump).
"""
import argparse
import json
import os
import sys

import semver  # shared, precedence-correct version math (scripts/semver.py)

DEFAULT_CATALOG_REL = os.path.join("..", "references", "version-catalog-{platform}.json")


def target_precision(spec):
    """How specifically did the user pin the target?

    Returns (precision, prefix) where precision is the count of concrete numeric
    components the user gave (1=major, 2=major.minor, 3=exact), and prefix is the
    tuple of those components. Wildcard/blank tokens ('x', '*', '+', '') and a
    leading 'v' are ignored, so 'v10', '10', '10.x', '10.+' all read as
    precision 1 / prefix (10,), while '10.0.0' reads as precision 3.

    The rule this encodes: a partial spec ("v10") means "the latest release in
    that line", an exact spec ("10.0.0") means "that release, nothing else".
    """
    s = str(spec).strip().lstrip("vV")
    concrete = []
    for tok in s.split("."):
        digits = "".join(ch for ch in tok if ch.isdigit())
        if tok in ("", "x", "X", "*", "+") or digits == "":
            break  # a wildcard/blank ends the concrete prefix
        concrete.append(int(digits))
    precision = min(len(concrete), 3)
    return precision, tuple(concrete[:precision])


def resolve_target(spec, versions):
    """Expand a possibly-partial target spec to a concrete catalogued version.

    - Exact (precision 3): return it as-is (validated against downgrade later;
      it need not be in the catalog — a customer may name a release we haven't
      scraped, and that's their call).
    - Partial (precision 1 or 2): pick the NEWEST catalogued version whose
      major(.minor) matches the prefix. This is the "v10 -> latest 10.x" rule.

    Returns (concrete_version_str, note) or raises ValueError if a partial spec
    matches nothing in the catalog.
    """
    precision, prefix = target_precision(spec)
    if precision >= 3:
        return str(spec).strip().lstrip("vV"), None
    if precision == 0:
        raise ValueError(f"could not read a version out of target '{spec}'")

    matches = [v for v in versions if semver.release_tuple(v["version"])[:precision] == prefix]
    if not matches:
        line = ".".join(str(x) for x in prefix) + ".x"
        raise ValueError(f"no catalogued release matches {line}")
    best = max(matches, key=lambda v: semver.key(v["version"]))
    line = ".".join(str(x) for x in prefix) + ".x"
    note = (f"Interpreted target '{spec}' as the {line} line → newest available "
            f"is {best['version']} ({best.get('date', '?')}).")
    return best["version"], note


def load_catalog(platform, override):
    if override:
        path = override
    else:
        here = os.path.dirname(os.path.abspath(__file__))
        path = os.path.normpath(os.path.join(here, DEFAULT_CATALOG_REL.format(platform=platform)))
    if not os.path.isfile(path):
        sys.exit(f"error: version catalog not found at {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f), path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--current", required=True, help="Detected current version, e.g. 8.1.0")
    ap.add_argument("--target", default=None,
                    help="Version the customer asked for. A PARTIAL spec ('v10', '10', '10.x', "
                         "'10.1') is expanded to the newest catalogued release in that line "
                         "(so 'v10' -> latest 10.x). An EXACT spec ('10.0.0') pins that release "
                         "only. If the resolved target is lower than --current, this is a "
                         "downgrade: the script errors out and the migration must stop.")
    ap.add_argument("--platform", default="android")
    ap.add_argument("--catalog", default=None)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    catalog, path = load_catalog(args.platform, args.catalog)
    boundary = catalog.get("eraBoundaryMajor", 10)
    versions = catalog["versions"]
    cur = semver.parse(args.current)                 # precedence-correct comparisons
    cur_major = semver.release_tuple(args.current)[0]  # era/grouping only
    cur_era = "unified" if cur_major >= boundary else "legacy"

    # Downgrade guard. If the customer named a specific target and it is *older* than what
    # their build files already declare, refuse — this skill upgrades the SDK, it never moves
    # a project backwards. A downgrade is almost always a typo or a misread of the current
    # version, and silently "migrating" to an older release would break their app. Stop here
    # and let the caller surface the error rather than guessing what they meant.
    target_resolution_note = None
    if args.target is not None:
        # Expand a partial spec ("v10", "10.x") to the newest catalogued release
        # in that line; leave an exact spec ("10.0.0") untouched.
        try:
            resolved_target, target_resolution_note = resolve_target(args.target, versions)
        except ValueError as e:
            err = {
                "error": "unresolvable target",
                "currentVersion": args.current,
                "requestedTarget": args.target,
                "message": str(e),
            }
            print(json.dumps(err, indent=2))
            print(f"\nerror: {e}", file=sys.stderr)
            sys.exit(3)
        args.target = resolved_target  # downstream logic uses the concrete version

        tgt = semver.parse(args.target)
        if tgt < cur:
            err = {
                "error": "cant downgrade the sdk",
                "currentVersion": args.current,
                "requestedTarget": args.target,
                "message": (
                    f"Requested target {args.target} is lower than the currently integrated "
                    f"version {args.current}. This skill only upgrades the SFMC SDK; it will not "
                    f"downgrade. Stopping."
                ),
            }
            print(json.dumps(err, indent=2))
            print(f"\nerror: cant downgrade the sdk "
                  f"(requested {args.target} < current {args.current})", file=sys.stderr)
            sys.exit(2)
        if tgt == cur:
            print(json.dumps({
                "platform": args.platform, "catalogPath": path,
                "currentVersion": args.current, "requestedTarget": args.target,
                "resolvedTarget": args.target, "targetResolutionNote": target_resolution_note,
                "currentEra": cur_era, "alreadyCurrent": True, "options": [],
                "message": f"Requested target {args.target} matches the current version — nothing to do."
            }, indent=2))
            return

    # Newer-than-current versions only.
    newer = [v for v in versions if semver.parse(v["version"]) > cur]
    newer.sort(key=lambda v: semver.key(v["version"]))

    options = []
    seen_kinds = set()

    def add(v, label, rationale):
        crosses = (v["major"] >= boundary) and (cur_major < boundary)
        options.append({
            "version": v["version"],
            "date": v.get("date"),
            "label": label,
            "crossesArchitectureBoundary": crosses,
            "migrationKind": "full-code-migration" if crosses else "version-config-bump",
            "rationale": rationale,
            "notes": v.get("notes", ""),
        })

    if not newer:
        print(json.dumps({
            "platform": args.platform, "catalogPath": path,
            "currentVersion": args.current, "currentEra": cur_era,
            "alreadyCurrent": True, "options": [],
            "message": "Already at or above the newest catalogued version."
        }, indent=2))
        return

    latest = newer[-1]

    # Option 1: latest stable (always offered).
    add(latest, "Latest stable", "Most current features and fixes.")
    seen_kinds.add(latest["version"])

    # Option 2: highest patch within the current major (safe, no architecture change),
    # if one exists and isn't already the latest.
    same_major = [v for v in newer if v["major"] == cur_major]
    if same_major and same_major[-1]["version"] not in seen_kinds:
        v = same_major[-1]
        add(v, f"Latest {cur_major}.x (stay on current architecture)",
            "Safest upgrade — newest release without leaving your current SDK architecture. No code-level API migration.")
        seen_kinds.add(v["version"])

    # Option 3: the FIRST version of the new era (entry point across the boundary),
    # if the customer is currently legacy. This is the "do the architecture jump,
    # but to its baseline, then upgrade further later" staged option.
    if cur_era == "legacy":
        unified = [v for v in newer if v["major"] >= boundary]
        unified.sort(key=lambda v: semver.key(v["version"]))
        if unified and unified[0]["version"] not in seen_kinds:
            v = unified[0]
            add(v, "First unified release (staged architecture jump)",
                "Minimal version that crosses to the new SFMCSdk architecture. Useful if you want to stage the migration: cross the boundary now, climb to latest later.")
            seen_kinds.add(v["version"])

    # Option 4: next major after current, if it's an intermediate step not already listed.
    next_major_versions = [v for v in newer if v["major"] == cur_major + 1]
    if next_major_versions and next_major_versions[-1]["version"] not in seen_kinds:
        v = next_major_versions[-1]
        add(v, f"Next major ({v['major']}.x)",
            "One major step up — a moderate, incremental upgrade.")
        seen_kinds.add(v["version"])

    # Sort options by version ascending for a natural "small -> big jump" menu.
    options.sort(key=lambda o: semver.key(o["version"]))

    out = {
        "platform": args.platform,
        "catalogPath": path,
        "currentVersion": args.current,
        "currentEra": cur_era,
        "eraBoundaryMajor": boundary,
        "latestStable": latest["version"],
        "alreadyCurrent": False,
        "resolvedTarget": args.target,          # concrete version if one was requested, else null
        "targetResolutionNote": target_resolution_note,
        "options": options,
        "migrationGuides": catalog.get("migrationGuides", {}),
    }
    print(json.dumps(out, indent=2))

    if not args.json:
        print("", file=sys.stderr)
        print(f"=== Upgrade targets from {args.current} ({cur_era}) ===", file=sys.stderr)
        if target_resolution_note:
            print(f"  {target_resolution_note}", file=sys.stderr)
        for o in options:
            tag = "ARCH JUMP (full code migration)" if o["crossesArchitectureBoundary"] else "version/config bump"
            star = " ← resolved target" if args.target and o["version"] == args.target else ""
            print(f"  • {o['version']:<8} [{tag}] — {o['label']}{star}", file=sys.stderr)


if __name__ == "__main__":
    main()
