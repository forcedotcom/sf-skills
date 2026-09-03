#!/bin/bash
# Decision test for `sf-context plugin-install` (Phase 4 / Phase 4.5).
#
# The code-enforced trust flow for one uninstalled plugin-catalog entry:
# an accepted, same-session Salesforce-marketplace proposal installs in one
# call; an external proposal or bare self-directed call prints the
# plugin's name and source (+ a trust warning when the source is fetched from
# outside this repo) and a one-time nonce bound to that exact name and source;
# only a second external/self-directed call with the SAME nonce via --confirm proceeds to the
# hardened, no-shell `claude plugin install ...` shell-out.
# `--decline` is the explicit, never-inferred decline half of the
# plugin_loaded/plugin_suggestion_declined telemetry correlation. This test
# asserts, fully offline (`claude` itself is stubbed -- no real install runs):
#   - the dry run names the plugin, its source, and the external trust warning,
#     and emits a nonce -- without ever invoking `claude`
#   - a wrong or malformed nonce refuses; an unknown/current/already-installed
#     plugin name refuses; an unreadable/missing settings.json (unknown "enabled"
#     state) still allows the dry run rather than refusing, matching
#     discovery's fail-open read of the same state
#   - the confirmed path shell-outs `claude` twice with the expected argv -- a
#     best-effort `marketplace add` of this repo's own checkout (so a
#     --plugin-dir dev session, which never registered "salesforce" through
#     the marketplace/install-tracking system, gets it registered before the
#     install call needs it), then the install itself -- and never leaks
#     either call's raw stubbed-subprocess text
#   - a confirmed install's failure surfaces only exit/timeout metadata
#   - --decline refuses with no prior proposal; succeeds without a manually
#     copied --session-id after either a direct plugin-match result or a
#     UserPromptSubmit hook recommendation actually surfaced the plugin; and
#     the resulting marker entry downgrades a later same-session bypass-gate
#     hit to warn (not deny)
#   - a confirmed install with a prior proposal consumes (clears) the marker
#     entry, observable as a subsequent --decline on the same plugin+session
#     refusing again with "not proposed" (proxy for the plugin_loaded
#     correlation firing and clearing its entry; the exact telemetry
#     payload is covered by test_sf_context.py, not this bash harness)
#
# Run: bash plugins/builder/salesforce-development/scripts/test/plugin-install.test.sh

set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CTX="$ROOT/sf-context"
MONOREPO_ROOT="$(cd "$ROOT/../../../.." && pwd)"
PASS=0
FAIL=0

NAME="agentforce-adlc"
HIGH_PROMPT="author and test a new Agentforce .agent file for an employee agent"
MEDIUM_PROMPT="curious about agentforce for this"

STUBDIR=$(mktemp -d)
STUB_LOG="$STUBDIR/claude-calls.log"
HERMETIC_CONFIG=$(mktemp -d)
printf '{"enabledPlugins":{"salesforce-development@salesforce":true}}' \
  > "$HERMETIC_CONFIG/settings.json"
export CLAUDE_CONFIG_DIR="$HERMETIC_CONFIG"
trap 'rm -rf "$STUBDIR" "$HERMETIC_CONFIG"' EXIT

write_stub() {
  # write_stub <exit-code>
  cat > "$STUBDIR/claude" <<EOF
#!/bin/bash
printf '%s\n' "\$*" >> "$STUB_LOG"
exit $1
EOF
  chmod +x "$STUBDIR/claude"
}

stubbed_ctx() {
  # stubbed_ctx <args...> — run sf-context with the stub `claude` first on PATH
  : > "$STUB_LOG"
  PATH="$STUBDIR:$PATH" "$CTX" "$@"
}

extract_nonce() {
  # extract_nonce <dry-run-output>
  printf '%s' "$1" | grep -o -- '--confirm [a-f0-9]\{64\}' | awk '{print $2}'
}

fresh_proposal() {
  # fresh_proposal <session_id> — write a real high-confidence proposal via
  # the already-verified plugin-match consumer, so the marker entry this test
  # correlates against is genuine, not hand-crafted.
  "$CTX" plugin-match --session-id "$1" "$HIGH_PROMPT" >/dev/null
}

capture_prompt() {
  # capture_prompt <session_id> <prompt_id> <prompt-text> — mirrors
  # plugin-match.test.sh: the bypass gate scores the CAPTURED prompt text
  # merged with the tool command, not the bare command alone, so a bypass
  # payload only re-matches the plugin when the same prompt_id was captured
  # for this session first (as a real UserPromptSubmit would do).
  printf '{"session_id":"%s","prompt_id":"%s","prompt":"%s"}' "$1" "$2" "$3" \
    | "$CTX" prompt-dispatch >/dev/null
}

echo "sf-context plugin-install — decision (offline, no org, claude stubbed)"

# --- accepted reviewed-marketplace proposal installs in one guarded call ---
TRUSTED_NAME="experience-react"
TRUSTED_SID="plugin-install-trusted-$$-$RANDOM"
"$CTX" plugin-match --session-id "$TRUSTED_SID" \
  "scaffold a new Salesforce React UI bundle app with Tailwind and shadcn" >/dev/null
printf '{"session_id":"%s","prompt_id":"p1","prompt":"install experience-react"}' \
  "$TRUSTED_SID" | "$CTX" prompt-dispatch >/dev/null
write_stub 0
OUT_TRUSTED=$(CLAUDE_CODE_SESSION_ID="$TRUSTED_SID" \
  stubbed_ctx plugin-install "$TRUSTED_NAME" --accept-proposed)
CODE_TRUSTED=$?
TRUSTED_CALL1=$(sed -n '1p' "$STUB_LOG")
TRUSTED_CALL2=$(sed -n '2p' "$STUB_LOG")
if [ "$CODE_TRUSTED" -eq 0 ] \
   && echo "$OUT_TRUSTED" | grep -q "Installed $TRUSTED_NAME on disk" \
   && echo "$OUT_TRUSTED" | grep -q "Run /reload-plugins now" \
   && ! echo "$OUT_TRUSTED" | grep -q "Plugin: $TRUSTED_NAME" \
   && ! echo "$OUT_TRUSTED" | grep -q -- "--confirm" \
   && [ "$TRUSTED_CALL1" = "plugin marketplace add $MONOREPO_ROOT" ] \
   && [ "$TRUSTED_CALL2" = "plugin install $TRUSTED_NAME@salesforce --yes" ]; then
  PASS=$((PASS + 1)); printf '  ok   %-60s → one acceptance, direct install + reload handoff\n' \
    "trusted proposed install"
else
  FAIL=$((FAIL + 1)); printf '  FAIL %-60s → exit=%s call1=%s call2=%s out=%s\n' \
    "trusted proposed install" "$CODE_TRUSTED" "$TRUSTED_CALL1" "$TRUSTED_CALL2" "$OUT_TRUSTED"
fi

# The fast path is unavailable without both the proposal ledger entry and the
# selected live workflow, even for a local marketplace source.
OUT_UNSELECTED=$(CLAUDE_CODE_SESSION_ID="plugin-install-unselected-$$-$RANDOM" \
  "$CTX" plugin-install "$TRUSTED_NAME" --accept-proposed 2>&1)
CODE_UNSELECTED=$?
if [ "$CODE_UNSELECTED" -eq 2 ] \
   && echo "$OUT_UNSELECTED" | grep -q "proposed and selected in the same session"; then
  PASS=$((PASS + 1)); printf '  ok   %-60s → fail-closed without selected proposal\n' \
    "trusted fast path requires same-session selection"
else
  FAIL=$((FAIL + 1)); printf '  FAIL %-60s → exit=%s out=%s\n' \
    "trusted fast path requires same-session selection" "$CODE_UNSELECTED" "$OUT_UNSELECTED"
fi

# An accepted external proposal never inherits the marketplace fast path; it
# renders its source warning and nonce without invoking claude.
EXTERNAL_SID="plugin-install-external-accept-$$-$RANDOM"
fresh_proposal "$EXTERNAL_SID"
printf '{"session_id":"%s","prompt_id":"p1","prompt":"install agentforce-adlc"}' \
  "$EXTERNAL_SID" | "$CTX" prompt-dispatch >/dev/null
write_stub 0
OUT_EXTERNAL_ACCEPT=$(CLAUDE_CODE_SESSION_ID="$EXTERNAL_SID" \
  stubbed_ctx plugin-install "$NAME" --accept-proposed)
CODE_EXTERNAL_ACCEPT=$?
EXTERNAL_NONCE=$(extract_nonce "$OUT_EXTERNAL_ACCEPT")
if [ "$CODE_EXTERNAL_ACCEPT" -eq 0 ] \
   && echo "$OUT_EXTERNAL_ACCEPT" | grep -qi "TRUST WARNING" \
   && [ -n "$EXTERNAL_NONCE" ] \
   && [ ! -s "$STUB_LOG" ]; then
  PASS=$((PASS + 1)); printf '  ok   %-60s → source warning + nonce, no install\n' \
    "external proposed install retains confirmation"
else
  FAIL=$((FAIL + 1)); printf '  FAIL %-60s → exit=%s nonce=%s log=%s out=%s\n' \
    "external proposed install retains confirmation" "$CODE_EXTERNAL_ACCEPT" \
    "$EXTERNAL_NONCE" "$(cat "$STUB_LOG")" "$OUT_EXTERNAL_ACCEPT"
fi

# --- dry run: names the plugin, pin, trust warning; never invokes claude ---
write_stub 0
OUT_DRY=$(stubbed_ctx plugin-install "$NAME")
CODE_DRY=$?
NONCE=$(extract_nonce "$OUT_DRY")
if [ "$CODE_DRY" -eq 0 ] \
   && echo "$OUT_DRY" | grep -q "Plugin: $NAME" \
   && echo "$OUT_DRY" | grep -q "Installs from: $NAME@claude-plugins-official" \
   && echo "$OUT_DRY" | grep -qi "TRUST WARNING" \
   && echo "$OUT_DRY" | grep -q "must run /reload-plugins" \
   && [ -n "$NONCE" ] \
   && [ ! -s "$STUB_LOG" ]; then
  PASS=$((PASS + 1)); printf '  ok   %-60s → names plugin + install target + trust warning + nonce, no claude call\n' "dry run"
else
  FAIL=$((FAIL + 1)); printf '  FAIL %-60s → exit=%s nonce=%s log=%s out=%s\n' "dry run" "$CODE_DRY" "$NONCE" "$(cat "$STUB_LOG")" "$OUT_DRY"
fi

# --- a wrong nonce refuses without ever invoking claude --------------------
write_stub 0
WRONG="0000000000000000000000000000000000000000000000000000000000000000"
OUT_WRONG=$(stubbed_ctx plugin-install "$NAME" --confirm "$WRONG" 2>&1)
CODE_WRONG=$?
if [ "$CODE_WRONG" -eq 3 ] && [ ! -s "$STUB_LOG" ]; then
  PASS=$((PASS + 1)); printf '  ok   %-60s → refused, no claude call\n' "wrong nonce refuses"
else
  FAIL=$((FAIL + 1)); printf '  FAIL %-60s → exit=%s log=%s\n' "wrong nonce refuses" "$CODE_WRONG" "$(cat "$STUB_LOG")"
fi

# --- a malformed (wrong-shape) nonce refuses at parse time ------------------
OUT_MALFORMED=$("$CTX" plugin-install "$NAME" --confirm not-a-real-nonce 2>&1)
CODE_MALFORMED=$?
if [ "$CODE_MALFORMED" -eq 2 ]; then
  PASS=$((PASS + 1)); printf '  ok   %-60s → %s\n' "malformed nonce shape refuses" "exit=$CODE_MALFORMED"
else
  FAIL=$((FAIL + 1)); printf '  FAIL %-60s → exit=%s\n' "malformed nonce shape refuses" "$CODE_MALFORMED"
fi

# --- --confirm and --decline are mutually exclusive -------------------------
RIGHT_NONCE=$(extract_nonce "$("$CTX" plugin-install "$NAME")")
OUT_BOTH=$("$CTX" plugin-install "$NAME" --confirm "$RIGHT_NONCE" --decline 2>&1)
CODE_BOTH=$?
if [ "$CODE_BOTH" -eq 2 ]; then
  PASS=$((PASS + 1)); printf '  ok   %-60s → %s\n' "--confirm and --decline together refuse" "exit=$CODE_BOTH"
else
  FAIL=$((FAIL + 1)); printf '  FAIL %-60s → exit=%s\n' "--confirm and --decline together refuse" "$CODE_BOTH"
fi

# --- an unknown name refuses -------------------------------------------------
OUT_UNKNOWN=$("$CTX" plugin-install "totally-unknown-plugin-$$-$RANDOM" 2>&1)
CODE_UNKNOWN=$?
if [ "$CODE_UNKNOWN" -eq 2 ] \
   && echo "$OUT_UNKNOWN" | grep -q "not found in the plugin catalog" \
   && echo "$OUT_UNKNOWN" | grep -q "requires.plugins"; then
  PASS=$((PASS + 1)); printf '  ok   %-60s → reason is actionable\n' "unknown name refuses"
else
  FAIL=$((FAIL + 1)); printf '  FAIL %-60s → exit=%s out=%s\n' \
    "unknown name refuses" "$CODE_UNKNOWN" "$OUT_UNKNOWN"
fi

# --- the plugin currently running this code (self) refuses -----------------
OUT_SELF=$("$CTX" plugin-install salesforce-development 2>&1)
CODE_SELF=$?
if [ "$CODE_SELF" -eq 2 ] \
   && echo "$OUT_SELF" | grep -q "cannot install itself"; then
  PASS=$((PASS + 1)); printf '  ok   %-60s → reason identifies self\n' "current plugin refuses"
else
  FAIL=$((FAIL + 1)); printf '  FAIL %-60s → exit=%s out=%s\n' \
    "current plugin refuses" "$CODE_SELF" "$OUT_SELF"
fi

# --- an already-installed name refuses --------------------------------------
CONFIG_DIR=$(mktemp -d)
cat > "$CONFIG_DIR/settings.json" <<EOF
{"enabledPlugins": {"$NAME@salesforce": true}}
EOF
OUT_INSTALLED=$(CLAUDE_CONFIG_DIR="$CONFIG_DIR" "$CTX" plugin-install "$NAME" 2>&1)
CODE_INSTALLED=$?
rm -rf "$CONFIG_DIR"
if [ "$CODE_INSTALLED" -eq 2 ] \
   && echo "$OUT_INSTALLED" | grep -q "already installed" \
   && echo "$OUT_INSTALLED" | grep -q "no installation is needed"; then
  PASS=$((PASS + 1)); printf '  ok   %-60s → reason identifies installed state\n' \
    "already-installed name refuses"
else
  FAIL=$((FAIL + 1)); printf '  FAIL %-60s → exit=%s out=%s\n' \
    "already-installed name refuses" "$CODE_INSTALLED" "$OUT_INSTALLED"
fi

# --- unreadable/missing settings.json still allows the dry run (fail-open,
# matching discovery's overview/plugin-match reads of the same "enabled"
# state) -- regression for a bug where this refused instead ------------------
EMPTY_CONFIG_DIR=$(mktemp -d)
OUT_NOSETTINGS=$(CLAUDE_CONFIG_DIR="$EMPTY_CONFIG_DIR" "$CTX" plugin-install "$NAME" 2>&1)
CODE_NOSETTINGS=$?
rm -rf "$EMPTY_CONFIG_DIR"
if [ "$CODE_NOSETTINGS" -eq 0 ] && echo "$OUT_NOSETTINGS" | grep -q "Plugin: $NAME"; then
  PASS=$((PASS + 1)); printf '  ok   %-60s → %s\n' "missing settings.json still allows dry run (fail-open)" "exit=$CODE_NOSETTINGS"
else
  FAIL=$((FAIL + 1)); printf '  FAIL %-60s → exit=%s out=%s\n' "missing settings.json still allows dry run (fail-open)" "$CODE_NOSETTINGS" "$OUT_NOSETTINGS"
fi

# --- confirmed install of an EXTERNAL-source plugin: claude is shelled out
# exactly ONCE, routed to the pre-registered official marketplace
# (`@claude-plugins-official`) with NO `salesforce` marketplace registration --
# agentforce-adlc lives in the official marketplace, not this repo's. The
# local-source register-then-install two-call flow (`marketplace add` this
# repo's checkout, then `<name>@salesforce`) is covered by the "trusted
# proposed install" (experience-react) case above. --------------------------
write_stub 0
NONCE_OK=$(extract_nonce "$("$CTX" plugin-install "$NAME")")
OUT_OK=$(stubbed_ctx plugin-install "$NAME" --confirm "$NONCE_OK")
CODE_OK=$?
CALL1=$(sed -n '1p' "$STUB_LOG")
CALL2=$(sed -n '2p' "$STUB_LOG")
if [ "$CODE_OK" -eq 0 ] \
   && echo "$OUT_OK" | grep -q "Installed $NAME on disk" \
   && echo "$OUT_OK" | grep -q "not active in this session yet" \
   && echo "$OUT_OK" | grep -q "Run /reload-plugins now" \
   && echo "$OUT_OK" | grep -q "refreshed inventory shows $NAME is active" \
   && echo "$OUT_OK" | grep -q "start a fresh session" \
   && echo "$OUT_OK" | grep -q "submit a concrete task to begin using it" \
   && ! echo "$OUT_OK" | grep -q "resume your original task" \
   && [ "$CALL1" = "plugin install $NAME@claude-plugins-official --yes" ] \
   && [ -z "$CALL2" ]; then
  PASS=$((PASS + 1)); printf '  ok   %-60s → official-marketplace single-call argv, success message\n' "confirmed external install shells out claude once"
else
  FAIL=$((FAIL + 1)); printf '  FAIL %-60s → exit=%s call1=%s call2=%s out=%s\n' "confirmed external install shells out claude once" "$CODE_OK" "$CALL1" "$CALL2" "$OUT_OK"
fi

# --- a failed claude call surfaces only exit-code metadata, never raw text -
write_stub 1
NONCE_FAIL=$(extract_nonce "$("$CTX" plugin-install "$NAME")")
OUT_FAIL=$(stubbed_ctx plugin-install "$NAME" --confirm "$NONCE_FAIL" 2>&1)
CODE_FAIL=$?
if [ "$CODE_FAIL" -eq 3 ] && echo "$OUT_FAIL" | grep -q "exit=1"; then
  PASS=$((PASS + 1)); printf '  ok   %-60s → %s\n' "failed claude call surfaces exit code only" "$OUT_FAIL"
else
  FAIL=$((FAIL + 1)); printf '  FAIL %-60s → exit=%s out=%s\n' "failed claude call surfaces exit code only" "$CODE_FAIL" "$OUT_FAIL"
fi

# --- --decline with no prior proposal in this session refuses --------------
SID_NOPROPOSAL="plugin-install-nodecline-$$-$RANDOM"
OUT_NODECLINE=$(CLAUDE_CODE_SESSION_ID="$SID_NOPROPOSAL" \
  "$CTX" plugin-install "$NAME" --decline 2>&1)
CODE_NODECLINE=$?
if [ "$CODE_NODECLINE" -eq 2 ]; then
  PASS=$((PASS + 1)); printf '  ok   %-60s → %s\n' "session-env decline with unseen plugin refuses" "exit=$CODE_NODECLINE"
else
  FAIL=$((FAIL + 1)); printf '  FAIL %-60s → exit=%s\n' "session-env decline with unseen plugin refuses" "$CODE_NODECLINE"
fi

# --- a direct matcher result is a real user-visible proposal ---------------
# Claude Code injects this variable into Bash/PowerShell subprocesses. The model
# should not need to know or copy the opaque id into either command.
SID_DIRECT="plugin-install-direct-match-$$-$RANDOM"
CLAUDE_CODE_SESSION_ID="$SID_DIRECT" \
  "$CTX" plugin-match "$HIGH_PROMPT" >/dev/null
OUT_DIRECT_DECLINE=$(CLAUDE_CODE_SESSION_ID="$SID_DIRECT" \
  "$CTX" plugin-install "$NAME" --decline 2>&1)
CODE_DIRECT_DECLINE=$?
if [ "$CODE_DIRECT_DECLINE" -eq 0 ] && echo "$OUT_DIRECT_DECLINE" | grep -qi "declined"; then
  PASS=$((PASS + 1)); printf '  ok   %-60s → %s\n' "direct matcher proposal can be declined via session env" "$OUT_DIRECT_DECLINE"
else
  FAIL=$((FAIL + 1)); printf '  FAIL %-60s → exit=%s out=%s\n' "direct matcher proposal can be declined via session env" "$CODE_DIRECT_DECLINE" "$OUT_DIRECT_DECLINE"
fi

# --- a UserPromptSubmit recommendation is also a user-visible proposal -----
SID_HOOK="plugin-install-user-prompt-$$-$RANDOM"
HOOK_OUT=$(printf '{"session_id":"%s","prompt_id":"p-hook","prompt":"%s"}' \
  "$SID_HOOK" "$HIGH_PROMPT" | "$CTX" prompt-dispatch)
OUT_HOOK_DECLINE=$(CLAUDE_CODE_SESSION_ID="$SID_HOOK" \
  "$CTX" plugin-install "$NAME" --decline 2>&1)
CODE_HOOK_DECLINE=$?
if echo "$HOOK_OUT" | grep -q "/salesforce-development:plugin-install $NAME" \
   && [ "$CODE_HOOK_DECLINE" -eq 0 ] \
   && echo "$OUT_HOOK_DECLINE" | grep -qi "declined"; then
  PASS=$((PASS + 1)); printf '  ok   %-60s → %s\n' "UserPromptSubmit proposal can be declined via session env" "$OUT_HOOK_DECLINE"
else
  FAIL=$((FAIL + 1)); printf '  FAIL %-60s → hook=%s exit=%s out=%s\n' "UserPromptSubmit proposal can be declined via session env" "$HOOK_OUT" "$CODE_HOOK_DECLINE" "$OUT_HOOK_DECLINE"
fi

# --- --decline after a real proposal succeeds, and downgrades a later ------
# same-session bypass-gate hit to warn (not deny) -- the observable proxy for
# "the marker entry survives the decline."
SID_DECLINE="plugin-install-decline-$$-$RANDOM"
fresh_proposal "$SID_DECLINE"
OUT_DECLINE=$("$CTX" plugin-install "$NAME" --decline --session-id "$SID_DECLINE" 2>&1)
CODE_DECLINE=$?
if [ "$CODE_DECLINE" -eq 0 ] && echo "$OUT_DECLINE" | grep -qi "declined"; then
  PASS=$((PASS + 1)); printf '  ok   %-60s → %s\n' "--decline after a real proposal succeeds" "$OUT_DECLINE"
else
  FAIL=$((FAIL + 1)); printf '  FAIL %-60s → exit=%s out=%s\n' "--decline after a real proposal succeeds" "$CODE_DECLINE" "$OUT_DECLINE"
fi

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

BYPASS_CMD="sf project deploy start --source-dir force-app"
capture_prompt "$SID_DECLINE" "p1" "$MEDIUM_PROMPT"
BYPASS_PAYLOAD="{\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"$BYPASS_CMD\"},\"session_id\":\"$SID_DECLINE\",\"prompt_id\":\"p1\"}"
GOT_AFTER_DECLINE=$(printf '%s' "$BYPASS_PAYLOAD" | "$CTX" skills-first-advisory | parse_decision)
if [ "$GOT_AFTER_DECLINE" = "warn" ]; then
  PASS=$((PASS + 1)); printf '  ok   %-60s → %s\n' "a later bypass-gate hit after decline warns (not denies)" "$GOT_AFTER_DECLINE"
else
  FAIL=$((FAIL + 1)); printf '  FAIL %-60s → got "%s", expected "warn"\n' "a later bypass-gate hit after decline warns (not denies)" "$GOT_AFTER_DECLINE"
fi

# --- --decline again for the same plugin+session still succeeds (the entry
# persists; decline is idempotent against an already-declined proposal) ----
OUT_REDECLINE=$("$CTX" plugin-install "$NAME" --decline --session-id "$SID_DECLINE" 2>&1)
CODE_REDECLINE=$?
if [ "$CODE_REDECLINE" -eq 0 ]; then
  PASS=$((PASS + 1)); printf '  ok   %-60s → %s\n' "declining an already-declined proposal stays idempotent" "exit=$CODE_REDECLINE"
else
  FAIL=$((FAIL + 1)); printf '  FAIL %-60s → exit=%s\n' "declining an already-declined proposal stays idempotent" "$CODE_REDECLINE"
fi

# --- a confirmed install consumes (clears) a prior proposal's marker entry --
# Observable proxy: --decline on the SAME plugin+session AFTER a confirmed
# install now refuses again with "not proposed", because plugin_loaded's
# correlation cleared the entry on success (Phase 4.5's accept half). The
# exact capture_event(plugin_loaded, ...) call is unit-tested in Python
# (test_sf_context.py), since capture_event's own consent/project/notice
# gating makes its buffered-output shape awkward to assert from bash.
write_stub 0
SID_CONSUME="plugin-install-consume-$$-$RANDOM"
fresh_proposal "$SID_CONSUME"
NONCE_CONSUME=$(extract_nonce "$("$CTX" plugin-install "$NAME" --session-id "$SID_CONSUME")")
stubbed_ctx plugin-install "$NAME" --confirm "$NONCE_CONSUME" --session-id "$SID_CONSUME" >/dev/null
OUT_POSTINSTALL_DECLINE=$("$CTX" plugin-install "$NAME" --decline --session-id "$SID_CONSUME" 2>&1)
CODE_POSTINSTALL_DECLINE=$?
if [ "$CODE_POSTINSTALL_DECLINE" -eq 2 ] && echo "$OUT_POSTINSTALL_DECLINE" | grep -qi "not proposed"; then
  PASS=$((PASS + 1)); printf '  ok   %-60s → marker entry was cleared on install success\n' "confirmed install consumes the proposal marker"
else
  FAIL=$((FAIL + 1)); printf '  FAIL %-60s → exit=%s out=%s\n' "confirmed install consumes the proposal marker" "$CODE_POSTINSTALL_DECLINE" "$OUT_POSTINSTALL_DECLINE"
fi

echo ""
echo "  $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
