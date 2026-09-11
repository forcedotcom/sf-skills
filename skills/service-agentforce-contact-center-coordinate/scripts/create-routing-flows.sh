#!/usr/bin/env bash
# Create and deploy the two RoutingFlows of a voice Omni Flow, then return the inbound flow's
# FlowDefinition Id (300-prefix) for the channel's SessionHandlerId.
#   - Inbound    <api-name>_Voice_Omni_Flow  : routingType=Copilot   -> routes to the agent, queue as fallback
#   - Escalation <api-name>_Voice_Escalation : routingType=QueueBased -> agent hands off to the queue
# Usage: create-routing-flows.sh <org-alias> <agent-api-name> <agent-label> <queue-id> <queue-name> [work-dir]
#   work-dir defaults to ./acc-voice-build (reuse the same dir as create-voice-agent.sh)
# Output: the inbound FlowDefinition Id (300-prefix) on stdout.
# Exit 0 on success, 2 usage, 5 on deploy failure, 3 if the inbound flow did not activate.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib.sh"

if [[ "${1:-}" == "--help" || $# -lt 5 ]]; then
  echo "Usage: create-routing-flows.sh <org-alias> <agent-api-name> <agent-label> <queue-id> <queue-name> [work-dir]" >&2
  [[ "${1:-}" == "--help" ]] && exit 0 || exit 2
fi

ALIAS="$1"; API_NAME="$2"; LABEL="$3"; QUEUE_ID="$4"; QUEUE_NAME="$5"; WORK_DIR="${6:-acc-voice-build}"

INBOUND="${API_NAME}_Voice_Omni_Flow"
ESC="${API_NAME}_Voice_Escalation"
ASSETS_DIR="$(cd "$SCRIPT_DIR/../assets" && pwd)"

# Free-text values land in XML stringValue/label nodes — escape them so a queue name or
# agent label containing &, <, >, etc. can't produce malformed XML. QUEUE_ID and API_NAME
# are platform-constrained (Id / DeveloperName), so they pass through unescaped.
LABEL_X="$(xml_escape "$LABEL")"
QUEUE_NAME_X="$(xml_escape "$QUEUE_NAME")"

ensure_sfdx_project "$WORK_DIR"
WORK_DIR_ABS="$(cd "$WORK_DIR" && pwd)"
FLOWS_DIR="$WORK_DIR_ABS/force-app/main/default/flows"
mkdir -p "$FLOWS_DIR"

render_template "$ASSETS_DIR/omni-flow.flow-meta.xml" \
  "FLOW_LABEL=${LABEL_X} Voice Omni Flow" "AGENT_API_NAME=${API_NAME}" "AGENT_LABEL=${LABEL_X}" \
  "QUEUE_ID=${QUEUE_ID}" "QUEUE_LABEL=${QUEUE_NAME_X}" > "$FLOWS_DIR/${INBOUND}.flow-meta.xml"

render_template "$ASSETS_DIR/escalation-flow.flow-meta.xml" \
  "FLOW_LABEL=${LABEL_X} Voice Escalation" "QUEUE_ID=${QUEUE_ID}" "QUEUE_LABEL=${QUEUE_NAME_X}" \
  > "$FLOWS_DIR/${ESC}.flow-meta.xml"

DEP=$(cd "$WORK_DIR_ABS" && sf project deploy start --source-dir "$FLOWS_DIR" --target-org "$ALIAS" --json 2>&1) \
  || { echo "flow deploy failed:" >&2; echo "$DEP" >&2; exit 5; }

# The channel wires to the inbound flow's FlowDefinition Id; it must be active.
"$SCRIPT_DIR/resolve-flow-definition.sh" "$ALIAS" "$INBOUND"
