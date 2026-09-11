#!/usr/bin/env bash
# Resolve the Agentforce Contact Center default queue Id by name (never hardcoded — org-specific).
# Usage: resolve-acc-queue.sh <org-alias> [queue-name]
#   queue-name defaults to "Default Queue Agentforce Contact Center"
# Output: the queue Id on stdout. Exit 1 if not found.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib.sh"

if [[ "${1:-}" == "--help" || $# -lt 1 ]]; then
  echo "Usage: resolve-acc-queue.sh <org-alias> [queue-name]" >&2
  [[ "${1:-}" == "--help" ]] && exit 0 || exit 2
fi

ALIAS="$1"
QUEUE_NAME="${2:-Default Queue Agentforce Contact Center}"

ID=$(sf data query \
  --query "SELECT Id FROM Group WHERE Type = 'Queue' AND Name = '${QUEUE_NAME}' LIMIT 1" \
  --target-org "$ALIAS" --json 2>/dev/null | jq -r '.result.records[0].Id // empty')

if [[ -z "$ID" ]]; then
  echo "error: queue '${QUEUE_NAME}' not found in org '${ALIAS}'" >&2
  exit 1
fi
echo "$ID"
