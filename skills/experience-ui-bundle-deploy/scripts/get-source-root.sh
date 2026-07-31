#!/usr/bin/env bash
# Resolve the metadata source directory from sfdx-project.json.
#
# Prints "<packageDirectories[0].path>/main/default" (the dir the deploy and
# metadata-discovery steps use) and exits 0. Exits non-zero with a message on
# stderr when the project file is missing or malformed, so callers never fall
# back to a hardcoded force-app/main/default.
#
# Usage: scripts/get-source-root.sh [project-dir]
#   project-dir defaults to the current directory.
set -euo pipefail

project_dir="${1:-.}"
project_file="$project_dir/sfdx-project.json"

if [[ ! -f "$project_file" ]]; then
  echo "get-source-root: no sfdx-project.json in '$project_dir'" >&2
  exit 1
fi

path="$(jq -r '.packageDirectories[0].path // empty' "$project_file")"
if [[ -z "$path" ]]; then
  echo "get-source-root: packageDirectories[0].path is missing or empty in $project_file" >&2
  exit 1
fi

# Strip any trailing slash, then append the fixed metadata subpath.
path="${path%/}"
echo "$path/main/default"
