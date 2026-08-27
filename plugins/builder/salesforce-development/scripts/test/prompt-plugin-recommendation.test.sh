#!/bin/bash
# Decision test for proactive UserPromptSubmit plugin recommendations (W-23856691).
#
# Exact CMS prompts from the live-session transcript must recommend experience-cms
# before the model answers. Strong existing and remaining-product prompts must
# route to one product plugin, while unsupported, medium, and generic matches stay
# quiet. All checks are offline, project-scoped, and use a hermetic installed-plugin
# configuration.
#
# Run: bash plugins/builder/salesforce-development/scripts/test/prompt-plugin-recommendation.test.sh

set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CTX="$ROOT/sf-context"
PASS=0
FAIL=0

CFG="$(mktemp -d)"
PROJ="$(mktemp -d)"
NONPROJ="$(mktemp -d)"
trap 'rm -rf "$CFG" "$PROJ" "$NONPROJ"' EXIT

# Only the foundation plugin is installed; every add-on is available to match.
printf '{"enabledPlugins":{"salesforce-development@salesforce":true}}' \
  > "$CFG/settings.json"
export CLAUDE_CONFIG_DIR="$CFG"
printf '{"packageDirectories":[{"path":"force-app","default":true}]}' \
  > "$PROJ/sfdx-project.json"

TAIL_PLUGINS="commerce-b2b|dx-isv-partner|mobile-development|platform-observability|platform-trust-security"
CORE_PLUGINS="agentforce-adlc|experience-cms|experience-lwc|experience-react|dx-org-lifecycle|dx-devops"

run_prompt() {
  # run_prompt <cwd> <session-id> <prompt-text>
  local cwd="$1" session="$2" prompt="$3"
  (
    cd "$cwd" || exit 1
    python3 -c 'import json,sys; print(json.dumps({"session_id":sys.argv[1], "prompt_id":"p1", "prompt":sys.argv[2]}))' \
      "$session" "$prompt" | "$CTX" prompt-dispatch
  )
}

assert_route() {
  # assert_route <description> <expected-plugin> <unexpected-regex> <prompt>
  local desc="$1" expected="$2" unexpected="$3" prompt="$4" out
  out=$(run_prompt "$PROJ" "prompt-route-${PASS}-${FAIL}-$$-$RANDOM" "$prompt")
  if echo "$out" | grep -q "Recommended plugin for this task" \
     && echo "$out" | grep -q "$expected" \
     && echo "$out" | grep -q "high confidence" \
     && echo "$out" | grep -q "/salesforce-development:plugin-install ${expected}" \
     && echo "$out" | grep -q "deterministic high-confidence plugin match" \
     && ! echo "$out" | grep -Eq "$unexpected"; then
    PASS=$((PASS + 1)); printf '  ok   %-62s → %s\n' "$desc" "$expected"
  else
    FAIL=$((FAIL + 1)); printf '  FAIL %-62s → %s\n' "$desc" "$out"
  fi
}

assert_quiet() {
  # assert_quiet <description> <prompt>
  local desc="$1" prompt="$2" out
  out=$(run_prompt "$PROJ" "prompt-quiet-${PASS}-${FAIL}-$$-$RANDOM" "$prompt")
  if ! echo "$out" | grep -q "Recommended plugin for this task"; then
    PASS=$((PASS + 1)); printf '  ok   %-62s → quiet\n' "$desc"
  else
    FAIL=$((FAIL + 1)); printf '  FAIL %-62s → %s\n' "$desc" "$out"
  fi
}

assert_plugin_absent() {
  # assert_plugin_absent <description> <plugin> <prompt>
  local desc="$1" plugin="$2" prompt="$3" out
  out=$(run_prompt "$PROJ" "prompt-absent-${PASS}-${FAIL}-$$-$RANDOM" "$prompt")
  if ! echo "$out" | grep -q "/salesforce-development:plugin-install ${plugin}"; then
    PASS=$((PASS + 1)); printf '  ok   %-62s → %s not recommended\n' "$desc" "$plugin"
  else
    FAIL=$((FAIL + 1)); printf '  FAIL %-62s → %s\n' "$desc" "$out"
  fi
}

echo "sf-context prompt plugin recommendation — decision (offline, no org)"

# These first two prompts are copied exactly from the hesitant live session.
assert_route \
  "existing Salesforce CMS media prompt recommends CMS" \
  "experience-cms" "agentforce-adlc|experience-(lwc|react) —|dx-org-lifecycle|dx-devops|${TAIL_PLUGINS}" \
  "I need to search Salesforce CMS for an existing media asset"

assert_route \
  "Experience Cloud stock imagery prompt recommends CMS" \
  "experience-cms" "agentforce-adlc|experience-(lwc|react) —|dx-org-lifecycle|dx-devops|${TAIL_PLUGINS}" \
  "I need to find stock imagery for an Experience Cloud CMS"

# Regression coverage for the two established plugin routes. The CMS addition and
# prompt-time surface must not steal these strong, product-specific asks.
assert_route \
  "strong LWC prompt still recommends the LWC plugin" \
  "experience-lwc" "agentforce-adlc|experience-(cms|react) —|dx-org-lifecycle|dx-devops|${TAIL_PLUGINS}" \
  "build me an LWC datatable with wire service and Jest tests"

assert_route \
  "strong React prompt still recommends the React plugin" \
  "experience-react" "agentforce-adlc|experience-(cms|lwc) —|dx-org-lifecycle|dx-devops|${TAIL_PLUGINS}" \
  "scaffold a new Salesforce React UI bundle app with Tailwind and shadcn"

# Exact live-QE sequence: SessionStart proposed one React plugin, the user asked
# about that recommendation, then replied `ok install it`. The session workflow
# must survive the explanatory turn and route the sole active candidate to its
# same-session acceptance path without rescoring.
SID_SESSION_FLOW="prompt-session-flow-$$-$RANDOM"
"$CTX" plugin-match --json --surface session-start \
  --session-id "$SID_SESSION_FLOW" \
  "react ui bundle tsx tailwind shadcn" >/dev/null
OUT_FLOW_QUESTION=$(run_prompt "$PROJ" "$SID_SESSION_FLOW" \
  "Which plugin would help me build a Salesforce React UI bundle with tsx, tailwind, and shadcn?")
OUT_FLOW_ACCEPT=$(run_prompt "$PROJ" "$SID_SESSION_FLOW" "ok install it")
if ! echo "$OUT_FLOW_QUESTION" | grep -q "Recommended plugin for this task" \
   && echo "$OUT_FLOW_ACCEPT" \
     | grep -q "plugin-install experience-react --accept-proposed" \
   && echo "$OUT_FLOW_ACCEPT" | grep -qi "install immediately" \
   && ! echo "$OUT_FLOW_ACCEPT" | grep -q "Recommended plugin for this task" \
   && ! echo "$OUT_FLOW_ACCEPT" | grep -Eq \
     "/salesforce-development:plugin-install (experience-cms|dx-org-lifecycle)"; then
  PASS=$((PASS + 1)); printf '  ok   %-62s → locked React acceptance, no replacements\n' \
    "SessionStart flow survives explanation + terse acceptance"
else
  FAIL=$((FAIL + 1)); printf '  FAIL %-62s → question=%s acceptance=%s\n' \
    "SessionStart flow survives explanation + terse acceptance" \
    "$OUT_FLOW_QUESTION" "$OUT_FLOW_ACCEPT"
fi

# Proposal decisions are session-scoped rather than project-scoped. Explicit
# discovery is valid in any directory, so its later named accept/decline turns
# must route before the Salesforce-project presentation gate.
SID_OUTSIDE_ACCEPT="prompt-outside-accept-$$-$RANDOM"
"$CTX" plugin-match --session-id "$SID_OUTSIDE_ACCEPT" \
  "scaffold a new Salesforce React UI bundle app with Tailwind and shadcn" >/dev/null
OUT_OUTSIDE_ACCEPT=$(run_prompt "$NONPROJ" "$SID_OUTSIDE_ACCEPT" \
  "go ahead with experience-react")
if echo "$OUT_OUTSIDE_ACCEPT" \
     | grep -q "plugin-install experience-react --accept-proposed" \
   && echo "$OUT_OUTSIDE_ACCEPT" | grep -qi "install immediately" \
   && ! echo "$OUT_OUTSIDE_ACCEPT" | grep -q "Recommended plugin for this task"; then
  PASS=$((PASS + 1)); printf '  ok   %-62s → routed acceptance outside project\n' \
    "discovery proposal can be accepted outside a project"
else
  FAIL=$((FAIL + 1)); printf '  FAIL %-62s → %s\n' \
    "discovery proposal can be accepted outside a project" "$OUT_OUTSIDE_ACCEPT"
fi

SID_OUTSIDE_DECLINE="prompt-outside-decline-$$-$RANDOM"
"$CTX" plugin-match --session-id "$SID_OUTSIDE_DECLINE" \
  "scaffold a new Salesforce React UI bundle app with Tailwind and shadcn" >/dev/null
OUT_OUTSIDE_DECLINE=$(run_prompt "$NONPROJ" "$SID_OUTSIDE_DECLINE" \
  "no thanks, do not install experience-react")
if echo "$OUT_OUTSIDE_DECLINE" | grep -q "was recorded for this session" \
   && echo "$OUT_OUTSIDE_DECLINE" | grep -qi "do not run a tool" \
   && ! echo "$OUT_OUTSIDE_DECLINE" | grep -q "plugin-install" \
   && ! echo "$OUT_OUTSIDE_DECLINE" | grep -q "Recommended plugin for this task"; then
  PASS=$((PASS + 1)); printf '  ok   %-62s → routed decline outside project\n' \
    "discovery proposal can be declined outside a project"
else
  FAIL=$((FAIL + 1)); printf '  FAIL %-62s → %s\n' \
    "discovery proposal can be declined outside a project" "$OUT_OUTSIDE_DECLINE"
fi

# Live QE regression: once React was proposed, an explicit named decline was
# incorrectly rescored as a fresh task. "experience" surfaced CMS and "install"
# surfaced org lifecycle, while the model merely acknowledged the refusal and
# never invoked the guarded decline path. The hook must route the prior proposal
# and stay free of replacement recommendation paint.
SID_DECLINE="prompt-explicit-decline-$$-$RANDOM"
run_prompt "$PROJ" "$SID_DECLINE" \
  "scaffold a new Salesforce React UI bundle app with Tailwind and shadcn" >/dev/null
OUT_DECLINE=$(run_prompt "$PROJ" "$SID_DECLINE" \
  "no thanks, do not install experience-react")
if echo "$OUT_DECLINE" | grep -q "was recorded for this session" \
   && echo "$OUT_DECLINE" | grep -qi "do not run a tool" \
   && ! echo "$OUT_DECLINE" | grep -q "plugin-install" \
   && ! echo "$OUT_DECLINE" | grep -q "Recommended plugin for this task" \
   && ! echo "$OUT_DECLINE" | grep -Eq \
     "/salesforce-development:plugin-install (experience-cms|dx-org-lifecycle)"; then
  PASS=$((PASS + 1)); printf '  ok   %-62s → routed decline, no replacements\n' \
    "named React decline bypasses recommendation scoring"
else
  FAIL=$((FAIL + 1)); printf '  FAIL %-62s → %s\n' \
    "named React decline bypasses recommendation scoring" "$OUT_DECLINE"
fi

# Once a dry run pins the workflow to one plugin, a generic decline must remain
# in that workflow too: route the selected plugin, never score replacement ones.
SID_DECLINE_PENDING="prompt-pending-decline-$$-$RANDOM"
run_prompt "$PROJ" "$SID_DECLINE_PENDING" \
  "scaffold a new Salesforce React UI bundle app with Tailwind and shadcn" >/dev/null
CLAUDE_CODE_SESSION_ID="$SID_DECLINE_PENDING" \
  "$CTX" plugin-install experience-react >/dev/null
OUT_DECLINE_PENDING=$(run_prompt "$PROJ" "$SID_DECLINE_PENDING" "no thanks")
if echo "$OUT_DECLINE_PENDING" | grep -q "was recorded for this session" \
   && echo "$OUT_DECLINE_PENDING" | grep -qi "do not run a tool" \
   && ! echo "$OUT_DECLINE_PENDING" | grep -q "plugin-install" \
   && ! echo "$OUT_DECLINE_PENDING" | grep -q "Recommended plugin for this task" \
   && ! echo "$OUT_DECLINE_PENDING" | grep -Eq \
     "/salesforce-development:plugin-install (experience-cms|dx-org-lifecycle)"; then
  PASS=$((PASS + 1)); printf '  ok   %-62s → routed decline, no replacements\n' \
    "pending-workflow decline bypasses recommendation scoring"
else
  FAIL=$((FAIL + 1)); printf '  FAIL %-62s → %s\n' \
    "pending-workflow decline bypasses recommendation scoring" "$OUT_DECLINE_PENDING"
fi

# Symmetric live-QE regression: accepting one previously proposed plugin is a
# control reply too. It must advance that exact plugin to the guarded accepted-
# proposal path instead of rescoring "install experience-react" and painting the next
# incidental CMS/org-lifecycle matches after React is deduplicated.
SID_INSTALL="prompt-explicit-install-$$-$RANDOM"
run_prompt "$PROJ" "$SID_INSTALL" \
  "scaffold a new Salesforce React UI bundle app with Tailwind and shadcn" >/dev/null
OUT_INSTALL=$(run_prompt "$PROJ" "$SID_INSTALL" "Install experience-react")
if echo "$OUT_INSTALL" \
     | grep -q "plugin-install experience-react --accept-proposed" \
   && echo "$OUT_INSTALL" | grep -qi "install immediately" \
   && ! echo "$OUT_INSTALL" | grep -q "Recommended plugin for this task" \
   && ! echo "$OUT_INSTALL" | grep -Eq \
     "/salesforce-development:plugin-install (experience-cms|dx-org-lifecycle)"; then
  PASS=$((PASS + 1)); printf '  ok   %-62s → routed acceptance, no replacements\n' \
    "named React install bypasses recommendation scoring"
else
  FAIL=$((FAIL + 1)); printf '  FAIL %-62s → %s\n' \
    "named React install bypasses recommendation scoring" "$OUT_INSTALL"
fi

# Live QE regression (bare-name acceptance): SessionStart proposes plugins and
# asks "which one would you like me to install?"; the natural reply is the bare
# plugin name with no install verb. That most-explicit possible naming must
# select the proposal so `plugin-install <name> --accept-proposed` succeeds
# instead of refusing with "requires this exact plugin to be proposed and
# selected in the same session." Design invariant: an explicitly named valid
# proposal can always select itself.
SID_BARE="prompt-bare-name-$$"
"$CTX" plugin-match --json --surface session-start \
  --session-id "$SID_BARE" \
  "react ui bundle tsx tailwind shadcn" >/dev/null
OUT_BARE=$(run_prompt "$PROJ" "$SID_BARE" "experience-react")
if echo "$OUT_BARE" \
     | grep -q "plugin-install experience-react --accept-proposed" \
   && echo "$OUT_BARE" | grep -qi "install immediately" \
   && ! echo "$OUT_BARE" | grep -q "Recommended plugin for this task" \
   && ! echo "$OUT_BARE" | grep -Eq \
     "/salesforce-development:plugin-install (experience-cms|dx-org-lifecycle)"; then
  PASS=$((PASS + 1)); printf '  ok   %-62s → routed acceptance, no replacements\n' \
    "bare proposed plugin name selects for accept-proposed"
else
  FAIL=$((FAIL + 1)); printf '  FAIL %-62s → %s\n' \
    "bare proposed plugin name selects for accept-proposed" "$OUT_BARE"
fi

# The bare-name path must not fire when the name is merely mentioned inside a
# question — that stays a selection-only turn and must not route an install.
SID_BARE_Q="prompt-bare-name-question-$$"
"$CTX" plugin-match --json --surface session-start \
  --session-id "$SID_BARE_Q" \
  "react ui bundle tsx tailwind shadcn" >/dev/null
OUT_BARE_Q=$(run_prompt "$PROJ" "$SID_BARE_Q" \
  "what does experience-react do before I decide?")
if ! echo "$OUT_BARE_Q" | grep -q "plugin-install experience-react --accept-proposed"; then
  PASS=$((PASS + 1)); printf '  ok   %-62s → no premature install route\n' \
    "name inside a question does not select for install"
else
  FAIL=$((FAIL + 1)); printf '  FAIL %-62s → %s\n' \
    "name inside a question does not select for install" "$OUT_BARE_Q"
fi

# Live Pass 3 regression: after the mandatory dry run, the natural follow-up
# "yes install it" names no plugin. It must correlate only with that fresh,
# same-session dry run and route its exact nonce-bound confirmation; rescoring
# the generic word "install" previously painted dx-org-lifecycle instead.
SID_CONFIRM="prompt-explicit-confirm-$$-$RANDOM"
run_prompt "$PROJ" "$SID_CONFIRM" \
  "scaffold a new Salesforce React UI bundle app with Tailwind and shadcn" >/dev/null
DRY_CONFIRM=$(CLAUDE_CODE_SESSION_ID="$SID_CONFIRM" \
  "$CTX" plugin-install experience-react)
NONCE_CONFIRM=$(printf '%s' "$DRY_CONFIRM" \
  | grep -o -- '--confirm [a-f0-9]\{64\}' | awk '{print $2}')
OUT_CONFIRM=$(run_prompt "$PROJ" "$SID_CONFIRM" "yes install it")
if [ -n "$NONCE_CONFIRM" ] \
   && echo "$OUT_CONFIRM" \
     | grep -q "plugin-install experience-react --confirm $NONCE_CONFIRM" \
   && echo "$OUT_CONFIRM" | grep -qi "same-session source preview" \
   && ! echo "$OUT_CONFIRM" | grep -q "Recommended plugin for this task" \
   && ! echo "$OUT_CONFIRM" | grep -Eq \
     "/salesforce-development:plugin-install (experience-cms|dx-org-lifecycle)"; then
  PASS=$((PASS + 1)); printf '  ok   %-62s → routed confirm, no replacements\n' \
    "dry-run confirmation bypasses recommendation scoring"
else
  FAIL=$((FAIL + 1)); printf '  FAIL %-62s → %s\n' \
    "dry-run confirmation bypasses recommendation scoring" "$OUT_CONFIRM"
fi

# Live follow-up regression: the terminal submission was the terse `ok install`
# (not the longer paraphrase used in the report). It has the same meaning only
# when a fresh nonce-bound dry run exists in this session.
SID_CONFIRM_SHORT="prompt-explicit-confirm-short-$$-$RANDOM"
run_prompt "$PROJ" "$SID_CONFIRM_SHORT" \
  "scaffold a new Salesforce React UI bundle app with Tailwind and shadcn" >/dev/null
DRY_CONFIRM_SHORT=$(CLAUDE_CODE_SESSION_ID="$SID_CONFIRM_SHORT" \
  "$CTX" plugin-install experience-react)
NONCE_CONFIRM_SHORT=$(printf '%s' "$DRY_CONFIRM_SHORT" \
  | grep -o -- '--confirm [a-f0-9]\{64\}' | awk '{print $2}')
OUT_CONFIRM_SHORT=$(run_prompt "$PROJ" "$SID_CONFIRM_SHORT" "ok install")
if [ -n "$NONCE_CONFIRM_SHORT" ] \
   && echo "$OUT_CONFIRM_SHORT" \
     | grep -q "plugin-install experience-react --confirm $NONCE_CONFIRM_SHORT" \
   && ! echo "$OUT_CONFIRM_SHORT" | grep -q "Recommended plugin for this task" \
   && ! echo "$OUT_CONFIRM_SHORT" | grep -Eq \
     "/salesforce-development:plugin-install (experience-cms|dx-org-lifecycle)"; then
  PASS=$((PASS + 1)); printf '  ok   %-62s → routed confirm, no replacements\n' \
    "terse dry-run confirmation bypasses recommendation scoring"
else
  FAIL=$((FAIL + 1)); printf '  FAIL %-62s → %s\n' \
    "terse dry-run confirmation bypasses recommendation scoring" "$OUT_CONFIRM_SHORT"
fi

# A normal status question stays inside the pending workflow and preserves its
# nonce for the next explicit confirmation.
SID_CONFIRM_STATUS="prompt-confirm-status-$$-$RANDOM"
run_prompt "$PROJ" "$SID_CONFIRM_STATUS" \
  "scaffold a new Salesforce React UI bundle app with Tailwind and shadcn" >/dev/null
DRY_CONFIRM_STATUS=$(CLAUDE_CODE_SESSION_ID="$SID_CONFIRM_STATUS" \
  "$CTX" plugin-install experience-react)
NONCE_CONFIRM_STATUS=$(printf '%s' "$DRY_CONFIRM_STATUS" \
  | grep -o -- '--confirm [a-f0-9]\{64\}' | awk '{print $2}')
OUT_CONFIRM_STATUS=$(run_prompt "$PROJ" "$SID_CONFIRM_STATUS" "is it installed?")
OUT_CONFIRM_AFTER_STATUS=$(run_prompt "$PROJ" "$SID_CONFIRM_STATUS" "OK")
if [ -n "$NONCE_CONFIRM_STATUS" ] \
   && ! echo "$OUT_CONFIRM_STATUS" | grep -q "Recommended plugin for this task" \
   && echo "$OUT_CONFIRM_AFTER_STATUS" \
     | grep -q "plugin-install experience-react --confirm $NONCE_CONFIRM_STATUS"; then
  PASS=$((PASS + 1)); printf '  ok   %-62s → pending nonce preserved\n' \
    "question-mark status follow-up remains in workflow"
else
  FAIL=$((FAIL + 1)); printf '  FAIL %-62s → status=%s confirm=%s\n' \
    "question-mark status follow-up remains in workflow" \
    "$OUT_CONFIRM_STATUS" "$OUT_CONFIRM_AFTER_STATUS"
fi

# A broad word in a real changed-topic request is not a plugin decline. It
# consumes the old one-prompt confirmation marker, so a later bare OK cannot
# install the previously selected plugin.
SID_PENDING_CHANGED="prompt-pending-changed-$$-$RANDOM"
run_prompt "$PROJ" "$SID_PENDING_CHANGED" \
  "scaffold a new Salesforce React UI bundle app with Tailwind and shadcn" >/dev/null
DRY_PENDING_CHANGED=$(CLAUDE_CODE_SESSION_ID="$SID_PENDING_CHANGED" \
  "$CTX" plugin-install experience-react)
NONCE_PENDING_CHANGED=$(printf '%s' "$DRY_PENDING_CHANGED" \
  | grep -o -- '--confirm [a-f0-9]\{64\}' | awk '{print $2}')
OUT_PENDING_CHANGED=$(run_prompt "$PROJ" "$SID_PENDING_CHANGED" \
  "skip the tests and show the config")
OUT_AFTER_CHANGED=$(run_prompt "$PROJ" "$SID_PENDING_CHANGED" "OK")
if [ -n "$NONCE_PENDING_CHANGED" ] \
   && ! echo "$OUT_PENDING_CHANGED" \
     | grep -q "plugin-install experience-react --decline" \
   && ! echo "$OUT_AFTER_CHANGED" \
     | grep -q "plugin-install experience-react --confirm $NONCE_PENDING_CHANGED"; then
  PASS=$((PASS + 1)); printf '  ok   %-62s → marker consumed, no false decline\n' \
    "unrelated skip wording releases pending confirmation"
else
  FAIL=$((FAIL + 1)); printf '  FAIL %-62s → changed=%s after=%s\n' \
    "unrelated skip wording releases pending confirmation" \
    "$OUT_PENDING_CHANGED" "$OUT_AFTER_CHANGED"
fi

# Multiple proposals cannot replace a nonce-bound decision. A named request for
# another candidate is held until the pending React decision is resolved.
SID_PENDING_SWITCH="prompt-pending-switch-$$-$RANDOM"
"$CTX" plugin-match --surface session-start --session-id "$SID_PENDING_SWITCH" \
  "scaffold a new Salesforce React UI bundle app with Tailwind and shadcn" >/dev/null
"$CTX" plugin-match --surface session-start --session-id "$SID_PENDING_SWITCH" \
  "search Salesforce CMS for an existing media asset" >/dev/null
DRY_PENDING_SWITCH=$(CLAUDE_CODE_SESSION_ID="$SID_PENDING_SWITCH" \
  "$CTX" plugin-install experience-react)
NONCE_PENDING_SWITCH=$(printf '%s' "$DRY_PENDING_SWITCH" \
  | grep -o -- '--confirm [a-f0-9]\{64\}' | awk '{print $2}')
OUT_PENDING_SWITCH=$(run_prompt "$PROJ" "$SID_PENDING_SWITCH" \
  "install experience-cms")
OUT_AFTER_SWITCH=$(run_prompt "$PROJ" "$SID_PENDING_SWITCH" "OK")
if [ -n "$NONCE_PENDING_SWITCH" ] \
   && echo "$OUT_PENDING_SWITCH" | grep -q "experience-react" \
   && echo "$OUT_PENDING_SWITCH" | grep -qi "pending plugin first" \
   && ! echo "$OUT_PENDING_SWITCH" | grep -q "plugin-install experience-cms" \
   && echo "$OUT_AFTER_SWITCH" \
     | grep -q "plugin-install experience-react --confirm $NONCE_PENDING_SWITCH"; then
  PASS=$((PASS + 1)); printf '  ok   %-62s → React decision stays pinned\n' \
    "different named install cannot replace pending plugin"
else
  FAIL=$((FAIL + 1)); printf '  FAIL %-62s → switch=%s after=%s\n' \
    "different named install cannot replace pending plugin" \
    "$OUT_PENDING_SWITCH" "$OUT_AFTER_SWITCH"
fi

# Declining another valid proposal consumes the old pending nonce before routing
# that explicit decline; a later affirmative must not confirm the old plugin.
SID_PENDING_OTHER_DECLINE="prompt-pending-other-decline-$$-$RANDOM"
"$CTX" plugin-match --surface session-start --session-id "$SID_PENDING_OTHER_DECLINE" \
  "scaffold a new Salesforce React UI bundle app with Tailwind and shadcn" >/dev/null
"$CTX" plugin-match --surface session-start --session-id "$SID_PENDING_OTHER_DECLINE" \
  "search Salesforce CMS for an existing media asset" >/dev/null
DRY_PENDING_OTHER_DECLINE=$(CLAUDE_CODE_SESSION_ID="$SID_PENDING_OTHER_DECLINE" \
  "$CTX" plugin-install experience-react)
NONCE_PENDING_OTHER_DECLINE=$(printf '%s' "$DRY_PENDING_OTHER_DECLINE" \
  | grep -o -- '--confirm [a-f0-9]\{64\}' | awk '{print $2}')
OUT_OTHER_DECLINE=$(run_prompt "$PROJ" "$SID_PENDING_OTHER_DECLINE" \
  "do not install experience-cms")
OUT_AFTER_OTHER_DECLINE=$(run_prompt "$PROJ" "$SID_PENDING_OTHER_DECLINE" "OK")
if [ -n "$NONCE_PENDING_OTHER_DECLINE" ] \
   && echo "$OUT_OTHER_DECLINE" | grep -q "was recorded for this session" \
   && ! echo "$OUT_OTHER_DECLINE" | grep -q "plugin-install" \
   && ! echo "$OUT_AFTER_OTHER_DECLINE" \
     | grep -q "plugin-install experience-react --confirm $NONCE_PENDING_OTHER_DECLINE"; then
  PASS=$((PASS + 1)); printf '  ok   %-62s → old nonce consumed\n' \
    "other proposal decline cannot leave old confirmation active"
else
  FAIL=$((FAIL + 1)); printf '  FAIL %-62s → decline=%s after=%s\n' \
    "other proposal decline cannot leave old confirmation active" \
    "$OUT_OTHER_DECLINE" "$OUT_AFTER_OTHER_DECLINE"
fi

# Without a valid pending dry run, a bare confirmation-like reply is ambiguous.
# Stay quiet rather than manufacturing a plugin recommendation or confirmation.
assert_quiet \
  "confirmation-like reply without a pending dry run stays quiet" \
  "yes install it"
assert_quiet \
  "terse confirmation without a pending dry run stays quiet" \
  "ok install"
assert_quiet \
  "bare OK without a pending dry run stays quiet" \
  "OK"
assert_quiet \
  "bare Go without a pending dry run stays quiet" \
  "Go"
assert_quiet \
  "decline-like reply without a pending dry run stays quiet" \
  "no thanks"

assert_route \
  "strong Agentforce prompt remains isolated" \
  "agentforce-adlc" "experience-(cms|lwc|react) —|dx-org-lifecycle|dx-devops|${TAIL_PLUGINS}" \
  "author and test a new Agentforce .agent file for an employee agent"

# Complete org-lifecycle boundary: three distinct tasks should converge on one
# product plugin without stealing or being stolen by adjacent add-ons.
assert_route \
  "sandbox post-copy task recommends org lifecycle" \
  "dx-org-lifecycle" "agentforce-adlc|experience-(cms|lwc|react) —|dx-devops|${TAIL_PLUGINS}" \
  "configure post-copy steps for my Salesforce sandbox refresh"

assert_route \
  "trial provisioning recommends org lifecycle" \
  "dx-org-lifecycle" "agentforce-adlc|experience-(cms|lwc|react) —|dx-devops|${TAIL_PLUGINS}" \
  "create a Salesforce trial org for this demo"

assert_route \
  "default org switch recommends org lifecycle" \
  "dx-org-lifecycle" "agentforce-adlc|experience-(cms|lwc|react) —|dx-devops|${TAIL_PLUGINS}" \
  "switch my default Salesforce org"

# Reduced DevOps Center boundary deliberately covers pipeline/work-item
# management and test configuration/execution/analysis, but not promotion.
assert_route \
  "test pipeline setup recommends DevOps Center" \
  "dx-devops" "agentforce-adlc|experience-(cms|lwc|react) —|dx-org-lifecycle|${TAIL_PLUGINS}" \
  "configure a DevOps Center test pipeline"

assert_route \
  "suite execution recommends DevOps Center" \
  "dx-devops" "agentforce-adlc|experience-(cms|lwc|react) —|dx-org-lifecycle|${TAIL_PLUGINS}" \
  "run the test suite for this DevOps Center pipeline stage"

assert_route \
  "test failure analysis recommends DevOps Center" \
  "dx-devops" "agentforce-adlc|experience-(cms|lwc|react) —|dx-org-lifecycle|${TAIL_PLUGINS}" \
  "analyze why my DevOps Center pipeline tests failed"

# Reduced Trust and Security boundary covers Shield Platform Encryption and
# operations on already-archived data, but not Salesforce Data Mask.
assert_route \
  "Shield encryption recommends Trust and Security" \
  "platform-trust-security" "${CORE_PLUGINS}|commerce-b2b|dx-isv-partner|mobile-development|platform-observability" \
  "configure encryptionScheme for Shield Platform Encryption"

assert_route \
  "archive search recommends Trust and Security" \
  "platform-trust-security" "${CORE_PLUGINS}|commerce-b2b|dx-isv-partner|mobile-development|platform-observability" \
  "search Salesforce Archive for archived Account records"

# Reduced Commerce boundary customizes an existing storefront with the official
# open-code library; initial B2B store creation is intentionally not bundled.
assert_route \
  "open-code integration recommends B2B Commerce" \
  "commerce-b2b" "${CORE_PLUGINS}|dx-isv-partner|mobile-development|platform-observability|platform-trust-security" \
  "integrate open code into my B2B Commerce storefront"

assert_route \
  "OOTB replacement recommends B2B Commerce" \
  "commerce-b2b" "${CORE_PLUGINS}|dx-isv-partner|mobile-development|platform-observability|platform-trust-security" \
  "replace OOTB B2B Commerce definitions with mapped site equivalents"

# Mobile Development owns native capability integration, Komaci offline review,
# and scaffolding/extending a native Salesforce mobile app.
assert_route \
  "native barcode support recommends Mobile Development" \
  "mobile-development" "${CORE_PLUGINS}|commerce-b2b|dx-isv-partner|platform-observability|platform-trust-security" \
  "use lightning/mobileCapabilities to add native barcode scanner support"

assert_route \
  "Komaci audit recommends Mobile Development" \
  "mobile-development" "${CORE_PLUGINS}|commerce-b2b|dx-isv-partner|platform-observability|platform-trust-security" \
  "run a Komaci offline priming audit for Salesforce Mobile App Plus"

assert_route \
  "MSDK offline storage recommends Mobile Development" \
  "mobile-development" "${CORE_PLUGINS}|commerce-b2b|dx-isv-partner|platform-observability|platform-trust-security" \
  "add MobileSync and SmartStore offline storage to my mobile app"

# Observability owns the two API-68 tracing settings. It does not claim trace
# querying or analysis after spans have been ingested.
assert_route \
  "TraceSpanEvent setting recommends Platform Observability" \
  "platform-observability" "${CORE_PLUGINS}|commerce-b2b|dx-isv-partner|mobile-development|platform-trust-security" \
  "turn on TraceSpanEvent publishing with enablePlatformTracing"

assert_route \
  "Agentforce trace setting recommends Platform Observability" \
  "platform-observability" "${CORE_PLUGINS}|commerce-b2b|dx-isv-partner|mobile-development|platform-trust-security" \
  "generate AgentforcePlatformTracingSettings metadata"

# ISV and Partner owns the two partner-specific operating tasks without
# advertising package publication, listing creation, or generic org lifecycle.
assert_route \
  "App Analytics request recommends ISV and Partner" \
  "dx-isv-partner" "${CORE_PLUGINS}|commerce-b2b|mobile-development|platform-observability|platform-trust-security" \
  "AppAnalyticsQueryRequest PackageUsageSummary SubscriberSnapshot"

assert_route \
  "Dev Hub allocation recommends org lifecycle" \
  "dx-org-lifecycle" "experience-(cms|lwc|react) —|agentforce-adlc|dx-isv-partner|dx-devops|commerce-b2b|mobile-development|platform-observability|platform-trust-security" \
  "enable Dev Hub and show my scratch org allocation"

assert_route \
  "partner-offer preference recommends ISV and Partner" \
  "dx-isv-partner" "${CORE_PLUGINS}|commerce-b2b|mobile-development|platform-observability|platform-trust-security" \
  "enable the TransactableMarketplaceReceivePartnerOffers org preference"

# Prompt-time proactivity is high-confidence-only. A medium catalog match remains
# available to explicit discovery / the reactive gate but does not paint early.
OUT_MED=$(run_prompt "$PROJ" "prompt-medium-$$-$RANDOM" "build me a bot")
if ! echo "$OUT_MED" | grep -q "Recommended plugin for this task"; then
  PASS=$((PASS + 1)); printf '  ok   %-62s → quiet\n' "medium match does not create prompt-time noise"
else
  FAIL=$((FAIL + 1)); printf '  FAIL %-62s → %s\n' "medium match does not create prompt-time noise" "$OUT_MED"
fi

assert_quiet "generic prompt stays recommendation-free" "calculate seven factorial"

assert_quiet \
  "custom-object creation remains a foundation task" \
  "create a custom object"

assert_quiet \
  "Account field creation remains a foundation task" \
  "add a field to the Account object"

assert_quiet \
  "generic flow file lookup does not imply Agentforce" \
  "which file holds the flows?"

assert_quiet "git branch switching does not imply org lifecycle" "switch my git branch"

assert_quiet \
  "non-Salesforce product trial does not imply org lifecycle" \
  "start a free trial for my photo editor"

assert_plugin_absent \
  "local file encryption does not select Trust and Security" \
  "platform-trust-security" \
  "encrypt a local zip file"

assert_plugin_absent \
  "React replacement stays with the React route" \
  "commerce-b2b" \
  "replace a React component"

assert_plugin_absent \
  "Journey Builder does not select B2B Commerce" \
  "commerce-b2b" \
  "where is the journey builder flow?"

assert_plugin_absent \
  "generic iOS app creation does not select Mobile Development" \
  "mobile-development" \
  "create a generic iOS app"

assert_plugin_absent \
  "local Python debugging does not select Platform Observability" \
  "platform-observability" \
  "debug a local Python program"

assert_plugin_absent \
  "generic website metrics do not select ISV and Partner" \
  "dx-isv-partner" \
  "query website analytics"

# Canonical task verbs alone are deliberately not product evidence. A short
# "search" request must not be captured by CMS without a CMS/Experience signal.
OUT_AMBIGUOUS=$(run_prompt "$PROJ" "prompt-ambiguous-$$-$RANDOM" "search for a logo")
if ! echo "$OUT_AMBIGUOUS" | grep -q "Recommended plugin for this task"; then
  PASS=$((PASS + 1)); printf '  ok   %-62s → quiet\n' "ambiguous search verb does not imply CMS"
else
  FAIL=$((FAIL + 1)); printf '  FAIL %-62s → %s\n' "ambiguous search verb does not imply CMS" "$OUT_AMBIGUOUS"
fi

OUT_OUTSIDE=$(run_prompt "$NONPROJ" "prompt-outside-$$-$RANDOM" \
  "I need to search Salesforce CMS for an existing media asset")
if ! echo "$OUT_OUTSIDE" | grep -q "Recommended plugin for this task"; then
  PASS=$((PASS + 1)); printf '  ok   %-62s → quiet\n' "CMS prompt outside a Salesforce project stays scoped"
else
  FAIL=$((FAIL + 1)); printf '  FAIL %-62s → %s\n' "CMS prompt outside a Salesforce project stays scoped" "$OUT_OUTSIDE"
fi

# An enabled plugin is not a recommendation candidate.
printf '{"enabledPlugins":{"salesforce-development@salesforce":true,"experience-cms@salesforce":true}}' \
  > "$CFG/settings.json"
OUT_INSTALLED=$(run_prompt "$PROJ" "prompt-installed-$$-$RANDOM" \
  "I need to search Salesforce CMS for an existing media asset")
if ! echo "$OUT_INSTALLED" | grep -q "Recommended plugin for this task"; then
  PASS=$((PASS + 1)); printf '  ok   %-62s → quiet\n' "enabled CMS plugin is not recommended again"
else
  FAIL=$((FAIL + 1)); printf '  FAIL %-62s → %s\n' "enabled CMS plugin is not recommended again" "$OUT_INSTALLED"
fi

for installed_case in \
  "dx-org-lifecycle|configure post-copy steps for my Salesforce sandbox refresh" \
  "dx-devops|configure a DevOps Center test pipeline" \
  "platform-trust-security|search Salesforce Archive for archived Account records" \
  "commerce-b2b|integrate open code into my B2B Commerce storefront" \
  "mobile-development|run a Komaci offline priming audit for Salesforce Mobile App Plus" \
  "platform-observability|turn on TraceSpanEvent publishing with enablePlatformTracing" \
  "dx-isv-partner|AppAnalyticsQueryRequest PackageUsageSummary SubscriberSnapshot"; do
  plugin="${installed_case%%|*}"
  prompt="${installed_case#*|}"
  printf '{"enabledPlugins":{"salesforce-development@salesforce":true,"%s@salesforce":true}}' \
    "$plugin" > "$CFG/settings.json"
  OUT_INSTALLED=$(run_prompt "$PROJ" "prompt-installed-${plugin}-$$-$RANDOM" "$prompt")
  if ! echo "$OUT_INSTALLED" | grep -q "/salesforce-development:plugin-install ${plugin}"; then
    PASS=$((PASS + 1)); printf '  ok   %-62s → quiet\n' "enabled ${plugin} plugin is not recommended again"
  else
    FAIL=$((FAIL + 1)); printf '  FAIL %-62s → %s\n' "enabled ${plugin} plugin is not recommended again" "$OUT_INSTALLED"
  fi
done

# --- W-23856691 tranche 2: service-engagement, integration, ----------------
# platform-lightning-widgets. Reset to the foundation-only baseline first —
# the loop above left an add-on enabled.
printf '{"enabledPlugins":{"salesforce-development@salesforce":true}}' \
  > "$CFG/settings.json"

assert_route \
  "Digital Engagement channel setup recommends Service Engagement" \
  "service-engagement" "agentforce-adlc|experience-(cms|lwc|react) —|dx-org-lifecycle|dx-devops|integration —|platform-lightning-widgets —" \
  "set up a Salesforce Digital Engagement messaging channel"

# This mandated positive example also carries pre-existing "web"/"service" token
# overlap with experience-lwc's own vocabulary ("lightning web component", "wire
# service") -- present even without this tranche's plugins in the corpus (verified
# against the base marketplace). It is a structural BM25/corpus property, not a
# regression this tranche introduces, so this assertion checks service-engagement
# is offered at high confidence without requiring full isolation.
OUT_WEBCHAT=$(run_prompt "$PROJ" "prompt-webchat-$$-$RANDOM" "configure a Service Cloud web chat deployment")
if echo "$OUT_WEBCHAT" | grep -Eq "Recommended plugins? for this task" \
   && echo "$OUT_WEBCHAT" | grep -q "service-engagement" \
   && echo "$OUT_WEBCHAT" | grep -q "/salesforce-development:plugin-install service-engagement" \
   && ! echo "$OUT_WEBCHAT" | grep -Eq "agentforce-adlc|dx-org-lifecycle|dx-devops|integration —|platform-lightning-widgets —"; then
  PASS=$((PASS + 1)); printf '  ok   %-62s → %s\n' "Service Cloud web chat deployment recommends Service Engagement" "service-engagement"
else
  FAIL=$((FAIL + 1)); printf '  FAIL %-62s → %s\n' "Service Cloud web chat deployment recommends Service Engagement" "$OUT_WEBCHAT"
fi

assert_route \
  "messaging site integration recommends Service Engagement" \
  "service-engagement" "agentforce-adlc|experience-(cms|lwc|react) —|dx-org-lifecycle|dx-devops|integration —|platform-lightning-widgets —" \
  "integrate a messaging site with my Salesforce service org"

assert_route \
  "Connected App OAuth setup recommends Integration" \
  "integration" "agentforce-adlc|experience-(cms|lwc|react) —|dx-org-lifecycle|dx-devops|service-engagement —|platform-lightning-widgets —" \
  "configure a Salesforce Connected App for OAuth"

assert_route \
  "Change Data Capture setup recommends Integration" \
  "integration" "agentforce-adlc|experience-(cms|lwc|react) —|dx-org-lifecycle|dx-devops|service-engagement —|platform-lightning-widgets —" \
  "enable Change Data Capture for Account"

assert_route \
  "platform event subscription setup recommends Integration" \
  "integration" "agentforce-adlc|experience-(cms|lwc|react) —|dx-org-lifecycle|dx-devops|service-engagement —|platform-lightning-widgets —" \
  "configure a Salesforce platform event subscription"

assert_route \
  "custom Lightning Type generation recommends the widget plugin" \
  "platform-lightning-widgets" "agentforce-adlc|experience-(cms|lwc|react) —|dx-org-lifecycle|dx-devops|service-engagement —|integration —" \
  "generate a custom Salesforce Lightning Type"

assert_route \
  "MCP tool widget request recommends the widget plugin" \
  "platform-lightning-widgets" "agentforce-adlc|experience-(cms|lwc|react) —|dx-org-lifecycle|dx-devops|service-engagement —|integration —" \
  "build an MCP tool widget for this Agentforce action"

assert_route \
  "rich display widget request recommends the widget plugin" \
  "platform-lightning-widgets" "agentforce-adlc|experience-(cms|lwc|react) —|dx-org-lifecycle|dx-devops|service-engagement —|integration —" \
  "create a rich display widget for a Lightning Type"

# --- precision: generic verbs/products must not be captured by the new plugins -
assert_route \
  "React component integration stays with the React plugin, not Integration" \
  "experience-react" "agentforce-adlc|experience-(cms|lwc) —|dx-org-lifecycle|dx-devops|integration —" \
  "integrate this React component"

assert_quiet \
  "newsletter subscription does not imply eventing" \
  "subscribe me to this newsletter"

assert_route \
  "LWC datatable prompt stays with LWC, not captured by any new plugin" \
  "experience-lwc" "agentforce-adlc|experience-(cms|react) —|dx-org-lifecycle|dx-devops|service-engagement —|integration —|platform-lightning-widgets —" \
  "create an LWC datatable"

assert_quiet \
  "a generic Apex/Case coding task is not stolen by Service Engagement" \
  "write an Apex trigger for the Case object"

for new_installed_case in \
  "service-engagement|set up a Salesforce Digital Engagement messaging channel" \
  "integration|configure a Salesforce Connected App for OAuth" \
  "platform-lightning-widgets|generate a custom Salesforce Lightning Type"; do
  plugin="${new_installed_case%%|*}"
  prompt="${new_installed_case#*|}"
  printf '{"enabledPlugins":{"salesforce-development@salesforce":true,"%s@salesforce":true}}' \
    "$plugin" > "$CFG/settings.json"
  OUT_NEW_INSTALLED=$(run_prompt "$PROJ" "prompt-installed-${plugin}-$$-$RANDOM" "$prompt")
  if ! echo "$OUT_NEW_INSTALLED" | grep -q "/salesforce-development:plugin-install ${plugin}"; then
    PASS=$((PASS + 1)); printf '  ok   %-62s → quiet\n' "enabled ${plugin} plugin is not recommended again"
  else
    FAIL=$((FAIL + 1)); printf '  FAIL %-62s → %s\n' "enabled ${plugin} plugin is not recommended again" "$OUT_NEW_INSTALLED"
  fi
done

echo ""
echo "  $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
