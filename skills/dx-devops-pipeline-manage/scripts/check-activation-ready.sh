#!/usr/bin/env bash
# Check the deterministic activation prerequisite: a pipeline must have >=1 stage
# before `sf devops pipeline update --activate` will succeed.
# Usage: scripts/check-activation-ready.sh <pipeline-id> [target-org-alias]
# Exits 0 if the pipeline has at least one stage; otherwise prints an actionable
# error and exits 1. Exits 2 if the pipeline can't be read.

set -euo pipefail

PIPELINE_ID="${1:?Usage: check-activation-ready.sh <pipeline-id> [target-org-alias]}"
TARGET_ORG="${2:-}"

ORG_FLAG=()
[ -n "$TARGET_ORG" ] && ORG_FLAG=(--target-org "$TARGET_ORG")

GET_JSON=$(sf devops pipeline get --pipeline-id "$PIPELINE_ID" "${ORG_FLAG[@]+"${ORG_FLAG[@]}"}" --json 2>/dev/null) || {
  echo "ERROR: could not read pipeline '$PIPELINE_ID'. Verify the ID with 'sf devops pipeline list --json' and that the org has DevOps Center enabled." >&2
  exit 2
}

STATUS=$(echo "$GET_JSON" | jq -r '.status // 1')
if [ "$STATUS" != "0" ]; then
  echo "ERROR: 'pipeline get' returned status $STATUS for '$PIPELINE_ID'." >&2
  exit 2
fi

STAGE_COUNT=$(echo "$GET_JSON" | jq -r '(.result.stages // []) | length')
if [ "$STAGE_COUNT" -ge 1 ]; then
  echo "OK: pipeline '$PIPELINE_ID' has $STAGE_COUNT stage(s) — ready to activate"
  exit 0
fi

echo "ERROR: pipeline '$PIPELINE_ID' has no stages. Add at least one stage (sf devops pipeline stage add ...) before --activate." >&2
exit 1
