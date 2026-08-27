#!/usr/bin/env bash
# Detect the data-import plan that gates Step 7 (data import).
#
# Prints the path of the single `data-plan.json` and exits 0 when exactly one
# exists; exits non-zero (with a message on stderr) when none exists — the
# signal to skip the data step cleanly. The file is located recursively, so
# both a project-root `data/` layout and a `<packageDir>/main/default/data/`
# layout resolve. build/dependency dirs are pruned so a vendored copy never
# produces a false positive.
#
# Usage: scripts/find-data-plan.sh [search-dir]
#   search-dir defaults to the current directory.
set -euo pipefail

search_dir="${1:-.}"

if [[ ! -d "$search_dir" ]]; then
  echo "find-data-plan: '$search_dir' is not a directory" >&2
  exit 1
fi

# Collect matches (null-delimited), pruning node_modules/dist/.git.
matches=()
while IFS= read -r -d '' f; do
  matches+=("$f")
done < <(find "$search_dir" \
  \( -type d \( -name node_modules -o -name dist -o -name .git \) -prune \) -o \
  \( -type f -name 'data-plan.json' -print0 \))

count="${#matches[@]}"
if (( count == 0 )); then
  echo "find-data-plan: no data-plan.json under '$search_dir' — skip the data step" >&2
  exit 1
fi
if (( count > 1 )); then
  echo "find-data-plan: found $count data-plan.json files (expected one):" >&2
  printf '  %s\n' "${matches[@]}" >&2
  exit 1
fi

echo "${matches[0]}"
