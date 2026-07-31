#!/usr/bin/env bash
# Detect the optional data-import prep script for Step 7.
#
# Prints the path of `prepare-import-unique-fields.js` and exits 0 when one
# exists; exits non-zero (silently) when absent — the signal that there is no
# prep step to run. The file is located recursively so both a `data/`-dir copy
# and a top-level `scripts/`-dir copy resolve; build/dependency dirs are pruned
# so a vendored copy never produces a false positive. If more than one exists
# the first is printed (either copy is a valid prep script; the caller reads its
# header to pick the right invocation — see references/data-import.md).
#
# Usage: scripts/find-prep-script.sh [search-dir]
#   search-dir defaults to the current directory.
set -euo pipefail

search_dir="${1:-.}"

if [[ ! -d "$search_dir" ]]; then
  echo "find-prep-script: '$search_dir' is not a directory" >&2
  exit 1
fi

found=""
while IFS= read -r -d '' f; do
  found="$f"
  break
done < <(find "$search_dir" \
  \( -type d \( -name node_modules -o -name dist -o -name .git \) -prune \) -o \
  \( -type f -name 'prepare-import-unique-fields.js' -print0 \))

if [[ -z "$found" ]]; then
  exit 1
fi

echo "$found"
