#!/usr/bin/env bash
# Sanitize a CMDT record label into a Metadata API-safe DeveloperName.
#
# Usage:
#   scripts/sanitize-developer-name.sh "<LABEL>" [ROW]
#
# Args:
#   LABEL  Source label / key column value to sanitize.
#   ROW    Optional 1-based source-row index. Used only when the label collapses
#          to empty (all-symbol / non-Latin); defaults to 1.
#
# Rules (same input → same valid name):
#   1. Fold every run of non-[A-Za-z0-9] characters to a single _
#   2. Strip leading _
#   3. If the result starts with a digit, prefix X
#   4. Strip trailing _
#   5. Truncate to 40 characters, then strip a trailing _ the cut may have introduced
#   6. If empty, emit Record_<ROW> — never an empty name
#
# Prints the DeveloperName on stdout. Exits 0 on success, 1 on usage error.
# ASCII-only and lossy for accented / non-Latin labels — see references/cmdt-records.md §7.

set -euo pipefail

LABEL="${1-}"
ROW="${2:-1}"

if [ -z "$LABEL" ]; then
  echo "Usage: sanitize-developer-name.sh \"<LABEL>\" [ROW]" >&2
  exit 1
fi

if ! [[ "$ROW" =~ ^[1-9][0-9]*$ ]]; then
  echo "Error: ROW must be a positive integer (got '$ROW')" >&2
  exit 1
fi

name=$(printf '%s' "$LABEL" \
  | sed -E 's/[^A-Za-z0-9]+/_/g; s/^_+//; s/^([0-9])/X\1/; s/_+$//' \
  | cut -c1-40 | sed -E 's/_+$//')

if [ -z "$name" ]; then
  name="Record_$ROW"
fi

printf '%s\n' "$name"
