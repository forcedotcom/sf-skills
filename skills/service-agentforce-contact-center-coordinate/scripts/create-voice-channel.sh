#!/usr/bin/env bash
# Create an active PstnVoice MessagingChannel for a procured number.
# Usage: create-voice-channel.sh <org-alias> <phone-number> <channel-line-id> <session-handler-id> [fallback-queue-id]
#   Omni Queue (4 args): pass the ACC queue Id as <session-handler-id>.
#   Omni Flow  (5 args): pass the inbound FlowDefinition Id (300-prefix) as <session-handler-id>
#                        and the fallback queue Id as [fallback-queue-id].
# Output: JSON create response on stdout. Exit 0 only when the response is
# "success": true; exit 5 otherwise.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib.sh"

if [[ "${1:-}" == "--help" || $# -lt 4 ]]; then
  echo "Usage: create-voice-channel.sh <org-alias> <phone-number> <channel-line-id> <session-handler-id> [fallback-queue-id]" >&2
  [[ "${1:-}" == "--help" ]] && exit 0 || exit 2
fi

ALIAS="$1"; NUMBER="$2"; CHANNEL_LINE_ID="$3"; SESSION_HANDLER_ID="$4"; FALLBACK_QUEUE_ID="${5:-}"

DEV_NAME="Voice_Channel_${NUMBER//+/}"
ENDPOINT="/services/data/${API_VERSION}/sobjects/MessagingChannel/"

post_channel() {
  local err_file out status
  err_file="$(mktemp)"
  set +e
  out=$(sf api request rest "$ENDPOINT" \
    --method POST \
    --body "$1" \
    --target-org "$ALIAS" 2>"$err_file")
  status=$?
  set -e

  if [[ -n "$out" ]]; then
    printf '%s\n' "$out"
  else
    cat "$err_file"
  fi
  rm -f "$err_file"
  return "$status"
}

# SessionHandlerId is the queue Id (Omni Queue) or the inbound FlowDefinition Id (Omni Flow).
# On the Omni Flow path also set FallbackQueueId to the queue the agent overflows/escalates to.
if [[ -n "$FALLBACK_QUEUE_ID" ]]; then
  BODY=$(jq -n \
    --arg dn "$DEV_NAME" --arg num "$NUMBER" --arg cl "$CHANNEL_LINE_ID" \
    --arg sh "$SESSION_HANDLER_ID" --arg fq "$FALLBACK_QUEUE_ID" \
    '{DeveloperName:$dn, MasterLabel:("Voice Channel " + $num), MessageType:"PstnVoice",
      MessagingPlatformKey:$num, ChannelLineId:$cl, IsActive:true, SessionHandlerId:$sh, FallbackQueueId:$fq}')
else
  BODY=$(jq -n \
    --arg dn "$DEV_NAME" --arg num "$NUMBER" --arg cl "$CHANNEL_LINE_ID" --arg sh "$SESSION_HANDLER_ID" \
    '{DeveloperName:$dn, MasterLabel:("Voice Channel " + $num), MessageType:"PstnVoice",
      MessagingPlatformKey:$num, ChannelLineId:$cl, IsActive:true, SessionHandlerId:$sh}')
fi

RESP=$(post_channel "$BODY") || true

echo "$RESP"

# The response is emitted above for the caller to parse; set the exit code so a
# failed create (error payload, non-live number, duplicate name) can't be mistaken
# for success by a caller that only checks the exit status.
echo "$RESP" | jq -e '.success == true' >/dev/null 2>&1 || exit 5
