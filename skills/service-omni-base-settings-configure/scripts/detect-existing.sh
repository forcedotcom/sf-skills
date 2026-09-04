#!/usr/bin/env bash
# detect-existing.sh - read-only probe of OmniChannelSettings (five toggle values + all_enabled); deterministic, no side effects. Args, output, exit codes: SKILL.md.

set -euo pipefail

if [ $# -lt 1 ]; then
  echo '{"error":"Missing required argument: org-alias","usage":"bash detect-existing.sh <org-alias>"}' >&2
  exit 1
fi

ORG="$1"

# Verify org is authenticated (fail fast, do not retrieve if org auth is broken)
if ! sf org display --target-org "$ORG" --json >/dev/null 2>&1; then
  echo "{\"error\":\"Org alias '$ORG' is not authenticated. Run: sf org login web -a $ORG -r <my-domain-url>\"}" >&2
  exit 1
fi

# Retrieve Settings:OmniChannel into a per-invocation temp DX project.
# Metadata retrieve is slow (~1-2 min); this is expected and unavoidable.
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

cat > "$WORK/sfdx-project.json" <<'EOF'
{"packageDirectories":[{"path":"force-app","default":true}],"sourceApiVersion":"66.0"}
EOF
mkdir -p "$WORK/force-app/main/default"

if ! (cd "$WORK" && sf project retrieve start --target-org "$ORG" --metadata "Settings:OmniChannel" --json >/dev/null 2>&1); then
  echo "{\"error\":\"Metadata retrieve failed for Settings:OmniChannel on org '$ORG'. This is often transient (UNKNOWN_EXCEPTION) - retry once.\"}" >&2
  exit 1
fi

SETTINGS_RELATIVE_PATH="force-app/main/default/settings/OmniChannel.settings-meta.xml"
XML="$WORK/$SETTINGS_RELATIVE_PATH"
if [ ! -f "$XML" ]; then
  echo "{\"error\":\"Retrieve succeeded but expected file not found: $SETTINGS_RELATIVE_PATH. Org may not have Omni-Channel provisioned.\"}" >&2
  exit 1
fi

# Parse each toggle from the retrieved XML; a missing element means absent (treat as false).
parse_toggle() {
  local name="$1"
  local val
  val=$(grep -oE "<${name}>(true|false)</${name}>" "$XML" | head -1 | sed -E "s|</?${name}>||g" || true)
  if [ "$val" = "true" ]; then echo true; else echo false; fi
}

T1=$(parse_toggle enableOmniAutoLoginPrompt)
T2=$(parse_toggle enableOmniChannel)
T3=$(parse_toggle enableOmniSecondaryRoutingPriority)
T4=$(parse_toggle enableOmniSkillsRouting)
T5=$(parse_toggle enableOmniStatusCapModel)

ALL=false
if [ "$T1" = "true" ] && [ "$T2" = "true" ] && [ "$T3" = "true" ] && [ "$T4" = "true" ] && [ "$T5" = "true" ]; then
  ALL=true
fi

cat <<EOF
{
  "enableOmniAutoLoginPrompt": $T1,
  "enableOmniChannel": $T2,
  "enableOmniSecondaryRoutingPriority": $T3,
  "enableOmniSkillsRouting": $T4,
  "enableOmniStatusCapModel": $T5,
  "all_enabled": $ALL
}
EOF
