#!/usr/bin/env bash
#
# detect-framework.sh — deterministic UI Bundle framework detector.
#
# Usage: bash detect-framework.sh [ROOT]
#   ROOT  app or uiBundle root to inspect (default: current directory)
#
# Prints exactly one of the following tokens to stdout, nothing else:
#   react      — React signals only
#   angular    — Angular signals only
#   ambiguous  — both React and Angular signals present
#   unknown    — neither framework detected
#
# Step 0 of the skill calls this and only asks the user which framework to use
# when the result is `ambiguous` or `unknown`.

set -u

ROOT="${1:-.}"
angular=0
react=0

# Resolve ROOT to an absolute path when possible (for the angular.json walk-up).
abs_root="$(cd "$ROOT" 2>/dev/null && pwd || true)"

# 1) angular.json at or above ROOT → Angular workspace.
dir="$abs_root"
while [ -n "$dir" ]; do
  [ -f "$dir/angular.json" ] && angular=1
  [ "$dir" = "/" ] && break
  dir="$(dirname "$dir")"
done

# 2) package.json dependencies (excluding node_modules).
while IFS= read -r pkg; do
  [ -z "$pkg" ] && continue
  grep -q '"@angular/core"' "$pkg" 2>/dev/null && angular=1
  grep -Eq '"react"[[:space:]]*:' "$pkg" 2>/dev/null && react=1
done <<EOF
$(find "$ROOT" -type d -name node_modules -prune -o -type f -name package.json -print 2>/dev/null)
EOF

# 3) Source-file signatures (excluding node_modules).
has_file() {
  find "$ROOT" -type d -name node_modules -prune -o -type f -name "$1" -print 2>/dev/null | grep -q .
}

# Angular: component files, routing module, or @Component-decorated classes.
has_file '*.component.ts' && angular=1
has_file 'app.routes.ts' && angular=1
if grep -rls --exclude-dir=node_modules --include='*.ts' '@Component' "$ROOT" 2>/dev/null | grep -q .; then
  angular=1
fi

# React: JSX/TSX source files.
has_file '*.tsx' && react=1
has_file '*.jsx' && react=1

if [ "$angular" -eq 1 ] && [ "$react" -eq 1 ]; then
  echo ambiguous
elif [ "$angular" -eq 1 ]; then
  echo angular
elif [ "$react" -eq 1 ]; then
  echo react
else
  echo unknown
fi
