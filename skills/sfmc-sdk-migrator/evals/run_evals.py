#!/usr/bin/env python3
"""Network-free eval runner for the sfmc-sdk-migrator skill.

Runs the two detection scripts (scan_usage.py, target_options.py) against the
fixture repos under evals/inputs/ and checks the `deterministic` assertions in
evals/evals.json. No network, no LLM, no build tools — safe for CI.

The `llm_graded` assertions describe rewrite-quality criteria that a grader (a
human or an LLM) applies to the skill's *output*. This runner can't grade prose,
but when you point it at a migrated output tree it evaluates each such
assertion's `staticChecks` (mustContain / mustNotContain / regex) deterministi-
cally as a cheap proxy, and always prints the rubric so a grader has the spec.

Usage:
    # Deterministic tier only (CI): run every eval's detection assertions.
    python3 evals/run_evals.py

    # One eval, verbose (prints llm_graded rubrics too).
    python3 evals/run_evals.py --eval 0 --verbose

    # Grade a migrated output tree's static checks for eval 0. PATH is the root
    # of the skill's output (mirrors the fixture layout, e.g. a copy of
    # inputs/repo-full-android after the skill rewrote it).
    python3 evals/run_evals.py --with-skill 0=/tmp/out/repo-full-android

    # Machine-readable results.
    python3 evals/run_evals.py --json

Exit code: 0 if every checked assertion passed; 1 if any FAILED. llm_graded
assertions with no static checks (and no --with-skill tree) are SKIPPED and do
not affect the exit code.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys

EVALS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(EVALS_DIR)
SCAN_USAGE = os.path.join(REPO_ROOT, "scripts", "scan_usage.py")
TARGET_OPTIONS = os.path.join(REPO_ROOT, "scripts", "target_options.py")
EVALS_JSON = os.path.join(EVALS_DIR, "evals.json")

# Result statuses.
PASS = "PASS"
FAIL = "FAIL"
SKIP = "SKIP"


# --------------------------------------------------------------------------- #
# Path DSL
# --------------------------------------------------------------------------- #
def split_path(path):
    """Split a dotted path into segments without breaking on dots inside [...].

    'options[?version=11.0.1].migrationKind' -> ['options[?version=11.0.1]',
    'migrationKind']. The version literal keeps its dots because we only split
    on top-level '.' (bracket depth 0).
    """
    segments = []
    buf = ""
    depth = 0
    for ch in path:
        if ch == "[":
            depth += 1
            buf += ch
        elif ch == "]":
            depth -= 1
            buf += ch
        elif ch == "." and depth == 0:
            segments.append(buf)
            buf = ""
        else:
            buf += ch
    if buf:
        segments.append(buf)
    return segments


_FILTER_RE = re.compile(r"^([^\[]+)\[\?([^=]+)=(.+)\]$")
_INDEX_RE = re.compile(r"^([^\[]+)\[(\d+)\]$")


def resolve_path(obj, path):
    """Resolve a path against a JSON object.

    Returns (found, value). `found` is False if any segment is missing so
    callers can distinguish 'absent' from 'present but null/false'.
    """
    cur = obj
    for seg in split_path(path):
        if cur is None:
            return (False, None)

        m = _FILTER_RE.match(seg)
        if m:  # name[?key=value] — first list element whose key matches value
            list_key, f_key, f_val = m.groups()
            lst = cur.get(list_key) if isinstance(cur, dict) else None
            if not isinstance(lst, list):
                return (False, None)
            match = next(
                (el for el in lst
                 if isinstance(el, dict) and str(el.get(f_key)) == f_val),
                None,
            )
            if match is None:
                return (False, None)
            cur = match
            continue

        m = _INDEX_RE.match(seg)
        if m:  # name[0] — positional list index
            list_key, idx = m.groups()
            lst = cur.get(list_key) if isinstance(cur, dict) else None
            if not isinstance(lst, list) or int(idx) >= len(lst):
                return (False, None)
            cur = lst[int(idx)]
            continue

        if isinstance(cur, dict) and seg in cur:  # plain key
            cur = cur[seg]
        else:
            return (False, None)

    return (True, cur)


# --------------------------------------------------------------------------- #
# Operators
# --------------------------------------------------------------------------- #
def _as_len(v):
    try:
        return len(v)
    except TypeError:
        return None


def apply_op(op, found, actual, expected):
    """Evaluate one operator. Returns (ok, detail-string).

    A path that wasn't found fails every operator — assertions are written
    against outputs we've confirmed exist, so 'absent' is always a real defect.
    """
    if not found:
        return (False, "path not found")

    try:
        if op == "eq":
            return (actual == expected, f"{actual!r} == {expected!r}")
        if op == "ne":
            return (actual != expected, f"{actual!r} != {expected!r}")
        if op == "gt":
            return (actual > expected, f"{actual!r} > {expected!r}")
        if op == "gte":
            return (actual >= expected, f"{actual!r} >= {expected!r}")
        if op == "lt":
            return (actual < expected, f"{actual!r} < {expected!r}")
        if op == "lte":
            return (actual <= expected, f"{actual!r} <= {expected!r}")
        if op == "isTrue":
            return (actual is True, f"{actual!r} is true")
        if op == "isFalse":
            return (actual is False, f"{actual!r} is false")
        if op == "isNull":
            return (actual is None, f"{actual!r} is null")
        if op == "contains":
            return (expected in actual, f"{expected!r} in {actual!r}")
        if op == "notContains":
            return (expected not in actual, f"{expected!r} not in {actual!r}")
        if op == "subset":
            return (set(expected) <= set(actual),
                    f"{expected!r} subset of {actual!r}")
        if op == "setEq":
            return (set(actual) == set(expected),
                    f"set({actual!r}) == set({expected!r})")
        if op == "in":
            return (actual in expected, f"{actual!r} in {expected!r}")
        if op == "hasKey":
            return (isinstance(actual, dict) and expected in actual,
                    f"key {expected!r} in {actual!r}")
        if op == "lengthEq":
            n = _as_len(actual)
            return (n == expected, f"len={n} == {expected}")
        if op == "lengthGte":
            n = _as_len(actual)
            return (n is not None and n >= expected, f"len={n} >= {expected}")
        if op == "regex":
            return (bool(re.search(expected, str(actual))),
                    f"{actual!r} =~ /{expected}/")
    except TypeError as e:
        return (False, f"type error: {e}")

    return (False, f"unknown op {op!r}")


# --------------------------------------------------------------------------- #
# Script invocation (cached per eval)
# --------------------------------------------------------------------------- #
def run_json_script(argv):
    """Run a script that emits JSON on stdout. Returns (exit_code, obj|None)."""
    proc = subprocess.run(
        [sys.executable, *argv],
        capture_output=True,
        text=True,
    )
    obj = None
    if proc.stdout.strip():
        try:
            obj = json.loads(proc.stdout)
        except json.JSONDecodeError:
            obj = None
    return (proc.returncode, obj, proc.stderr.strip())


class ToolCache:
    """Runs scan_usage/target_options at most once per (fixture, args)."""

    def __init__(self, fixture_path, platform="android"):
        self.fixture_path = fixture_path
        self.platform = platform
        self._scan = None
        self._targets = {}

    def scan(self):
        if self._scan is None:
            code, obj, err = run_json_script(
                [SCAN_USAGE, self.fixture_path, "--platform", self.platform, "--json"]
            )
            self._scan = (code, obj, err)
        return self._scan

    def target(self, current, target=None):
        key = (current, target)
        if key not in self._targets:
            argv = [TARGET_OPTIONS, "--current", str(current),
                    "--platform", self.platform]
            if target is not None:
                argv += ["--target", str(target)]
            argv.append("--json")
            self._targets[key] = run_json_script(argv)
        return self._targets[key]


# --------------------------------------------------------------------------- #
# Assertion evaluation
# --------------------------------------------------------------------------- #
def eval_deterministic(assertion, cache):
    """Evaluate one deterministic assertion. Returns (status, detail)."""
    tool = assertion.get("tool")
    check = assertion.get("check") or {}
    op = check.get("op")
    path = check.get("path")
    expected = check.get("value")

    if tool == "scan_usage":
        code, obj, err = cache.scan()
        if obj is None:
            return (FAIL, f"scan_usage produced no JSON (exit {code}): {err[:200]}")
        found, actual = resolve_path(obj, path)
        ok, detail = apply_op(op, found, actual, expected)
        return (PASS if ok else FAIL, f"{path}: {detail}")

    if tool == "target_options":
        # Resolve dynamic args (argsFrom pulls from the scan output).
        current = None
        args_from = assertion.get("argsFrom") or {}
        if "current" in args_from:
            code, scan_obj, err = cache.scan()
            if scan_obj is None:
                return (FAIL, f"scan_usage failed, can't resolve current: {err[:120]}")
            found, current = resolve_path(scan_obj, args_from["current"])
            if not found:
                return (FAIL, f"argsFrom current path {args_from['current']!r} not found")
        static_args = assertion.get("args") or {}
        target = static_args.get("target")

        code, obj, err = cache.target(current, target)
        if obj is None:
            return (FAIL, f"target_options produced no JSON (exit {code}): {err[:200]}")
        found, actual = resolve_path(obj, path)
        ok, detail = apply_op(op, found, actual, expected)
        return (PASS if ok else FAIL, f"{path}: {detail}")

    return (FAIL, f"unknown tool {tool!r}")


def eval_static_checks(assertion, skill_root):
    """Evaluate an llm_graded assertion's staticChecks against an output tree.

    Returns (status, detail). SKIP when there's nothing to check statically.
    """
    static = assertion.get("staticChecks")
    target = assertion.get("target")
    if not static or not target or target == "*":
        return (SKIP, "no static checks (needs LLM/response grading)")

    file_path = os.path.join(skill_root, target)
    if not os.path.isfile(file_path):
        return (FAIL, f"expected output file missing: {target}")

    with open(file_path, "r", encoding="utf-8", errors="replace") as fh:
        text = fh.read()

    failures = []
    for chk in static:
        if "mustContain" in chk and chk["mustContain"] not in text:
            failures.append(f"missing {chk['mustContain']!r}")
        if "mustNotContain" in chk and chk["mustNotContain"] in text:
            failures.append(f"unexpected {chk['mustNotContain']!r}")
        if "regex" in chk and not re.search(chk["regex"], text):
            failures.append(f"no match /{chk['regex']}/")
    if failures:
        return (FAIL, f"{target}: " + "; ".join(failures))
    return (PASS, f"{target}: {len(static)} static check(s) ok")


# --------------------------------------------------------------------------- #
# Runner
# --------------------------------------------------------------------------- #
def parse_with_skill(pairs):
    """Parse repeated --with-skill ID=PATH into {eval_id: path}."""
    mapping = {}
    for pair in pairs or []:
        if "=" not in pair:
            raise SystemExit(f"--with-skill expects ID=PATH, got {pair!r}")
        eid, path = pair.split("=", 1)
        mapping[int(eid)] = path
    return mapping


def run(args):
    with open(EVALS_JSON, "r", encoding="utf-8") as fh:
        spec = json.load(fh)

    with_skill = parse_with_skill(args.with_skill)
    results = []

    for eval_def in spec.get("evals", []):
        eid = eval_def.get("id")
        if args.eval is not None and eid != args.eval:
            continue

        files = eval_def.get("files") or []
        fixture_path = os.path.join(EVALS_DIR, files[0]) if files else None
        if not fixture_path or not os.path.isdir(fixture_path):
            results.append({
                "eval": eid, "name": eval_def.get("name"),
                "assertion": "(fixture)", "tier": "-", "status": FAIL,
                "detail": f"fixture dir not found: {files}",
            })
            continue

        cache = ToolCache(fixture_path, platform=eval_def.get("platform", "android"))
        skill_root = with_skill.get(eid)

        for a in eval_def.get("assertions", []):
            tier = a.get("tier")
            if tier == "deterministic":
                status, detail = eval_deterministic(a, cache)
            elif tier == "llm_graded":
                if skill_root:
                    status, detail = eval_static_checks(a, skill_root)
                else:
                    status, detail = (SKIP, "llm_graded (rubric only; pass --with-skill to check statics)")
            else:
                status, detail = (FAIL, f"unknown tier {tier!r}")

            results.append({
                "eval": eid, "name": eval_def.get("name"),
                "assertion": a.get("id"), "tier": tier,
                "status": status, "detail": detail,
                "rubric": a.get("rubric"), "description": a.get("description"),
            })

    return results


def print_human(results, verbose):
    icons = {PASS: "✓", FAIL: "✗", SKIP: "•"}
    counts = {PASS: 0, FAIL: 0, SKIP: 0}
    cur_eval = object()

    for r in results:
        if r["eval"] != cur_eval:
            cur_eval = r["eval"]
            print(f"\n── eval {r['eval']}: {r['name']} " + "─" * 24)
        counts[r["status"]] = counts.get(r["status"], 0) + 1
        icon = icons.get(r["status"], "?")
        print(f"  {icon} [{r['status']}] {r['assertion']}  ({r['tier']})")
        if r["status"] == FAIL or verbose:
            if r.get("description"):
                print(f"        {r['description']}")
            print(f"        → {r['detail']}")
        if verbose and r["tier"] == "llm_graded" and r.get("rubric"):
            print(f"        rubric: {r['rubric']}")

    total = sum(counts.values())
    print("\n" + "═" * 60)
    print(f"  {counts[PASS]} passed, {counts[FAIL]} failed, "
          f"{counts[SKIP]} skipped  ({total} assertions)")
    print("═" * 60)
    return counts[FAIL] == 0


def main():
    ap = argparse.ArgumentParser(description="Run sfmc-sdk-migrator evals (network-free).")
    ap.add_argument("--eval", type=int, help="Run only the eval with this id.")
    ap.add_argument("--with-skill", action="append", metavar="ID=PATH",
                    help="Grade static checks for eval ID against migrated output tree PATH. Repeatable.")
    ap.add_argument("--verbose", action="store_true",
                    help="Print details and llm_graded rubrics for every assertion.")
    ap.add_argument("--json", action="store_true", help="Emit results as JSON.")
    args = ap.parse_args()

    results = run(args)

    if args.json:
        n_fail = sum(1 for r in results if r["status"] == FAIL)
        print(json.dumps({
            "results": results,
            "summary": {
                "passed": sum(1 for r in results if r["status"] == PASS),
                "failed": n_fail,
                "skipped": sum(1 for r in results if r["status"] == SKIP),
            },
        }, indent=2))
        return 1 if n_fail else 0

    ok = print_human(results, args.verbose)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
