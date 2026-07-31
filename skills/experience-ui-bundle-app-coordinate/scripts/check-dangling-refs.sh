#!/usr/bin/env bash
# Verify no surviving file still imports/references a file deleted during scaffold pruning
# Usage: check-dangling-refs.sh <deleted-basename> [<deleted-basename> ...]
#   <deleted-basename> is the file name without extension, e.g. "codegen" for codegen.yml,
#   "graphqlClient" for src/api/graphqlClient.ts, "useAsyncData" for the deleted hook.
# Exit 0 if no dangling references found, exit 1 with error message(s) if any are found.

set -e

if [ "$#" -eq 0 ]; then
  echo "ERROR: check-dangling-refs.sh requires at least one deleted-file basename as an argument"
  exit 1
fi

BUNDLE_DIR=$(find force-app/main/default/uiBundles -mindepth 1 -maxdepth 1 -type d 2>/dev/null | head -1)

if [ -z "$BUNDLE_DIR" ]; then
  echo "ERROR: No UI bundle directory found in force-app/main/default/uiBundles/"
  exit 1
fi

FOUND_DANGLING=0

for basename in "$@"; do
  # Search all tracked source/config files (excluding node_modules, dist, build) for the
  # basename — catches imports, requires, and config references (e.g. codegen.yml paths).
  MATCHES=$(grep -rlF --exclude-dir=node_modules --exclude-dir=dist --exclude-dir=build \
    --exclude-dir=.git -- "$basename" "$BUNDLE_DIR" 2>/dev/null || true)

  if [ -n "$MATCHES" ]; then
    echo "ERROR: Dangling reference to deleted file '$basename' found in:"
    echo "$MATCHES" | sed 's/^/  - /'
    FOUND_DANGLING=1
  fi
done

if [ "$FOUND_DANGLING" -eq 1 ]; then
  exit 1
fi

echo "SUCCESS: No dangling references found for: $*"
exit 0
