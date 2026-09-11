#!/usr/bin/env bash
# Preflight the Agentforce (service agent) prerequisite and resolve the canonical Einstein Agent User.
# The Omni Flow "create new agent" path needs a user with the Einstein Agent User profile;
# broader Agent/Bot profile matches can validate a spec but fail at publish time.
# If no canonical user exists, ask the Salesforce CLI to provision one with the correct
# profile, permission sets, and PSL assignments.
# Usage: check-agentforce-prereq.sh <org-alias> [base-username]
# Output: the Einstein Agent User Username on stdout.
# Exit 0 if found/provisioned, 2 usage, 3 if none exists and auto-provisioning fails.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib.sh"

if [[ "${1:-}" == "--help" || $# -lt 1 ]]; then
  echo "Usage: check-agentforce-prereq.sh <org-alias> [base-username]" >&2
  [[ "${1:-}" == "--help" ]] && exit 0 || exit 2
fi

ALIAS="$1"
BASE_USERNAME="${2:-agentforce-service-agent@example.com}"

# The profile name is the canonical signal used by `sf org create agent-user`.
# Do not fall back to generic Agent/Bot profiles; those users can make spec generation
# appear successful but fail `sf agent publish authoring-bundle`.
USERNAME=$(sf data query \
  --query "SELECT Username FROM User WHERE IsActive = true AND Profile.Name = 'Einstein Agent User' ORDER BY CreatedDate DESC LIMIT 1" \
  --target-org "$ALIAS" --json 2>/dev/null | jq -r '.result.records[0].Username // empty')

if [[ -n "$USERNAME" ]]; then
  echo "$USERNAME"
  exit 0
fi

CREATE_RESP=$(sf org create agent-user \
  --target-org "$ALIAS" \
  --base-username "$BASE_USERNAME" \
  --first-name "EinsteinServiceAgent" \
  --last-name "User" \
  --json 2>&1) || {
    echo "error: no Einstein Agent User found in '${ALIAS}', and auto-provisioning failed." >&2
    echo "$CREATE_RESP" >&2
    echo "See references/agentforce-prerequisite.md to enable Agentforce Agents or free an Agentforce Service Agent User license, then retry." >&2
    exit 3
  }

USERNAME=$(echo "$CREATE_RESP" | jq -r '.result.username // empty')
if [[ -z "$USERNAME" ]]; then
  echo "error: sf org create agent-user did not return result.username:" >&2
  echo "$CREATE_RESP" >&2
  exit 3
fi

echo "$USERNAME"
