#!/usr/bin/env bash
# Resolve the single UI bundle directory for this project.
# Usage: resolve-ui-bundle.sh [project-root]   (default: current directory)
#
# Reads sfdx-project.json's packageDirectories[0].path, looks under
# <that-path>/main/default/uiBundles/, and prints the resolved bundle
# directory to stdout on success.
#
# Exit 0: exactly one bundle directory found — printed to stdout.
# Exit 1: sfdx-project.json missing/invalid, or no uiBundles/* subdirectory
#         found at all (not a scaffolded SFDX project yet).
# Exit 2: multiple uiBundles/* subdirectories found — caller MUST ask the
#         user which one they mean rather than guessing; candidate names are
#         printed to stderr.

set -uo pipefail

PROJECT_ROOT="${1:-.}"
SFDX_PROJECT="$PROJECT_ROOT/sfdx-project.json"

if [ ! -f "$SFDX_PROJECT" ]; then
  echo "ERROR: sfdx-project.json not found at $SFDX_PROJECT" >&2
  exit 1
fi

SOURCE_PATH=$(python3 -c "
import json, sys
try:
    with open('$SFDX_PROJECT') as f:
        data = json.load(f)
    dirs = data.get('packageDirectories', [])
    print(dirs[0].get('path', '') if dirs else '')
except Exception:
    print('')
" 2>/dev/null)

if [ -z "$SOURCE_PATH" ]; then
  echo "ERROR: sfdx-project.json is invalid or has no packageDirectories[0].path" >&2
  exit 1
fi

BUNDLES_DIR="$PROJECT_ROOT/$SOURCE_PATH/main/default/uiBundles"

if [ ! -d "$BUNDLES_DIR" ]; then
  echo "ERROR: No uiBundles/ directory found at $BUNDLES_DIR" >&2
  exit 1
fi

BUNDLE_DIRS=()
while IFS= read -r d; do
  BUNDLE_DIRS+=("$d")
done < <(find "$BUNDLES_DIR" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | sort)

if [ "${#BUNDLE_DIRS[@]}" -eq 0 ]; then
  echo "ERROR: $BUNDLES_DIR exists but contains no bundle subdirectories" >&2
  exit 1
fi

if [ "${#BUNDLE_DIRS[@]}" -gt 1 ]; then
  echo "AMBIGUOUS: Multiple UI bundle directories found — ask the user which one they mean before editing or running any command:" >&2
  printf '  - %s\n' "${BUNDLE_DIRS[@]}" >&2
  exit 2
fi

echo "${BUNDLE_DIRS[0]}"
exit 0
