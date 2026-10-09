#!/usr/bin/env bash
# detect-existing.sh - read-only probe for existing agent users (org/profile/existing/missing indexes); deterministic, no side effects. Args + JSON output: SKILL.md.

set -euo pipefail

if [ $# -lt 1 ]; then
  echo '{"error":"Missing required argument: org-alias","usage":"bash detect-existing.sh <org-alias> [count=3] [profile-name=\"Standard User\"]"}' >&2
  exit 1
fi

ORG="$1"
COUNT="${2:-3}"
PROFILE_NAME="${3:-Standard User}"

if ! [[ "$COUNT" =~ ^[1-9]$|^10$ ]]; then
  echo "{\"error\":\"Count must be an integer in range 1..10, got: $COUNT\"}" >&2
  exit 1
fi

if ! sf org display --target-org "$ORG" --json >/dev/null 2>&1; then
  echo "{\"error\":\"Org alias '$ORG' is not authenticated. Run: sf org login web -a $ORG -r <my-domain-url>\"}" >&2
  exit 1
fi

# 1. Query Organization: a production org fails all of IsSandbox / TrialExpirationDate!=null /
#    OrganizationType in (Developer Edition, Base Edition).
ORG_JSON=$(sf data query --target-org "$ORG" --query "SELECT Id, IsSandbox, TrialExpirationDate, OrganizationType FROM Organization LIMIT 1" --json 2>/dev/null || true)
ORG_ID=$(echo "$ORG_JSON" | jq -r '.result.records[0].Id // empty')
IS_SANDBOX=$(echo "$ORG_JSON" | jq -r '.result.records[0].IsSandbox // false')
TRIAL_EXP=$(echo "$ORG_JSON" | jq -r '.result.records[0].TrialExpirationDate // "null"')
ORG_TYPE=$(echo "$ORG_JSON" | jq -r '.result.records[0].OrganizationType // "Unknown"')

if [ -z "$ORG_ID" ]; then
  echo '{"error":"Failed to query Organization.Id - check org auth and API permissions."}' >&2
  exit 1
fi

# Compute safe-to-write flag: true if the org is definitively NOT a production customer org.
SAFE_TO_WRITE=false
if [ "$IS_SANDBOX" = "true" ] || [ "$TRIAL_EXP" != "null" ] || [ "$ORG_TYPE" = "Developer Edition" ] || [ "$ORG_TYPE" = "Base Edition" ]; then
  SAFE_TO_WRITE=true
fi

# Derive suffix: last 8 chars of Organization.Id, lowercased. Deterministic per org.
SUFFIX=$(echo -n "${ORG_ID:10:8}" | tr '[:upper:]' '[:lower:]')

# 2. Query Profile. Profile.Name is a display name; escape ' for the SOQL literal (apostrophe safety + no injection).
PROFILE_NAME_SOQL=${PROFILE_NAME//\'/\\\'}
PROFILE_JSON=$(sf data query --target-org "$ORG" --query "SELECT Id, Name FROM Profile WHERE Name = '$PROFILE_NAME_SOQL' LIMIT 1" --json 2>/dev/null || true)
PROFILE_ID=$(echo "$PROFILE_JSON" | jq -r '.result.records[0].Id // empty')

if [ -z "$PROFILE_ID" ]; then
  echo "{\"error\":\"Profile '$PROFILE_NAME' not found on org '$ORG'. Check spelling - profile names are case-sensitive on some orgs and may be localized.\"}" >&2
  exit 1
fi

# 3. Query existing agent users matching the pattern
USER_JSON=$(sf data query --target-org "$ORG" \
  --query "SELECT Id, Username, IsActive FROM User WHERE Username LIKE 'agent%.${SUFFIX}@example.com'" \
  --json 2>/dev/null || true)

# Build existing_users array + missing_indexes array via jq
# For each i in 1..COUNT, check if agent{i}.<suffix>@example.com exists.
EXPECTED_USERNAMES=$(seq 1 "$COUNT" | awk -v s="$SUFFIX" '{ printf "\"agent%s.%s@example.com\"\n", $1, s }' | jq -s '.')

FULL_JSON=$(jq -n \
  --arg org_id "$ORG_ID" \
  --arg org_suffix "$SUFFIX" \
  --argjson is_sandbox "$IS_SANDBOX" \
  --arg trial_expiration_date "$TRIAL_EXP" \
  --arg organization_type "$ORG_TYPE" \
  --argjson safe_to_write "$SAFE_TO_WRITE" \
  --arg profile_id "$PROFILE_ID" \
  --arg profile_name "$PROFILE_NAME" \
  --argjson count "$COUNT" \
  --argjson expected "$EXPECTED_USERNAMES" \
  --argjson user_records "$(echo "$USER_JSON" | jq '.result.records // []')" \
  '
  # Build a map: username -> {id, is_active}
  ($user_records | map({ (.Username | ascii_downcase): {id: .Id, is_active: .IsActive} }) | add // {}) as $by_uname
  |
  # For each expected index, determine if user exists
  [range(1; $count + 1) as $i
   | ($expected[$i - 1] | ascii_downcase) as $uname
   | if $by_uname[$uname] then
       {index: $i, id: $by_uname[$uname].id, username: $uname, is_active: $by_uname[$uname].is_active}
     else
       null
     end
  ] as $slots
  |
  # occupied slots (any user present, active or not)
  ($slots | map(select(. != null))) as $occupied
  |
  # existing_users: only active occupants are reusable; inactive users are surfaced separately
  # (globally-unique username, not recreatable).
  ($occupied | map(select(.is_active == true))) as $existing
  |
  ($occupied | map(select(.is_active != true))) as $inactive
  |
  # missing_indexes: indexes where the slot is empty (no user at all - safe to create)
  ([range(1; $count + 1) as $i | if $slots[$i - 1] == null then $i else null end] | map(select(. != null))) as $missing
  |
  {
    org_id: $org_id,
    org_suffix: $org_suffix,
    is_sandbox: $is_sandbox,
    trial_expiration_date: (if $trial_expiration_date == "null" then null else $trial_expiration_date end),
    organization_type: $organization_type,
    safe_to_write: $safe_to_write,
    profile_id: $profile_id,
    profile_name: $profile_name,
    requested_count: $count,
    existing_users: $existing,
    inactive_users: $inactive,
    inactive_count: ($inactive | length),
    missing_indexes: $missing,
    missing_count: ($missing | length)
  }
  ')

echo "$FULL_JSON"
