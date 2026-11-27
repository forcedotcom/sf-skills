#!/usr/bin/env bash
# List active auto-launched flows; a flow's durableId feeds `callOriginationFlowId`.
# Usage: lookup-flows.sh <org-alias>  ->  { "flows": [ { durableId, apiName, label } ] }

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib.sh"

if [[ "${1:-}" == "--help" || $# -lt 1 ]]; then
  echo "Usage: lookup-flows.sh <org-alias>" >&2
  [[ "${1:-}" == "--help" ]] && exit 0 || exit 2
fi

ALIAS="$1"

# Capture the query result and verify it succeeded before handing it to jq: a
# failed `sf data query` still prints a JSON body, but with `status != 0` and no
# `.result.records`, which would make the jq filter emit a misleading empty list.
raw="$(sf data query \
  --query "SELECT DurableId, ApiName, Label, ProcessType FROM FlowDefinitionView WHERE IsActive = true AND ProcessType = 'AutoLaunchedFlow' AND ManageableState = 'unmanaged' ORDER BY Label ASC LIMIT 2000" \
  --target-org "$ALIAS" \
  --json)" || true

if [[ "$(jq -r '.status // empty' <<<"$raw" 2>/dev/null || true)" != "0" ]]; then
  echo "lookup-flows.sh: sf data query failed: $(jq -r '.message // "unknown error (no JSON returned)"' <<<"$raw" 2>/dev/null || echo "unknown error")" >&2
  exit 1
fi

jq '{flows: [.result.records[] | {durableId: .DurableId, apiName: .ApiName, label: .Label}]}' <<<"$raw"
