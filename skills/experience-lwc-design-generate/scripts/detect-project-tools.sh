#!/usr/bin/env bash
# Reports which of the Phase-4 lint/format/compile tools are configured
# in the target project. Emits one `<tool>=yes|no` line per checked tool
# on stdout so the caller can gate each Phase-4 substep deterministically
# instead of parsing prose.
#
# Detected tools:
#   eslint       — .eslintrc.* / eslint.config.* / package.json `eslintConfig`
#   prettier     — .prettierrc* / prettier.config.* / package.json `prettier`
#   cursor-rules — .cursor/rules/ or .cursorrules
#   lwc-compiler — sfdx-project.json or @lwc/compiler in package.json dependencies
#
# Usage:
#   <skill_dir>/scripts/detect-project-tools.sh [<projectRoot>]
#
# `<projectRoot>` defaults to the current working directory.
#
# Exit codes:
#   0 — detection completed (output on stdout is authoritative)
#   2 — usage error

set -euo pipefail

if [ "$#" -gt 1 ]; then
  echo "usage: $0 [<projectRoot>]" >&2
  exit 2
fi

root="${1:-.}"

if [ ! -d "$root" ]; then
  echo "detect-project-tools: project root \`$root\` does not exist" >&2
  exit 2
fi

python3 - "$root" <<'PY'
import json
import os
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()

def has_any(patterns):
    for p in patterns:
        # Interpret `*` as a shell-style glob relative to `root`.
        matches = list(root.glob(p))
        if matches:
            return True
    return False

def has_pkg_key(key):
    pkg = root / "package.json"
    if not pkg.is_file():
        return False
    try:
        data = json.loads(pkg.read_text(encoding="utf-8"))
    except Exception:
        return False
    if key in data:
        return True
    deps = {}
    for section in ("dependencies", "devDependencies", "peerDependencies"):
        d = data.get(section) or {}
        if isinstance(d, dict):
            deps.update(d)
    return key in deps

def yn(cond):
    return "yes" if cond else "no"

eslint = has_any([
    ".eslintrc",
    ".eslintrc.*",
    "eslint.config.*",
]) or has_pkg_key("eslintConfig")

prettier = has_any([
    ".prettierrc",
    ".prettierrc.*",
    "prettier.config.*",
]) or has_pkg_key("prettier")

cursor_rules = has_any([
    ".cursor/rules",
    ".cursorrules",
])

lwc_compiler = has_any([
    "sfdx-project.json",
]) or has_pkg_key("@lwc/compiler")

print(f"eslint={yn(eslint)}")
print(f"prettier={yn(prettier)}")
print(f"cursor-rules={yn(cursor_rules)}")
print(f"lwc-compiler={yn(lwc_compiler)}")
PY
