#!/usr/bin/env bash
# Create, publish, and activate an Agentforce voice service agent (Omni Flow "new agent" path).
# Replicates the validated session flow: generate an authoring bundle from a spec, repair
# generator placeholders, deploy the AiAuthoringBundle, validate, publish, and activate.
# Runs inside a scaffolded SFDX project so the bundle can publish.
#
# DEVIATION (do not remove): do NOT change plannerType to Atlas__VoiceAgent. This org (API <= 67)
# rejects it with an opaque server error. Keep the publish-generated
# Atlas__ConcurrentMultiAgentOrchestration planner — inbound voice routes correctly via the
# Copilot RoutingFlow regardless of planner type. See references/omni-flow-routing.md.
#
# Usage: create-voice-agent.sh <org-alias> <agent-api-name> <agent-label> <spec-file> [work-dir]
#   work-dir defaults to ./acc-voice-build (pass the same dir to create-routing-flows.sh)
# Output: the agent api-name (== BotDefinition DeveloperName) on stdout once Active.
# Exit 0 on Active, 2 usage, 5 on any generate/validate/publish/activate failure.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib.sh"

if [[ "${1:-}" == "--help" || $# -lt 4 ]]; then
  echo "Usage: create-voice-agent.sh <org-alias> <agent-api-name> <agent-label> <spec-file> [work-dir]" >&2
  [[ "${1:-}" == "--help" ]] && exit 0 || exit 2
fi

ALIAS="$1"; API_NAME="$2"; LABEL="$3"; SPEC="$4"; WORK_DIR="${5:-acc-voice-build}"

[[ -f "$SPEC" ]] || { echo "error: spec file not found: $SPEC" >&2; exit 2; }
SPEC_ABS="$(cd "$(dirname "$SPEC")" && pwd)/$(basename "$SPEC")"
AGENT_USER=$(awk -F: '/^agentUser:[[:space:]]*/ { sub(/^[[:space:]]+/, "", $2); gsub(/^"|"$/, "", $2); print $2; exit }' "$SPEC_ABS")

ensure_sfdx_project "$WORK_DIR"
cd "$WORK_DIR"

GEN=$(sf agent generate authoring-bundle --spec "$SPEC_ABS" --name "$LABEL" --api-name "$API_NAME" \
  --output-dir force-app/main/default --target-org "$ALIAS" --json 2>&1) \
  || { echo "authoring-bundle generation failed:" >&2; echo "$GEN" >&2; exit 5; }

AGENT_FILE="force-app/main/default/aiAuthoringBundles/${API_NAME}/${API_NAME}.agent"
if [[ -n "$AGENT_USER" && -f "$AGENT_FILE" ]]; then
  tmp_file="$(mktemp)"
  awk -v user="$AGENT_USER" '
    /^[[:space:]]*default_agent_user:/ {
      match($0, /^[[:space:]]*/)
      print substr($0, RSTART, RLENGTH) "default_agent_user: \"" user "\""
      next
    }
    { print }
  ' "$AGENT_FILE" > "$tmp_file"
  mv "$tmp_file" "$AGENT_FILE"
fi

DEP=$(sf project deploy start --source-dir "force-app/main/default/aiAuthoringBundles/${API_NAME}" \
  --target-org "$ALIAS" --json 2>&1) \
  || { echo "authoring-bundle deploy failed:" >&2; echo "$DEP" >&2; exit 5; }

VAL=$(sf agent validate authoring-bundle --api-name "$API_NAME" --target-org "$ALIAS" --json 2>&1) \
  || { echo "agent validate failed:" >&2; echo "$VAL" >&2; exit 5; }

PUB=$(sf agent publish authoring-bundle --api-name "$API_NAME" --target-org "$ALIAS" --json 2>&1) \
  || { echo "agent publish failed:" >&2; echo "$PUB" >&2; exit 5; }

# --json + --api-name is non-interactive: with --json and no --version the CLI auto-activates
# the latest version and does not prompt, so no confirmation needs to be piped in.
ACT=$(sf agent activate --api-name "$API_NAME" --target-org "$ALIAS" --json 2>&1) \
  || { echo "agent activate failed:" >&2; echo "$ACT" >&2; exit 5; }

STATUS=$(sf data query \
  --query "SELECT Status FROM BotVersion WHERE BotDefinition.DeveloperName = '${API_NAME}' ORDER BY VersionNumber DESC LIMIT 1" \
  --target-org "$ALIAS" --json 2>/dev/null | jq -r '.result.records[0].Status // empty')

[[ "$STATUS" == "Active" ]] || { echo "error: agent '${API_NAME}' is not Active (status: ${STATUS:-unknown})" >&2; exit 5; }
echo "$API_NAME"
