#!/bin/bash
# Decision test for SessionStart project-signal plugin recommendations (W-23856691).
#
# Concrete Agentforce, CMS, LWC, and React project signals must route to their
# intended uninstalled plugin at high confidence. The same signal outside a
# Salesforce project stays silent. A later matching concrete task promotes the
# SessionStart proposal to a resumable task-backed workflow and surfaces it once
# in that new task context.
#
# Run: bash plugins/builder/salesforce-development/scripts/test/session-plugin-hint-gate.test.sh

set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HINT="$ROOT/session_plugin_hint.py"
CTX="$ROOT/sf-context"
PASS=0
FAIL=0

CFG="$(mktemp -d)"
BASE="$(mktemp -d)"
trap 'rm -rf "$CFG" "$BASE"' EXIT

# Only the foundation is installed, so every add-on route is available to test.
printf '{"enabledPlugins":{"salesforce-development@salesforce":true}}' \
  > "$CFG/settings.json"
export CLAUDE_CONFIG_DIR="$CFG"

NONPROJ="$BASE/non-project"
AGENT="$BASE/agentforce-project"
CMS="$BASE/cms-project"
CMS_ASSET="$BASE/cms-asset-project"
CMS_STOCK="$BASE/cms-stock-project"
LWC="$BASE/lwc-project"
REACT="$BASE/react-project"
mkdir -p "$NONPROJ" "$AGENT" \
  "$CMS/force-app/main/default/managedContentTypes" \
  "$CMS_ASSET/force-app/main/default/contentassets" \
  "$CMS_STOCK/stockimages" \
  "$LWC/force-app/main/default/lwc/accountTable" \
  "$REACT/force-app/main/default/uiBundles/storefront/src/pages"

for project in "$AGENT" "$CMS" "$CMS_ASSET" "$CMS_STOCK" "$LWC" "$REACT"; do
  printf '{"packageDirectories":[{"path":"force-app","default":true}]}' \
    > "$project/sfdx-project.json"
done

touch "$NONPROJ/onboarding.agent"
touch "$AGENT/onboarding.agent"
touch "$CMS/force-app/main/default/managedContentTypes/News.managedContentType-meta.xml"
touch "$CMS_ASSET/force-app/main/default/contentassets/Hero.asset"
touch "$CMS_STOCK/stockimages/12345.jpg"
touch "$LWC/force-app/main/default/lwc/accountTable/accountTable.js"
touch "$REACT/force-app/main/default/uiBundles/storefront/src/pages/Home.tsx"

run_hint() {
  # run_hint <cwd> <session-id>
  printf '{"cwd":"%s","session_id":"%s","source":"startup"}' "$1" "$2" \
    | python3 "$HINT"
}

assert_route() {
  # assert_route <description> <cwd> <expected-plugin> <unexpected-regex>
  local desc="$1" cwd="$2" expected="$3" unexpected="$4" out
  out=$(run_hint "$cwd" "hint-${expected}-$$")
  if echo "$out" | grep -q "Recommended plugins for this project" \
     && echo "$out" | grep -q "$expected" \
     && echo "$out" | grep -q "high confidence" \
     && echo "$out" | grep -q "/salesforce-development:plugin-install $expected" \
     && ! echo "$out" | grep -Eq "$unexpected"; then
    PASS=$((PASS + 1)); printf '  ok   %-62s → %s\n' "$desc" "$expected"
  else
    FAIL=$((FAIL + 1)); printf '  FAIL %-62s → %s\n' "$desc" "$out"
  fi
}

echo "session_plugin_hint — project signals (offline, no org)"

OUT_OUTSIDE=$(run_hint "$NONPROJ" "hint-outside-$$")
if [ "$OUT_OUTSIDE" = '{"continue": true}' ]; then
  PASS=$((PASS + 1)); printf '  ok   %-62s → quiet\n' "signal outside Salesforce project stays silent"
else
  FAIL=$((FAIL + 1)); printf '  FAIL %-62s → %s\n' "signal outside Salesforce project stays silent" "$OUT_OUTSIDE"
fi

assert_route "Agentforce file routes to Agentforce plugin" \
  "$AGENT" "agentforce-adlc" "experience-(cms|lwc|react)"
assert_route "managed CMS content routes to CMS plugin" \
  "$CMS" "experience-cms" "agentforce-adlc|experience-(lwc|react)"
assert_route "Salesforce content asset routes to CMS plugin" \
  "$CMS_ASSET" "experience-cms" "agentforce-adlc|experience-(lwc|react)"
assert_route "stock-image output routes to CMS plugin" \
  "$CMS_STOCK" "experience-cms" "agentforce-adlc|experience-(lwc|react)"
assert_route "LWC source routes only to LWC plugin" \
  "$LWC" "experience-lwc" "agentforce-adlc|experience-(cms|react)"
assert_route "React UI bundle routes only to React plugin" \
  "$REACT" "experience-react" "agentforce-adlc|experience-(cms|lwc)"

# The exact live-QE flow: SessionStart proposes React, an explanatory plugin
# question keeps that decision active, and terse acceptance advances only React
# to the same-session accepted-proposal path.
SID_FLOW="hint-react-flow-$$"
run_hint "$REACT" "$SID_FLOW" >/dev/null
OUT_FLOW_QUESTION=$(
  cd "$REACT" || exit 1
  printf '{"session_id":"%s","prompt_id":"p1","prompt":"Which plugin would help me build a Salesforce React UI bundle with TSX, Tailwind, and shadcn?"}' \
    "$SID_FLOW" | "$CTX" prompt-dispatch
)
OUT_FLOW_ACCEPT=$(
  cd "$REACT" || exit 1
  printf '{"session_id":"%s","prompt_id":"p2","prompt":"ok install it"}' \
    "$SID_FLOW" | "$CTX" prompt-dispatch
)
if ! echo "$OUT_FLOW_QUESTION" | grep -q "Recommended plugin for this task" \
   && echo "$OUT_FLOW_ACCEPT" \
     | grep -q "plugin-install experience-react --accept-proposed" \
   && echo "$OUT_FLOW_ACCEPT" | grep -qi "install immediately" \
   && ! echo "$OUT_FLOW_ACCEPT" | grep -q "Recommended plugin for this task" \
   && ! echo "$OUT_FLOW_ACCEPT" | grep -Eq \
     "/salesforce-development:plugin-install (experience-cms|dx-org-lifecycle)"; then
  PASS=$((PASS + 1)); printf '  ok   %-62s → locked React acceptance\n' \
    "SessionStart workflow survives question + terse acceptance"
else
  FAIL=$((FAIL + 1)); printf '  FAIL %-62s → question=%s acceptance=%s\n' \
    "SessionStart workflow survives question + terse acceptance" \
    "$OUT_FLOW_QUESTION" "$OUT_FLOW_ACCEPT"
fi

# A SessionStart proposal is recommendation-only. When a concrete task arrives,
# promote the matching candidate and surface it in the resumable task context,
# even though the proposal ledger already consumed first occurrence.
SID_PROMOTE="hint-cms-promote-$$"
run_hint "$CMS" "$SID_PROMOTE" >/dev/null
OUT_PROMPT=$(
  cd "$CMS" || exit 1
  printf '{"session_id":"%s","prompt_id":"p1","prompt":"I need to search Salesforce CMS for an existing media asset"}' \
    "$SID_PROMOTE" | "$CTX" prompt-dispatch
)
if echo "$OUT_PROMPT" | grep -q "Recommended plugin for this task" \
   && echo "$OUT_PROMPT" | grep -q "experience-cms" \
   && ! echo "$OUT_PROMPT" | grep -Eq "agentforce-adlc|experience-(lwc|react)"; then
  PASS=$((PASS + 1)); printf '  ok   %-62s → task-backed CMS recommendation\n' \
    "SessionStart proposal promotes the next concrete CMS task"
else
  FAIL=$((FAIL + 1)); printf '  FAIL %-62s → %s\n' \
    "SessionStart proposal promotes the next concrete CMS task" "$OUT_PROMPT"
fi

echo ""
echo "  $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
