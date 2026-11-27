#!/usr/bin/env bash
# List live caller-line numbers (Tooling API); a `code` feeds `defaultCallerId`.
# Usage: lookup-caller-lines.sh <org-alias>  ->  { "callerLines": [ { id, code } ] }

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib.sh"

if [[ "${1:-}" == "--help" || $# -lt 1 ]]; then
  echo "Usage: lookup-caller-lines.sh <org-alias>" >&2
  [[ "${1:-}" == "--help" ]] && exit 0 || exit 2
fi

ALIAS="$1"

# Capture the query result and verify it succeeded before handing it to jq: a
# failed `sf data query` still prints a JSON body, but with `status != 0` and no
# `.result.records`, which would make the jq filter emit a misleading empty list.
raw="$(sf data query \
  --query "SELECT Id, Code FROM CommunicationChannelLine WHERE CodeStatus = 'Live' AND CliStatus IN ('DEFAULT_CLI','CLI_ENABLED') ORDER BY LastModifiedDate DESC LIMIT 2000" \
  --target-org "$ALIAS" \
  --use-tooling-api \
  --json)" || true

if [[ "$(jq -r '.status // empty' <<<"$raw" 2>/dev/null || true)" != "0" ]]; then
  echo "lookup-caller-lines.sh: sf data query failed: $(jq -r '.message // "unknown error (no JSON returned)"' <<<"$raw" 2>/dev/null || echo "unknown error")" >&2
  exit 1
fi

jq '{callerLines: [.result.records[] | {id: .Id, code: .Code}]}' <<<"$raw"
