#!/usr/bin/env python3
"""Validate a DsarPolicy tree against the hard caps before authoring metadata.

Checks (exits non-zero on the FIRST violation, printing it):
  - children per path <= 10
  - tree depth        <= 10   (a root path is depth 1)
  - total nodes       <= 200  (roots + every descendant path)
  - every developerName matches  [a-zA-Z]+[a-zA-Z0-9_]*

Input: a JSON file describing the tree. Shape (see references/configure.md):

  {
    "developerName": "CustomerPortability",
    "roots": [
      {
        "developerName": "ContactRoot",
        "object": "Contact",
        "fields": ["FirstName", "Email"],
        "children": [
          { "developerName": "ContactCases", "relationship": "Cases",
            "object": "Case", "fields": ["Subject"], "children": [] }
        ]
      }
    ]
  }

Usage:  python3 validate-policy-tree.py <tree.json>
"""

import json
import re
import sys

MAX_CHILDREN = 10
MAX_DEPTH = 10
MAX_NODES = 200
# \A ... \Z (not ^ ... $): $ also matches just before a trailing "\n", so a
# developerName like "Foo\n" would slip through .match(). \Z anchors the true
# end of the string and rejects any trailing newline.
NAME_RE = re.compile(r"\A[a-zA-Z]+[a-zA-Z0-9_]*\Z")


class TreeError(Exception):
    pass


def check_name(name, where):
    if not isinstance(name, str) or not name:
        raise TreeError(f"{where}: developerName is missing or not a string")
    if not NAME_RE.match(name):
        raise TreeError(
            f"{where}: developerName {name!r} does not match [a-zA-Z]+[a-zA-Z0-9_]*"
        )


def walk(node, depth, path):
    """Return the node count for this subtree; raise on the first violation."""
    where = f"{path}"
    check_name(node.get("developerName"), where)

    if depth > MAX_DEPTH:
        raise TreeError(
            f"{where}: depth {depth} exceeds the {MAX_DEPTH}-level cap"
        )

    children = node.get("children") or []
    if not isinstance(children, list):
        raise TreeError(f"{where}: 'children' must be a list")
    if len(children) > MAX_CHILDREN:
        raise TreeError(
            f"{where}: {len(children)} children exceeds the {MAX_CHILDREN}-per-path cap"
        )

    count = 1
    for i, child in enumerate(children):
        child_name = child.get("developerName", f"[{i}]") if isinstance(child, dict) else f"[{i}]"
        if not isinstance(child, dict):
            raise TreeError(f"{where} > child {i}: not an object")
        count += walk(child, depth + 1, f"{path} > {child_name}")
    return count


def validate(tree):
    if not isinstance(tree, dict):
        raise TreeError("top-level JSON must be an object")
    check_name(tree.get("developerName"), "DsarPolicy")

    roots = tree.get("roots")
    if not isinstance(roots, list) or not roots:
        raise TreeError("'roots' must be a non-empty list of root paths")

    total = 0
    for i, root in enumerate(roots):
        if not isinstance(root, dict):
            raise TreeError(f"roots[{i}]: not an object")
        root_name = root.get("developerName", f"[{i}]")
        total += walk(root, 1, f"{root_name}")

    if total > MAX_NODES:
        raise TreeError(f"total nodes {total} exceeds the {MAX_NODES}-node cap")

    return total


def main(argv):
    if len(argv) != 2:
        print(f"usage: {argv[0]} <tree.json>", file=sys.stderr)
        return 2
    try:
        with open(argv[1], "r", encoding="utf-8") as fh:
            tree = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"error: cannot read/parse {argv[1]}: {exc}", file=sys.stderr)
        return 2

    try:
        total = validate(tree)
    except TreeError as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 1

    print(
        f"OK: tree valid — {total} node(s), within caps "
        f"(<= {MAX_CHILDREN} children/path, depth <= {MAX_DEPTH}, <= {MAX_NODES} nodes)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
