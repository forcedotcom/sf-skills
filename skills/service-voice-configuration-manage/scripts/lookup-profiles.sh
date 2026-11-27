#!/usr/bin/env bash
# List org profiles; their ids feed `profileIds`.
# Usage: lookup-profiles.sh <org-alias>  ->  { "profiles": [ { id, name } ] }

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib.sh"

if [[ "${1:-}" == "--help" || $# -lt 1 ]]; then
  echo "Usage: lookup-profiles.sh <org-alias>" >&2
  [[ "${1:-}" == "--help" ]] && exit 0 || exit 2
fi

ALIAS="$1"

# Capture the query result and verify it succeeded before handing it to jq: a
# failed `sf data query` still prints a JSON body, but with `status != 0` and no
# `.result.records`, which would make the jq filter emit a misleading empty list.
raw="$(sf data query \
  --query "SELECT Id, Name FROM Profile ORDER BY Name ASC LIMIT 500" \
  --target-org "$ALIAS" \
  --json)" || true

if [[ "$(jq -r '.status // empty' <<<"$raw" 2>/dev/null || true)" != "0" ]]; then
  echo "lookup-profiles.sh: sf data query failed: $(jq -r '.message // "unknown error (no JSON returned)"' <<<"$raw" 2>/dev/null || echo "unknown error")" >&2
  exit 1
fi

jq '{profiles: [.result.records[] | {id: .Id, name: .Name}]}' <<<"$raw"
