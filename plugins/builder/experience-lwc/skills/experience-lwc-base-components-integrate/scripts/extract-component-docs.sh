#!/usr/bin/env bash
# Extracts the API doc block for one or more Lightning Base Components from
# references/lightning-components.md. Each component block is delimited by a
# line containing only `---` and identified by a line matching exactly
# `- **Name:** <camelCaseName>` (the leading bullet + colon + trailing
# end-of-line together anchor the match, so `button` does NOT collide with
# `buttonGroup`, `buttonIcon`, or `buttonMenu`).
#
# Usage:
#   scripts/extract-component-docs.sh <camelCaseName> [<camelCaseName>...]
#
# Example:
#   scripts/extract-component-docs.sh datatable recordEditForm buttonIcon

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REF="$SCRIPT_DIR/../references/lightning-components.md"

if [[ ! -f "$REF" ]]; then
  echo "reference file not found: $REF" >&2
  exit 2
fi

if [[ $# -lt 1 ]]; then
  echo "usage: $0 <camelCaseName> [<camelCaseName>...]" >&2
  exit 2
fi

EMITTED=0
for NAME in "$@"; do
  # awk: split on `^---$` delimiter lines using RS, buffer each block
  # in `block`, print blocks whose Name line matches EXACTLY. Delimiter
  # BETWEEN emitted blocks is inserted by the outer shell loop below —
  # awk only knows about its own single invocation.
  if [[ $EMITTED -eq 1 ]]; then
    echo "---"
  fi
  awk -v target="- **Name:** $NAME" '
    BEGIN { RS = "\n---\n"; found = 0 }
    {
      match_found = 0
      n = split($0, lines, "\n")
      for (i = 1; i <= n; i++) {
        if (lines[i] == target) { match_found = 1; break }
      }
      if (match_found) {
        if (found) print "---"
        print $0
        found = 1
      }
    }
    END {
      if (!found) {
        printf "no component named %s found in reference\n", target > "/dev/stderr"
        exit 1
      }
    }
  ' "$REF"
  EMITTED=1
done
