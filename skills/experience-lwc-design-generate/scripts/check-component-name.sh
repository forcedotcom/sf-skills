#!/usr/bin/env bash
# Validates that the two names an LWC bundle requires are in the correct
# case conventions and are consistent with each other:
#
#   componentName — camelCase (e.g. `productCard`)
#   tagName       — kebab-case (e.g. `product-card`)
#
# Also verifies the kebab-case form of `componentName` equals `tagName`,
# so `productCard` / `product-card` passes but `productCard` /
# `productcard` (missing dash) does not.
#
# Usage:
#   <skill_dir>/scripts/check-component-name.sh <componentName> <tagName>
#
# Exit codes:
#   0 — both names conform to their conventions and are consistent
#   1 — validation failure (message on stderr describing which rule failed)
#   2 — usage error

set -euo pipefail

fail() {
  echo "check-component-name: $*" >&2
  exit 1
}

if [ "$#" -ne 2 ]; then
  echo "usage: $0 <componentName> <tagName>" >&2
  exit 2
fi

component_name="$1"
tag_name="$2"

python3 - "$component_name" "$tag_name" <<'PY'
import re
import sys

component_name, tag_name = sys.argv[1], sys.argv[2]

CAMEL_RE = re.compile(r"^[a-z][a-zA-Z0-9]*$")
KEBAB_RE = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)+$")

errors = []

if not CAMEL_RE.match(component_name):
    errors.append(
        f"componentName `{component_name}` is not camelCase — must start with a "
        "lowercase letter and contain only letters/digits (e.g. `productCard`)."
    )

if not KEBAB_RE.match(tag_name):
    errors.append(
        f"tagName `{tag_name}` is not kebab-case — must start with a lowercase "
        "letter and contain at least one `-` separator with lowercase segments "
        "(e.g. `product-card`)."
    )

if not errors:
    # componentName -> expected kebab-case: insert `-` before each interior
    # uppercase letter and lowercase everything.
    expected = re.sub(r"([A-Z])", r"-\1", component_name).lower()
    if expected != tag_name:
        errors.append(
            f"tagName `{tag_name}` does not match componentName `{component_name}` "
            f"— expected kebab-case form `{expected}`."
        )

if errors:
    for e in errors:
        print(f"check-component-name: {e}", file=sys.stderr)
    sys.exit(1)

print(f"check-component-name: OK ({component_name} / {tag_name})")
PY
