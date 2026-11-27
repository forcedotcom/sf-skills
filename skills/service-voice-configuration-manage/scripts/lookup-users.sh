#!/usr/bin/env bash
# List active Contact Center users (deduped); their ids feed `userIds`.
# Usage: lookup-users.sh <org-alias>  ->  { "users": [ { id, name, username } ] }

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib.sh"

if [[ "${1:-}" == "--help" || $# -lt 1 ]]; then
  echo "Usage: lookup-users.sh <org-alias>" >&2
  [[ "${1:-}" == "--help" ]] && exit 0 || exit 2
fi

ALIAS="$1"

# Capture the query result and verify it succeeded before handing it to jq: a
# failed `sf data query` still prints a JSON body, but with `status != 0` and no
# `.result.records`, which would make the jq filter emit a misleading empty list.
raw="$(sf data query \
  --query "SELECT AssigneeId, Assignee.Name, Assignee.Username FROM PermissionSetAssignment WHERE PermissionSet.Name IN ('ContactCenterAgentNativeCCaaS','ContactCenterSupervisorNativeCCaaS','ContactCenterAdminNativeCCaaS') AND Assignee.IsActive = true ORDER BY Assignee.Name ASC LIMIT 2000" \
  --target-org "$ALIAS" \
  --json)" || true

if [[ "$(jq -r '.status // empty' <<<"$raw" 2>/dev/null || true)" != "0" ]]; then
  echo "lookup-users.sh: sf data query failed: $(jq -r '.message // "unknown error (no JSON returned)"' <<<"$raw" 2>/dev/null || echo "unknown error")" >&2
  exit 1
fi

jq '{users: ([.result.records[] | {id: .AssigneeId, name: .Assignee.Name, username: .Assignee.Username}] | unique_by(.id))}' <<<"$raw"
