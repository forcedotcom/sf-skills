#!/usr/bin/env bash
# enable-and-report.sh - enable the Omni-Channel sidebar on a Lightning console app (CustomApplication.isOmniPinnedViewEnabled=true) and verify round-trip; idempotent, non-destructive (only the one boolean). Args, exit codes: SKILL.md.

set -euo pipefail

if [ $# -lt 1 ]; then
  echo '{"error":"Usage: bash enable-and-report.sh <org-alias> [app_developer_name]"}' >&2
  exit 1
fi

ORG="$1"
APP_DN_ARG="${2:-}"

# App DeveloperName grammar (when supplied): leading letter, then letters/digits/underscore, max 80.
# A namespace prefix (ns__Name) is permitted for packaged apps.
if [ -n "$APP_DN_ARG" ] && ! [[ "$APP_DN_ARG" =~ ^([A-Za-z][A-Za-z0-9]{0,14}__)?[A-Za-z][A-Za-z0-9_]{0,79}$ ]]; then
  echo "{\"error\":\"Invalid app_developer_name '$APP_DN_ARG'. Must be a CustomApplication DeveloperName (letters, digits, underscores; optional ns__ prefix).\"}" >&2
  exit 1
fi

if ! sf org display --target-org "$ORG" --json >/dev/null 2>&1; then
  echo "{\"error\":\"Org alias '$ORG' is not authenticated. Run: sf org login web -a $ORG -r <my-domain-url>\"}" >&2
  exit 1
fi

# Helpers
emit_blocked() {
  local msg="$1"
  local click_path="${2:-}"
  local app_dn="${3:-}"
  local target_skill="${4:-}"

  local manual_actions='[]'
  if [ -n "$target_skill" ]; then
    manual_actions=$(jq -n --arg ts "$target_skill" '[{id: "MISSING_PREREQ", title: "Run prerequisite skill", target_skill: $ts}]')
  elif [ -n "$click_path" ]; then
    manual_actions=$(jq -n --arg cp "$click_path" '[{id: "MANUAL_FIX", title: "Manual fix required", click_path: $cp}]')
  fi

  EMITTED=1
  jq -n \
    --arg msg "$msg" \
    --arg dn "$app_dn" \
    --argjson ma "$manual_actions" \
    '{
      skill: "service-omni-sidebar-configure",
      status: "blocked",
      app_developer_name: (if $dn == "" then null else $dn end),
      app_label: null,
      before: null,
      after: null,
      deploy_id: null,
      manual_actions: $ma,
      blocking_issue: $msg
    }'
  exit 1
}

emit_plan() {
  local status="$1"
  local detail="$2"
  local app_dn="$3"
  EMITTED=1
  jq -n \
    --arg status "$status" \
    --arg detail "$detail" \
    --arg dn "$app_dn" \
    '{
      skill: "service-omni-sidebar-configure",
      status: $status,
      plan_mode: true,
      plan_detail: $detail,
      app_developer_name: (if $dn == "" then null else $dn end),
      manual_actions: [],
      blocking_issue: null
    }'
  exit 0
}

# Fail-safe: the leaf runs under `set -euo pipefail` with several unguarded jq/sed/awk calls, so a
# transient failure (e.g. a flaky Metadata API) could otherwise kill it with empty stdout. Emit a
# structured blocked JSON on any exit that happens before a real result, so the caller never parses
# empty output. EMITTED is flipped to 1 immediately before each intentional emission below.
EMITTED=0
WORK=""
cleanup_work() { [ -n "${WORK:-}" ] && rm -rf "$WORK" 2>/dev/null || true; }
on_exit() {
  cleanup_work
  if [ "$EMITTED" != "1" ]; then
    jq -n --arg dn "${APP_DN:-${APP_DN_ARG:-}}" \
      '{skill:"service-omni-sidebar-configure", status:"blocked",
        app_developer_name:(if $dn=="" then null else $dn end),
        app_label:null, before:null, after:null, deploy_id:null, manual_actions:[],
        blocking_issue:"Sidebar enablement aborted before completing (unexpected error; see stderr). Re-run, optionally with an explicit app_developer_name."}'
  fi
}
trap on_exit EXIT

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

retrieve_app_xml() {
  # Retrieve CustomApplication:<member> into a fresh temp DX project and echo the .app-meta.xml path
  # (empty if none returned). Caller owns cleanup of the printed dir's parent.
  local member="${1:-$APP_DN}"
  local work; work="$(mktemp -d)"
  cp "$SCRIPT_DIR/../assets/sfdx-project.json" "$work/sfdx-project.json" 2>/dev/null || echo '{"packageDirectories":[{"path":"force-app","default":true}],"sourceApiVersion":"66.0"}' > "$work/sfdx-project.json"
  mkdir -p "$work/force-app/main/default"
  ( cd "$work" && sf project retrieve start --target-org "$ORG" \
      --metadata "CustomApplication:${member}" --json >/dev/null 2>&1 || true )
  local xml; xml=$(find "$work" -name "*.app-meta.xml" 2>/dev/null | head -1)
  echo "$work|$xml"
}

# Step 1 - Organization + safe_to_write guard
ORG_GUARD_JSON=$(sf data query --target-org "$ORG" \
  --query "SELECT IsSandbox, TrialExpirationDate, OrganizationType FROM Organization LIMIT 1" \
  --json 2>/dev/null) || emit_blocked "Failed to query Organization for the safe_to_write guard."
IS_SANDBOX=$(echo "$ORG_GUARD_JSON" | jq -r '.result.records[0].IsSandbox')
TRIAL_EXP=$(echo "$ORG_GUARD_JSON"  | jq -r '.result.records[0].TrialExpirationDate // "null"')
ORG_TYPE=$(echo "$ORG_GUARD_JSON"   | jq -r '.result.records[0].OrganizationType')

SAFE_TO_WRITE=false
if [ "$IS_SANDBOX" = "true" ] \
   || [ "$TRIAL_EXP" != "null" ] \
   || [ "$ORG_TYPE" = "Developer Edition" ] \
   || [ "$ORG_TYPE" = "Base Edition" ]; then
  SAFE_TO_WRITE=true
fi

if [ "$SAFE_TO_WRITE" != "true" ]; then
  emit_blocked "Refusing to modify an app on a real production customer org (IsSandbox=$IS_SANDBOX, TrialExpirationDate=$TRIAL_EXP, OrganizationType=$ORG_TYPE). Target a sandbox, trial CDO, or Developer Edition org."
fi

# Step 2 - Resolve the target Lightning console app
APP_DN="$APP_DN_ARG"
APP_LABEL=""
if [ -z "$APP_DN" ]; then
  # Standard apps are frequently read-only even though AppDefinition reports them as console apps.
  # Enumerate actual CustomApplication members and inspect only non-standard metadata so automatic
  # selection cannot pick an undeployable platform app.
  APP_METADATA_JSON=$(sf org list metadata --metadata-type CustomApplication \
    --target-org "$ORG" --json 2>/dev/null) \
    || emit_blocked "Could not list CustomApplication metadata to auto-detect a deployable Lightning console app. Re-run with a reachable org, or pass an explicit app_developer_name."
  echo "$APP_METADATA_JSON" | jq -e '.result | arrays' >/dev/null 2>&1 \
    || emit_blocked "CustomApplication metadata discovery returned no parseable result (inconclusive). Re-run, or pass an explicit app_developer_name."

  CANDIDATES='[]'
  CUSTOM_MEMBERS=$(echo "$APP_METADATA_JSON" | jq -r '.result[]?.fullName | select(startswith("standard__") | not)')
  for APP_MEMBER in $CUSTOM_MEMBERS; do
    CANDIDATE_RET=$(retrieve_app_xml "$APP_MEMBER")
    CANDIDATE_WORK="${CANDIDATE_RET%%|*}"
    CANDIDATE_XML="${CANDIDATE_RET#*|}"
    if [ -n "$CANDIDATE_XML" ] && [ -f "$CANDIDATE_XML" ] \
      && grep -q '<uiType>Lightning</uiType>' "$CANDIDATE_XML" \
      && grep -q '<navType>Console</navType>' "$CANDIDATE_XML"; then
      CANDIDATES=$(echo "$CANDIDATES" | jq --arg dn "$APP_MEMBER" '. + [$dn]')
    fi
    rm -rf "$CANDIDATE_WORK"
  done

  APP_COUNT=$(echo "$CANDIDATES" | jq 'length')
  if [ "$APP_COUNT" = "0" ]; then
    emit_blocked "No deployable custom Lightning console app found on this org. Create one first, then pass its DeveloperName." \
      "Setup → App Manager → New Lightning App → Navigation Style: Console → Save"
  elif [ "$APP_COUNT" != "1" ]; then
    emit_blocked "Found $APP_COUNT deployable custom Lightning console apps ($CANDIDATES). Re-run with an explicit app_developer_name so the sidebar is enabled on the intended app."
  fi
  APP_DN=$(echo "$CANDIDATES" | jq -r '.[0]')
fi

# Step 3 - Retrieve the app's CustomApplication metadata
RET=$(retrieve_app_xml "$APP_DN")
WORK="${RET%%|*}"
APP_XML="${RET#*|}"

# Standard apps expose AppDefinition.DeveloperName without the standard__ prefix, but the
# CustomApplication metadata member requires it (e.g. standard__LightningService). If the plain
# member did not resolve and the name is unprefixed, retry with standard__ and adopt whichever
# member actually retrieves, so the later deploy targets the correct component.
if { [ -z "$APP_XML" ] || [ ! -f "$APP_XML" ]; } && [[ "$APP_DN" != *"__"* ]]; then
  cleanup_work
  RET=$(retrieve_app_xml "standard__$APP_DN")
  WORK="${RET%%|*}"
  APP_XML="${RET#*|}"
  { [ -n "$APP_XML" ] && [ -f "$APP_XML" ]; } && APP_DN="standard__$APP_DN"
fi

if [ -z "$APP_XML" ] || [ ! -f "$APP_XML" ]; then
  emit_blocked "Could not retrieve CustomApplication '$APP_DN' (it may not exist, may be a standard/Aura app that is not deployable as CustomApplication, or the retrieve returned no metadata)." \
    "Setup → App Manager → confirm '$APP_DN' is a custom Lightning console app"
fi

# Current value of the boolean (true only when the element is present AND set true).
current_flag() {
  if grep -oE "<isOmniPinnedViewEnabled>[^<]*</isOmniPinnedViewEnabled>" "$1" 2>/dev/null \
       | grep -qi ">true<"; then
    echo true
  else
    echo false
  fi
}
BEFORE=$(current_flag "$APP_XML")

# PLAN_ONLY - all reads above are read-only; report intent and stop before any write.
if [ "${PLAN_ONLY:-}" = "1" ]; then
  if [ "$BEFORE" = "true" ]; then
    emit_plan "reused" "Omni sidebar already enabled (isOmniPinnedViewEnabled=true) on '$APP_DN'." "$APP_DN"
  else
    emit_plan "action_needed" "Would set isOmniPinnedViewEnabled=true on Lightning console app '$APP_DN'." "$APP_DN"
  fi
fi

# Step 4 - Already enabled → reused (no deploy)
if [ "$BEFORE" = "true" ]; then
  EMITTED=1
  jq -n --arg dn "$APP_DN" --arg lbl "$APP_LABEL" \
    '{
      skill: "service-omni-sidebar-configure",
      status: "reused",
      app_developer_name: $dn,
      app_label: (if $lbl == "" then null else $lbl end),
      before: true,
      after: true,
      deploy_id: null,
      manual_actions: [],
      blocking_issue: null
    }'
  exit 0
fi

# Step 5 - Set the flag (replace in place, or insert in XSD order before <label>)
if grep -q "<isOmniPinnedViewEnabled>" "$APP_XML"; then
  sed -E "s|<isOmniPinnedViewEnabled>[^<]*</isOmniPinnedViewEnabled>|<isOmniPinnedViewEnabled>true</isOmniPinnedViewEnabled>|" \
    "$APP_XML" > "$APP_XML.tmp" && mv "$APP_XML.tmp" "$APP_XML"
else
  # Insert immediately before the first top-level <label> - its XSD-ordered position in
  # CustomApplication (the is* booleans precede <label>). Only the first match is edited.
  awk 'BEGIN{done=0}
       /<label>/ && !done { print "    <isOmniPinnedViewEnabled>true</isOmniPinnedViewEnabled>"; done=1 }
       { print }' "$APP_XML" > "$APP_XML.tmp" && mv "$APP_XML.tmp" "$APP_XML"
fi

if [ "$(current_flag "$APP_XML")" != "true" ]; then
  emit_blocked "Failed to set isOmniPinnedViewEnabled in the retrieved CustomApplication payload for '$APP_DN' (unexpected app metadata shape)." "" "$APP_DN"
fi

# Step 6 - Deploy the single CustomApplication (async + poll to a terminal state)
START_JSON=$(cd "$WORK" && sf project deploy start --target-org "$ORG" \
  --metadata "CustomApplication:${APP_DN}" --async --json 2>/dev/null || true)
DEPLOY_ID=$(echo "$START_JSON" | jq -r '.result.id // ""' 2>/dev/null)
DEPLOY_JSON="$START_JSON"

if [ -n "$DEPLOY_ID" ] && [ "$DEPLOY_ID" != "null" ]; then
  POLL_STATUS=""
  for _ in $(seq 1 40); do
    REPORT_JSON=$(cd "$WORK" && sf project deploy report --job-id "$DEPLOY_ID" --target-org "$ORG" --json 2>/dev/null || true)
    CUR_STATUS=$(echo "$REPORT_JSON" | jq -r '.result.status // ""' 2>/dev/null)
    case "$CUR_STATUS" in
      Succeeded|Failed|SucceededPartial|Canceled) DEPLOY_JSON="$REPORT_JSON"; POLL_STATUS="$CUR_STATUS"; break ;;
    esac
    sleep 15
  done
  if [ -z "$POLL_STATUS" ]; then
    emit_blocked "CustomApplication deploy job $DEPLOY_ID for '$APP_DN' did not reach a terminal state within the poll budget. Not reporting success." "" "$APP_DN"
  fi
fi

DEPLOY_SUCCESS=$(echo "$DEPLOY_JSON" | jq -r '.result.success // false' 2>/dev/null)
DEPLOY_ID=$(echo "$DEPLOY_JSON"      | jq -r '.result.id      // ""'    2>/dev/null)

if [ "$DEPLOY_SUCCESS" != "true" ]; then
  FAILURES=$(echo "$DEPLOY_JSON" | jq -r '.result.details.componentFailures // [] | map(.problem) | join("; ")' 2>/dev/null)
  if [ -z "$FAILURES" ] || [ "$FAILURES" = "null" ]; then
    FAILURES=$(echo "$DEPLOY_JSON" | jq -r '.message // .result.errorMessage // "Unknown deploy error"' 2>/dev/null)
  fi
  # Standard console apps (standard__*) are frequently read-only via the Metadata API, so the
  # fallback deploy can be rejected. Give a targeted remediation instead of only the raw error.
  if [[ "$APP_DN" == standard__* ]]; then
    emit_blocked "Deploy of the standard console app '$APP_DN' failed: $FAILURES. Standard apps are often not modifiable via the Metadata API - enable the Omni sidebar in Setup, or re-run this skill against a custom Lightning console app (pass its DeveloperName)." \
      "Setup → App Manager → ${APP_DN#standard__} → Edit → enable the Omni-Channel pinned/utility sidebar" "$APP_DN"
  fi
  emit_blocked "Deploy of CustomApplication '$APP_DN' failed: $FAILURES" "" "$APP_DN"
fi

# Step 7 - Post-verify: re-retrieve and confirm the flag is true on the org
AFTER="unverified"
for verify_attempt in 1 2 3; do
  VRET=$(retrieve_app_xml "$APP_DN")
  VWORK="${VRET%%|*}"; VXML="${VRET#*|}"
  if [ -n "$VXML" ] && [ -f "$VXML" ]; then
    AFTER=$(current_flag "$VXML")
    rm -rf "$VWORK"
    break
  fi
  rm -rf "$VWORK"
  [ "$verify_attempt" -lt 3 ] && sleep 10
done

if [ "$AFTER" != "true" ]; then
  emit_blocked "Deploy reported success but isOmniPinnedViewEnabled is not true for '$APP_DN' on post-verify (retrieved metadata does not confirm the sidebar is pinned)." "" "$APP_DN"
fi

EMITTED=1
jq -n --arg dn "$APP_DN" --arg lbl "$APP_LABEL" --arg deploy_id "$DEPLOY_ID" \
  '{
    skill: "service-omni-sidebar-configure",
    status: "enabled",
    app_developer_name: $dn,
    app_label: (if $lbl == "" then null else $lbl end),
    before: false,
    after: true,
    deploy_id: (if $deploy_id == "" then null else $deploy_id end),
    manual_actions: [],
    blocking_issue: null
  }'
