#!/usr/bin/env bash
# Resolve a RoutingFlow's FlowDefinition Id (300-prefix) by DeveloperName via the Tooling API.
# Used for the channel's SessionHandlerId on the Omni Flow path, and to validate an existing
# inbound flow when the user reuses one. FlowDefinition (300) is the stable handle — not the
# per-version Flow (301) Id.
# Usage: resolve-flow-definition.sh <org-alias> <flow-developer-name>
# Output: the 300-prefix FlowDefinition Id on stdout.
# Exit 0 if active, 2 usage, 1 if not found, 3 if found but not activated (ActiveVersionId null).

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib.sh"

if [[ "${1:-}" == "--help" || $# -lt 2 ]]; then
  echo "Usage: resolve-flow-definition.sh <org-alias> <flow-developer-name>" >&2
  [[ "${1:-}" == "--help" ]] && exit 0 || exit 2
fi

ALIAS="$1"; DEVNAME="$2"

RESP=$(sf api request rest \
  "/services/data/${API_VERSION}/tooling/query?q=SELECT+Id,DeveloperName,ActiveVersionId+FROM+FlowDefinition+WHERE+DeveloperName='${DEVNAME}'+LIMIT+1" \
  --target-org "$ALIAS" 2>/dev/null || true)

# A success query is an object; an API error is a JSON array [{errorCode,...}].
echo "$RESP" | jq -e 'type == "array"' >/dev/null 2>&1 && { echo "error: FlowDefinition query failed for ${DEVNAME}: $RESP" >&2; exit 1; }

ID=$(echo "$RESP" | jq -r '.records[0].Id // empty')
ACTIVE=$(echo "$RESP" | jq -r '.records[0].ActiveVersionId // empty')

[[ -n "$ID" ]] || { echo "error: FlowDefinition '${DEVNAME}' not found in '${ALIAS}'" >&2; exit 1; }
[[ -n "$ACTIVE" ]] || { echo "error: FlowDefinition '${DEVNAME}' exists but has no active version" >&2; exit 3; }
echo "$ID"
