#!/usr/bin/env bash
# derive-alias.sh — deterministic scratch-org alias derivation + collision guard.
#
# Slugifies a base name and guarantees the result does not collide with an
# existing alias. `sf org create scratch` does NOT reject a reused alias — it
# silently re-points the alias to the new org, so the old org loses its handle.
# This script guards against that by appending -2, -3, … until the alias is free.
#
# Usage:
#   derive-alias.sh <base-name> [<count>]
#
#   <base-name>  Raw name to slugify (e.g. a package-directory name or cwd
#                basename, or a user-supplied alias). Required.
#   <count>      Optional. When >1, emits <count> distinct collision-guarded
#                aliases (base-1 … base-N) for a batch create, one per line.
#                Omit or 1 → emit a single collision-guarded alias.
#
# Output: the final alias(es), one per line, to stdout. Nothing else.
#
# Determinism: given the same base name and the same set of existing aliases,
# the output is always identical. The only external input is `sf org list`,
# which reflects live org state (the collision set) — that is intentional.
set -euo pipefail

if [ "$#" -lt 1 ] || [ -z "${1:-}" ]; then
  echo "usage: derive-alias.sh <base-name> [<count>]" >&2
  exit 2
fi

base_raw="$1"
count="${2:-1}"

# Slugify: lowercase, non-alphanumerics → hyphens, collapse repeats, trim ends.
slugify() {
  printf '%s' "$1" \
    | tr '[:upper:]' '[:lower:]' \
    | sed -E 's/[^a-z0-9]+/-/g; s/-+/-/g; s/^-+//; s/-+$//'
}

base="$(slugify "$base_raw")"
if [ -z "$base" ]; then
  echo "error: base name '$base_raw' slugifies to empty; provide an explicit alias" >&2
  exit 3
fi

# Collect existing aliases once. Fail CLOSED: the collision guard is the whole
# point of this script, so if we cannot reliably read the existing alias set we
# must NOT proceed with an empty set (that would emit an alias that may already
# exist, and `sf org create scratch` silently re-points a reused alias to the
# new org). Require jq, and treat a failed `sf org list` as a hard error.
if ! command -v jq >/dev/null 2>&1; then
  echo "error: jq is required for the alias collision check but was not found on PATH" >&2
  exit 4
fi

org_list_json="$(sf org list --json 2>/dev/null)" || {
  echo "error: 'sf org list --json' failed; cannot verify alias collisions — refusing to derive an unguarded alias" >&2
  exit 5
}

existing="$(printf '%s' "$org_list_json" \
  | jq -r '[.result.scratchOrgs[]?, .result.nonScratchOrgs[]?, .result.other[]?]
           | .[]? | .alias // empty')" || {
  echo "error: could not parse 'sf org list --json' output; refusing to derive an unguarded alias" >&2
  exit 5
}

is_taken() {
  printf '%s\n' "$existing" | grep -Fxq "$1"
}

# Produce one collision-guarded alias from a candidate stem.
guarded() {
  local candidate="$1"
  if ! is_taken "$candidate"; then
    printf '%s\n' "$candidate"
    return
  fi
  local n=2
  while is_taken "${candidate}-${n}"; do
    n=$((n + 1))
  done
  printf '%s\n' "${candidate}-${n}"
}

if [ "$count" -le 1 ]; then
  guarded "$base"
else
  # Batch: base-1 … base-N, each independently collision-guarded.
  i=1
  while [ "$i" -le "$count" ]; do
    guarded "${base}-${i}"
    i=$((i + 1))
  done
fi
