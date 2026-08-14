#!/usr/bin/env bash
# Resolve the package directory that actually owns a UI Bundle.
#
# Given a bundle name, walk sfdx-project.json's `packageDirectories` array and
# print the `path` of the entry whose tree contains `uiBundles/<bundle-name>/`
# on disk. This is what the skill's `<packageDir>` token substitutes to.
#
# Why this exists: `packageDirectories[0]` is only correct when the project
# has a single package directory. Multi-package projects can put the bundle
# under any entry, so writing metadata (CustomApplication, PermissionSet) into
# `[0]` blindly can land it *outside* the package being versioned, and the
# installed package will then be missing the intended wiring.
#
# Usage: scripts/find-bundle-package-dir.sh <bundleName> [project-dir]
#   project-dir defaults to the current directory.
#
# Exit 0: prints the matching `path` (no trailing slash) on stdout.
# Exit 1: no sfdx-project.json / malformed / no entry contains the bundle.
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "find-bundle-package-dir: usage: $0 <bundleName> [project-dir]" >&2
  exit 1
fi

bundle="$1"
project_dir="${2:-.}"
project_file="$project_dir/sfdx-project.json"

if [[ ! -f "$project_file" ]]; then
  echo "find-bundle-package-dir: no sfdx-project.json in '$project_dir'" >&2
  exit 1
fi

# Match anywhere under each packageDir tree, not just the fixed
# force-app/main/default layout — the bundle may live under any depth.
# Read paths one-at-a-time (portable to bash 3.2 on macOS).
found=""
while IFS= read -r raw; do
  [[ -z "$raw" ]] && continue
  path="${raw%/}"
  if [[ -d "$project_dir/$path" ]] && find "$project_dir/$path" -type d -path "*/uiBundles/$bundle" -print -quit 2>/dev/null | grep -q .; then
    found="$path"
    break
  fi
done < <(jq -r '.packageDirectories[]?.path // empty' "$project_file")

if [[ -z "$found" ]]; then
  echo "find-bundle-package-dir: no packageDirectories entry contains 'uiBundles/$bundle' — check the bundle name and sfdx-project.json paths" >&2
  exit 1
fi

echo "$found"
