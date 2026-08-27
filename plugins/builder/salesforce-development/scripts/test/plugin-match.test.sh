#!/bin/bash
# Decision test for `sf-context plugin-match` (Phase 3, consumer b).
#
# This is the explicit, on-demand discovery-command query: it renders the
# ranked uninstalled-plugin catalog matches for `<text>`, with no deny/warn
# semantics (there's no tool call to gate). It writes/updates the same
# session-scoped proposal marker the PreToolUse bypass gate (consumer a)
# reads, so a proposal surfaced here suppresses a redundant later deny for
# the same plugin in the same session. This test asserts, fully offline:
#   - a matching text renders the candidate list, never denies
#   - it writes the session marker with surface="discovery-command"
#   - a later same-session bypass-gate hit for the same plugin warns, not
#     denies (cross-surface dedup)
#   - a non-matching text renders an honest empty result, not an error
#
# Run: bash plugins/builder/salesforce-development/scripts/test/plugin-match.test.sh

set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CTX="$ROOT/sf-context"
PASS=0
FAIL=0

# Hermetic installed-plugin set (see skills-first-advisory.test.sh): pin agentforce-adlc
# as the sole uninstalled candidate so the render + empty-result assertions do not depend
# on the developer's real ~/.claude enabledPlugins.
CFG="$(mktemp -d)"
printf '{"enabledPlugins":{"experience-lwc@salesforce":true,"experience-react@salesforce":true}}' \
  > "$CFG/settings.json"
export CLAUDE_CONFIG_DIR="$CFG"
trap 'rm -rf "$CFG" "${PROJDIR:-}"' EXIT

HIGH_PROMPT="I need to author, discover, scaffold, deploy, test, secure, and optimize Agentforce .agent files for a new employee agent"
CMS_PROMPT="find a stock image for this Experience Cloud CMS page"
GENERIC_PROMPT="calculate seven factorial"
DEPLOY_BYPASS_CMD="sf project deploy start --source-dir force-app"

capture_prompt() {
  # capture_prompt <session_id> <prompt_id> <prompt-text>
  printf '{"session_id":"%s","prompt_id":"%s","prompt":"%s"}' "$1" "$2" "$3" \
    | "$CTX" prompt-dispatch >/dev/null
}

echo "sf-context plugin-match — decision (offline, no org)"

# --- a matching text renders the candidate list, never denies/warns --------
OUT_MATCH=$("$CTX" plugin-match --session-id "plugin-match-render-$$-$RANDOM" "$HIGH_PROMPT")
if echo "$OUT_MATCH" | grep -q "agentforce-adlc" \
   && echo "$OUT_MATCH" | grep -q "/salesforce-development:plugin-install agentforce-adlc" \
   && ! echo "$OUT_MATCH" | grep -qi '"permissionDecision"'; then
  PASS=$((PASS + 1)); printf '  ok   %-60s → renders candidate + install command, no deny\n' "matching text renders the candidate list"
else
  FAIL=$((FAIL + 1)); printf '  FAIL %-60s → %s\n' "matching text renders the candidate list" "$OUT_MATCH"
fi

# --- a CMS media prompt recommends the narrowed experience-cms plugin -------
OUT_CMS=$("$CTX" plugin-match --session-id "plugin-match-cms-$$-$RANDOM" "$CMS_PROMPT")
if echo "$OUT_CMS" | grep -q "experience-cms" \
   && echo "$OUT_CMS" | grep -q "/salesforce-development:plugin-install experience-cms" \
   && ! echo "$OUT_CMS" | grep -qi '"permissionDecision"'; then
  PASS=$((PASS + 1)); printf '  ok   %-60s → renders experience-cms + install command\n' "CMS media text recommends the narrowed plugin"
else
  FAIL=$((FAIL + 1)); printf '  FAIL %-60s → %s\n' "CMS media text recommends the narrowed plugin" "$OUT_CMS"
fi

# --- structured SessionStart consumer: high-only JSON + curated metadata ---
OUT_SESSION_JSON=$("$CTX" plugin-match --json --surface session-start \
  --session-id "plugin-match-session-$$-$RANDOM" "$CMS_PROMPT")
if printf '%s' "$OUT_SESSION_JSON" | python3 -c '
import json,sys
rows=json.load(sys.stdin).get("matches", [])
assert [row.get("name") for row in rows] == ["experience-cms"]
assert rows[0].get("band") == "high"
assert "stock" in rows[0].get("description", "").lower()
'; then
  PASS=$((PASS + 1)); printf '  ok   %-60s → structured high-confidence CMS match\n' "SessionStart JSON mode returns curated CMS metadata"
else
  FAIL=$((FAIL + 1)); printf '  FAIL %-60s → %s\n' "SessionStart JSON mode returns curated CMS metadata" "$OUT_SESSION_JSON"
fi

# --- explicit discovery routes each new product boundary at high confidence -
for match_case in \
  "dx-org-lifecycle|configure post-copy steps for my Salesforce sandbox refresh" \
  "dx-org-lifecycle|enable Dev Hub and show my scratch org allocation" \
  "dx-devops|configure a DevOps Center test pipeline" \
  "platform-trust-security|search Salesforce Archive for archived Account records" \
  "commerce-b2b|replace OOTB B2B Commerce definitions with mapped site equivalents" \
  "mobile-development|use lightning/mobileCapabilities to add native barcode scanner support" \
  "platform-observability|turn on TraceSpanEvent publishing with enablePlatformTracing" \
  "dx-isv-partner|AppAnalyticsQueryRequest PackageUsageSummary SubscriberSnapshot"; do
  expected="${match_case%%|*}"
  prompt="${match_case#*|}"
  OUT_TRANCHE=$("$CTX" plugin-match --json --surface discovery-command "$prompt")
  if printf '%s' "$OUT_TRANCHE" | python3 -c '
import json,sys
expected=sys.argv[1]
rows=json.load(sys.stdin).get("matches", [])
assert [row.get("name") for row in rows if row.get("band") == "high"] == [expected]
' "$expected"; then
    PASS=$((PASS + 1)); printf '  ok   %-60s → %s\n' "explicit discovery isolates ${expected}" "$expected"
  else
    FAIL=$((FAIL + 1)); printf '  FAIL %-60s → %s\n' "explicit discovery isolates ${expected}" "$OUT_TRANCHE"
  fi
done

# --- W-23856691 tranche 2: service-engagement, integration, ----------------
# platform-lightning-widgets, each isolated on a mandated positive example that
# has no pre-existing token overlap with another plugin's vocabulary.
for match_case in \
  "service-engagement|set up a Salesforce Digital Engagement messaging channel" \
  "integration|configure a Salesforce Connected App for OAuth" \
  "platform-lightning-widgets|generate a custom Salesforce Lightning Type"; do
  expected="${match_case%%|*}"
  prompt="${match_case#*|}"
  OUT_TRANCHE2=$("$CTX" plugin-match --json --surface discovery-command "$prompt")
  if printf '%s' "$OUT_TRANCHE2" | python3 -c '
import json,sys
expected=sys.argv[1]
rows=json.load(sys.stdin).get("matches", [])
assert [row.get("name") for row in rows if row.get("band") == "high"] == [expected]
' "$expected"; then
    PASS=$((PASS + 1)); printf '  ok   %-60s → %s\n' "explicit discovery isolates ${expected}" "$expected"
  else
    FAIL=$((FAIL + 1)); printf '  FAIL %-60s → %s\n' "explicit discovery isolates ${expected}" "$OUT_TRANCHE2"
  fi
done

# --- a non-matching text renders an honest empty result, not an error ------
OUT_EMPTY=$("$CTX" plugin-match --session-id "plugin-match-empty-$$-$RANDOM" "$GENERIC_PROMPT")
if echo "$OUT_EMPTY" | grep -qi "no matching"; then
  PASS=$((PASS + 1)); printf '  ok   %-60s → %s\n' "non-matching text renders honest empty result" "$OUT_EMPTY"
else
  FAIL=$((FAIL + 1)); printf '  FAIL %-60s → %s\n' "non-matching text renders honest empty result" "$OUT_EMPTY"
fi

# --- host session env records proposals without model-copied CLI args -------
SID_ENV="plugin-match-env-$$-$RANDOM"
OUT_NOSESSION=$(CLAUDE_CODE_SESSION_ID="$SID_ENV" "$CTX" plugin-match "$HIGH_PROMPT")
if echo "$OUT_NOSESSION" | grep -q "agentforce-adlc" \
   && CLAUDE_CODE_SESSION_ID="$SID_ENV" \
        "$CTX" plugin-install agentforce-adlc --decline >/dev/null 2>&1; then
  PASS=$((PASS + 1)); printf '  ok   %-60s → renders and records proposal\n' "session env replaces manually copied --session-id"
else
  FAIL=$((FAIL + 1)); printf '  FAIL %-60s → %s\n' "session env replaces manually copied --session-id" "$OUT_NOSESSION"
fi

# --- regression: a terminal (declined) flow must not silence later explicit --
# discovery for an unrelated plugin. $SID_ENV already reached "declined" for
# agentforce-adlc two blocks up; a fresh explicit query in that same session
# must still render, not silently return empty (this is render-only and has
# nothing to gate per docs/design/plugin-catalog.md).
OUT_AFTER_DECLINE=$(CLAUDE_CODE_SESSION_ID="$SID_ENV" "$CTX" plugin-match "$CMS_PROMPT")
if echo "$OUT_AFTER_DECLINE" | grep -q "experience-cms"; then
  PASS=$((PASS + 1)); printf '  ok   %-60s → still renders after same-session decline\n' "explicit discovery survives a terminal declined flow"
else
  FAIL=$((FAIL + 1)); printf '  FAIL %-60s → %s\n' "explicit discovery survives a terminal declined flow" "$OUT_AFTER_DECLINE"
fi

# --- cross-surface workflow lock: once a proposal is visible, a later ------
# same-session bypass gate must stay silent until the decision completes and a
# new substantive task releases the workflow.
echo ""
echo "  cross-surface dedup (with skills-first-advisory):"
# The bypass-gate (skills-first-advisory) only proposes plugins inside a Salesforce
# project, so run this section from a throwaway project dir. plugin-match itself is
# NOT project-gated (it is an explicit user query, so the render tests above are
# cwd-agnostic) — but the bypass-gate assertion below needs the gate open.
PROJDIR="$(mktemp -d)"
printf '{"packageDirectories":[{"path":"force-app","default":true}]}' > "$PROJDIR/sfdx-project.json"
cd "$PROJDIR" || exit 1
SID_CROSS="plugin-match-cross-$$-$RANDOM"
capture_prompt "$SID_CROSS" "p1" "$HIGH_PROMPT"
"$CTX" plugin-match --session-id "$SID_CROSS" "$HIGH_PROMPT" >/dev/null

parse_decision() {
  python3 -c "
import json,sys
d=json.load(sys.stdin)
hso=d.get('hookSpecificOutput',{})
decision=hso.get('permissionDecision')
ctx=hso.get('additionalContext','')
if decision:
    print('block' if decision=='deny' else decision)
elif ctx:
    print('warn')
else:
    print('quiet')
"
}

BYPASS_PAYLOAD="{\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"$DEPLOY_BYPASS_CMD\"},\"session_id\":\"$SID_CROSS\",\"prompt_id\":\"p1\"}"
GOT=$(printf '%s' "$BYPASS_PAYLOAD" | "$CTX" skills-first-advisory | parse_decision)
if [ "$GOT" = "quiet" ]; then
  PASS=$((PASS + 1)); printf '  ok   %-60s → %s\n' "same-session workflow suppresses bypass after plugin-match" "$GOT"
else
  FAIL=$((FAIL + 1)); printf '  FAIL %-60s → got "%s", expected "quiet"\n' "same-session workflow suppresses bypass after plugin-match" "$GOT"
fi

# A fresh live prompt now proposes on UserPromptSubmit before the first tool
# call. Its bypass gate is also silent while that choice remains active.
SID_FRESH="plugin-match-cross-fresh-$$-$RANDOM"
capture_prompt "$SID_FRESH" "p1" "$HIGH_PROMPT"
BYPASS_FRESH="{\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"$DEPLOY_BYPASS_CMD\"},\"session_id\":\"$SID_FRESH\",\"prompt_id\":\"p1\"}"
GOT_FRESH=$(printf '%s' "$BYPASS_FRESH" | "$CTX" skills-first-advisory | parse_decision)
if [ "$GOT_FRESH" = "quiet" ]; then
  PASS=$((PASS + 1)); printf '  ok   %-60s → %s\n' "a fresh prompt proposal suppresses later bypass text" "$GOT_FRESH"
else
  FAIL=$((FAIL + 1)); printf '  FAIL %-60s → got "%s", expected "quiet"\n' "a fresh prompt proposal suppresses later bypass text" "$GOT_FRESH"
fi

echo ""
echo "  $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
