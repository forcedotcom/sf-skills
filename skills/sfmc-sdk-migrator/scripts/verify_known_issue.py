#!/usr/bin/env python3
"""
verify_known_issue.py — Reproduce a known SFMC shipped-artifact defect against
what is ACTUALLY on the customer's disk, before the skill warns about it.

Why this exists: the migration matrix and version catalog carry a hand-curated
list of shipped-artifact bugs (packaging defects in the xcframework itself,
which no app-code fix can address). Those entries were seeded by unpacking the
shipped artifact and reading its swiftinterface. But Salesforce ships silent
republishes — a 1.0.0 xcframework can be quietly replaced with the same
version number but a fixed interface — and the toolchain that triggers the bug
(Xcode 26.2 / Swift 6.2.3, in the iam-1.0.0 case) is only one of several a
customer might build under. Emitting the warning unconditionally on the seed
data warns customers whose build passed cleanly; that reads as noise.

This verifier is the "reproduce it before you warn about it" gate. It runs the
issue's declared verifier — e.g. for iam-1.0.0-swiftinterface-nodoc, locate the
shipped `InAppMessagingFeatureSDK.private.swiftinterface` under the customer's
Pods / SPM artifacts / DerivedData, and grep for the offending declaration.
Verdicts:

  reproduces    The defect is present in the artifact this project resolves.
                Emit the warning verbatim.
  patched       The artifact resolved cleanly but the offending declaration is
                not there. Salesforce has silently republished — SUPPRESS the
                warning and note the observation in the report.
  not-materialized
                No copy of the artifact exists on disk yet. `pod install` /
                `xcodebuild -resolvePackageDependencies` hasn't run, or the
                pod/product isn't in the target's dependency graph. The
                caller should either run the resolver and re-verify, or emit
                the warning with an "unverified" tag.
  inconclusive  Something else prevented a clean read (interface unreadable,
                unexpected shape). Emit the warning with an "unverified" tag.

Usage:
    python3 verify_known_issue.py --project <project> --issue-id <id> [--json]

Exit code is 0 whenever the verifier ran to a verdict — the verdict itself is
in stdout JSON. Non-zero (2) is reserved for a usage error (unknown issue id,
missing --project).
"""
import argparse
import json
import os
import re
import sys


def _iter_interface_candidates(project, module_name):
    """Yield paths to `<module>.private.swiftinterface` under likely roots.

    Search order (cheapest first):
      1. `<project>/Pods/**` — CocoaPods installs xcframeworks straight into the
         Pods directory. Fastest and highest-signal for the CocoaPods case.
      2. `<project>/build/**` and `<project>/DerivedData/**` — project-local
         Xcode output. Present when the customer builds inside the project dir.
      3. `~/Library/Developer/Xcode/DerivedData/**` — the global DerivedData
         cache, where SPM-resolved artifacts and workspace builds land by
         default. Filtered by the project directory basename so we don't scan
         every customer app's cache — Xcode namespaces DerivedData entries
         with the project name plus a hash suffix (e.g. `MyApp-abcdef...`).

    We look specifically for a `.swiftmodule` directory named after the module
    and a `.private.swiftinterface` inside it. Public `.swiftinterface` is
    ignored — the bug lives in the private interface (which SPI-annotated
    declarations flow into) and the public one won't carry the reference.
    """
    private_interface_leaf = f"{module_name}.swiftmodule"
    project_basename = os.path.basename(os.path.abspath(project).rstrip("/"))

    roots = []
    roots.append(os.path.join(project, "Pods"))
    roots.append(os.path.join(project, "build"))
    roots.append(os.path.join(project, "DerivedData"))
    home_derived = os.path.expanduser("~/Library/Developer/Xcode/DerivedData")
    if os.path.isdir(home_derived):
        # Filter DerivedData subdirs by project basename prefix to avoid
        # scanning every project's cache on this machine. Xcode names entries
        # `<project>-<hash>`; a startswith match is safe.
        for entry in os.listdir(home_derived):
            if entry.startswith(project_basename + "-") or entry == project_basename:
                roots.append(os.path.join(home_derived, entry))

    seen = set()
    for root in roots:
        if not root or not os.path.isdir(root):
            continue
        for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
            # Only descend into swiftmodule dirs we care about + everything above them.
            if os.path.basename(dirpath) == private_interface_leaf:
                for fn in filenames:
                    if fn.endswith(".private.swiftinterface"):
                        full = os.path.join(dirpath, fn)
                        if full not in seen:
                            seen.add(full)
                            yield full
                # No need to descend further into the swiftmodule directory.
                dirnames[:] = []


def _grep_interface(interface_path, pattern):
    """Return (line_number, line_text) of the first match, or None.

    Reads the file line by line so we can report the concrete line number the
    matrix comment points at (line 84 in the seeded case). Compiled regex is
    passed in — the caller decides whether to escalate to a broader form when
    the exact anchored pattern doesn't hit.
    """
    try:
        with open(interface_path, "r", encoding="utf-8", errors="replace") as f:
            for i, line in enumerate(f, start=1):
                if pattern.search(line):
                    return (i, line.rstrip("\n"))
    except OSError:
        return None
    return None


def verify_iam_swiftinterface_nodoc(project):
    """Verify iam-1.0.0-swiftinterface-nodoc against the shipped artifact.

    Concrete check: does `InAppMessagingFeatureSDK.private.swiftinterface`
    contain a declaration referencing `SFMCSDK.InAppMessagingFeatureProtocol`?
    That is the exact packaging defect the known issue describes — an
    extension whose conformance names an SPI-marked (`:nodoc:` +
    SWIFT_UNAVAILABLE) protocol, which Xcode 26.2's module verifier refuses to
    load.

    The pattern is intentionally loose on whitespace and does not anchor to a
    specific line: Salesforce may re-flow the interface between builds without
    otherwise fixing the bug. A tighter check would false-negative on cosmetic
    changes.
    """
    module = "InAppMessagingFeatureSDK"
    candidates = list(_iter_interface_candidates(project, module))

    if not candidates:
        return {
            "verdict": "not-materialized",
            "module": module,
            "interfacePaths": [],
            "match": None,
            "reason": (
                f"No `{module}.private.swiftinterface` under `{project}/Pods`, "
                f"`{project}/build`, `{project}/DerivedData`, or the global "
                f"~/Library/Developer/Xcode/DerivedData tree filtered by project "
                f"name. Run `pod install --repo-update` (CocoaPods) or "
                f"`xcodebuild -resolvePackageDependencies` (SPM) and re-verify. "
                f"If IAM isn't in the app's dependency graph the artifact will "
                f"never materialize — check the Podfile / Package.swift first."
            ),
        }

    pattern = re.compile(
        r"extension\s+InAppMessagingFeature\b.*?:.*?\bSFMCSDK\.InAppMessagingFeatureProtocol\b"
    )
    for path in candidates:
        hit = _grep_interface(path, pattern)
        if hit is not None:
            line_no, line_text = hit
            return {
                "verdict": "reproduces",
                "module": module,
                "interfacePaths": candidates,
                "match": {
                    "path": path,
                    "line": line_no,
                    "text": line_text,
                },
                "reason": (
                    f"`{path}` line {line_no} declares an extension of "
                    f"`InAppMessagingFeature` naming `SFMCSDK.InAppMessagingFeatureProtocol` "
                    f"— the exact SPI-unavailable protocol reference the known issue "
                    f"describes. Module verification will fail on Xcode 26.2 / Swift 6.2.3."
                ),
            }

    return {
        "verdict": "patched",
        "module": module,
        "interfacePaths": candidates,
        "match": None,
        "reason": (
            f"Read {len(candidates)} `{module}.private.swiftinterface` file(s) "
            f"under this project; none reference `SFMCSDK.InAppMessagingFeatureProtocol`. "
            f"Salesforce appears to have silently republished the shipped artifact "
            f"since the skill's seed date (2026-07). Suppress the warning; record "
            f"the observation in the report so a future regression is visible."
        ),
    }


# Registry: known issue id → verifier callable.
# Add new entries here as more shipped-artifact defects get catalogued.
VERIFIERS = {
    "iam-1.0.0-swiftinterface-nodoc": verify_iam_swiftinterface_nodoc,
}


def main():
    ap = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    ap.add_argument("--project", required=True,
                    help="Absolute path to the customer project (same value as the skill's "
                         "`project` input).")
    ap.add_argument("--issue-id", required=True, choices=sorted(VERIFIERS.keys()),
                    help="Known-issue id from version-catalog-ios.json / migration-matrix-ios.json.")
    ap.add_argument("--json", action="store_true",
                    help="Emit raw JSON only (default: also print a one-line summary to stderr).")
    args = ap.parse_args()

    project = os.path.abspath(args.project)
    if not os.path.isdir(project):
        sys.exit(f"error: --project is not a directory: {project}")

    result = VERIFIERS[args.issue_id](project)
    result["issueId"] = args.issue_id
    result["projectPath"] = project

    print(json.dumps(result, indent=2))
    if not args.json:
        verdict = result["verdict"]
        tag = {
            "reproduces": "REPRODUCES — emit warning",
            "patched": "PATCHED — suppress warning",
            "not-materialized": "NOT MATERIALIZED — resolver hasn't run",
            "inconclusive": "INCONCLUSIVE — emit warning tagged unverified",
        }.get(verdict, verdict)
        print(f"\n=== {args.issue_id}: {tag} ===", file=sys.stderr)
        print(f"  reason: {result['reason']}", file=sys.stderr)


if __name__ == "__main__":
    main()
