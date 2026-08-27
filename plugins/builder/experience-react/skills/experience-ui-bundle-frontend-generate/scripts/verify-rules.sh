#!/usr/bin/env bash
# Grep-based verification of the hard, checkable rules in this skill that
# `npm run lint` / `npm run build` do not catch on their own — a wrong
# react-router-dom import, a hardcoded basename, an inline style prop, a
# stray lightning/*-or-@wire import, or leftover template boilerplate can
# all lint and build clean while breaking at runtime or shipping unfinished
# branding.
#
# Usage: verify-rules.sh <file-or-dir> [<file-or-dir> ...]
#   Pass the specific files you edited, or the bundle's src/ directory (and
#   its index.html) to check everything.
#
# Exit 0 if no violations are found.
# Exit 1 with every violation listed (rule + matching file paths) if any
# are found — fix them before considering the task complete, even if lint
# and build passed.

set -uo pipefail

if [ "$#" -eq 0 ]; then
  echo "ERROR: verify-rules.sh requires at least one file or directory argument" >&2
  exit 1
fi

for p in "$@"; do
  if [ ! -e "$p" ]; then
    echo "ERROR: path does not exist: $p" >&2
    exit 1
  fi
done

FOUND=0

check() {
  label="$1"
  pattern="$2"
  shift 2
  hits=$(grep -rlE --include='*.ts' --include='*.tsx' --include='*.js' --include='*.jsx' --include='*.html' \
    --exclude-dir=node_modules --exclude-dir=dist --exclude-dir=build -- "$pattern" "$@" 2>/dev/null || true)
  if [ -n "$hits" ]; then
    echo "ERROR: $label found in:" >&2
    echo "$hits" | sed 's/^/  - /' >&2
    FOUND=1
  fi
}

check 'import from "react-router-dom" (must be "react-router")' 'from[[:space:]]+['"'"'"]react-router-dom['"'"'"]' "$@"
check 'a hardcoded basename literal (must derive from <base href> at runtime)' 'basename:[[:space:]]*['"'"'"][/A-Za-z0-9_-]+['"'"'"]' "$@"
check 'an inline style={{...}} prop (Tailwind utility classes only)' 'style=\{\{' "$@"
check 'a forbidden lightning/* import or @wire usage (LWC-only)' 'from[[:space:]]+['"'"'"]lightning/|@wire' "$@"
check 'leftover boilerplate branding (<title>React App</title> / Vite + React)' '<title>[^<]*React App[^<]*</title>|Vite[[:space:]]*\+[[:space:]]*React' "$@"

if [ "$FOUND" -eq 1 ]; then
  exit 1
fi

echo "SUCCESS: No hard-rule violations found in: $*"
exit 0
