#!/bin/bash
# Decision test for the salesforce-test-drive re-entry surfaces (end-to-end, via
# the real sf-context CLI, fully offline).
#
# Two related behaviors for a user who has salesforce-test-drive INSTALLED:
#   - COLD "no rec": recommendations are uninstalled-only, so a fresh
#     test-drive/walkthrough ask when the plugin is ALREADY installed surfaces
#     nothing for it -- there is nothing to install, and the user just runs its
#     command. (With no live marker there is no resume pointer either.)
#   - WARM "resume" (C): an interrupted drive left a project-scoped marker; terse
#     continuation language ("continue", "pick it back up") points the user back
#     at `/salesforce-test-drive:start <driveId>`. The anti-nag guarantee: a user
#     in build mode is never pulled back in -- a substantive build task stays
#     silent even with a live marker, and the kill switch suppresses everything.
#
# The marker data layer, TTL, and the fullmatch regex are unit-tested in
# test_sf_context.py; this asserts the real CLI wiring the unit tests mock away
# (settings.json install state, the test-drive-mark companion command writing a
# marker that prompt-dispatch then reads through real project-root resolution).
#
# Run: bash plugins/builder/salesforce-development/scripts/test/test-drive-resume.test.sh

set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CTX="$ROOT/sf-context"
PASS=0
FAIL=0

# Self-contained + hermetic: a stray ambient session id must not leak into the
# proposal marker (see plugin-discovery-shell-test-env-trap), and the installed
# set is pinned rather than read from the developer's real ~/.claude.
unset CLAUDE_CODE_SESSION_ID
CFG="$(mktemp -d)"
PROJ="$(mktemp -d)"
cleanup() {
  # Best-effort clear of the project-scoped marker (shared system runtime dir).
  ( cd "$PROJ" && "$CTX" test-drive-mark done >/dev/null 2>&1 )
  rm -rf "$CFG" "$PROJ"
}
trap cleanup EXIT
export CLAUDE_CONFIG_DIR="$CFG"
printf '{"packageDirectories":[{"path":"force-app","default":true}]}' \
  > "$PROJ/sfdx-project.json"

installed_both() {
  printf '{"enabledPlugins":{"salesforce-development@salesforce":true,"salesforce-test-drive@salesforce":true}}' \
    > "$CFG/settings.json"
}
installed_foundation_only() {
  printf '{"enabledPlugins":{"salesforce-development@salesforce":true}}' \
    > "$CFG/settings.json"
}

disp() {
  # disp <session-id> <prompt-text>  (dispatched from inside the project)
  ( cd "$PROJ" && printf '{"session_id":"%s","prompt_id":"p1","prompt":"%s"}' "$1" "$2" \
      | "$CTX" prompt-dispatch )
}
mark() { ( cd "$PROJ" && "$CTX" test-drive-mark "$@" ); }

sys_message() {
  # Extract systemMessage (the visible surface) from a prompt-dispatch payload.
  python3 -c 'import json,sys
try:
    print(json.load(sys.stdin).get("systemMessage") or "")
except Exception:
    print("")'
}

echo "sf-context test-drive re-entry — decision (offline, no org)"

# --- COLD installed → no test-drive surface (recs are uninstalled-only) -----
# A fresh test-drive/walkthrough ask when the plugin is ALREADY installed has
# nothing to recommend: no "you already have it" pointer, no install pitch, and
# (with no live marker yet) no resume pointer. The prompt just proceeds.
installed_both

for cold_prompt in \
  "take Service Cloud for a test drive" \
  "give me a guided walkthrough of building a Service help agent"; do
  OUT=$(disp "cold-${PASS}-${FAIL}-$$-$RANDOM" "$cold_prompt" | sys_message)
  if ! echo "$OUT" | grep -q "You already have this plugin installed" \
     && ! echo "$OUT" | grep -q "test drive in progress" \
     && ! echo "$OUT" | grep -q "run /salesforce-test-drive:start" \
     && ! echo "$OUT" | grep -q "/salesforce-development:plugin-install salesforce-test-drive"; then
    PASS=$((PASS + 1)); printf '  ok   %-58s → no test-drive pointer\n' "cold: ${cold_prompt:0:44}"
  else
    FAIL=$((FAIL + 1)); printf '  FAIL %-58s → %s\n' "cold: ${cold_prompt:0:44}" "$OUT"
  fi
done

# --- WARM "resume" (C): live marker + terse continuation --------------------
mark start service-help-agent >/dev/null

for resume_prompt in "continue" "pick it back up"; do
  OUT=$(disp "warm-${PASS}-${FAIL}-$$-$RANDOM" "$resume_prompt" | sys_message)
  if echo "$OUT" | grep -q "test drive in progress" \
     && echo "$OUT" | grep -q "run /salesforce-test-drive:start service-help-agent"; then
    PASS=$((PASS + 1)); printf '  ok   %-58s → resume pointer\n' "warm: \"$resume_prompt\""
  else
    FAIL=$((FAIL + 1)); printf '  FAIL %-58s → %s\n' "warm: \"$resume_prompt\"" "$OUT"
  fi
done

# --- anti-nag: a substantive build task never resumes, even with a live marker
OUT=$(disp "warm-build-$$-$RANDOM" "build me a record-triggered flow for approvals" | sys_message)
if ! echo "$OUT" | grep -q "test drive in progress"; then
  PASS=$((PASS + 1)); printf '  ok   %-58s → stays in build mode\n' "anti-nag: build task with live marker"
else
  FAIL=$((FAIL + 1)); printf '  FAIL %-58s → %s\n' "anti-nag: build task with live marker" "$OUT"
fi

# --- kill switch: SF_DISABLE_PLUGIN_MATCH suppresses the warm surface --------
# (marker is still live here -- it is only cleared in the next case).
OUT=$( cd "$PROJ" && printf '{"session_id":"kill-%s","prompt_id":"p1","prompt":"continue"}' "$$" \
        | SF_DISABLE_PLUGIN_MATCH=1 "$CTX" prompt-dispatch | sys_message )
if ! echo "$OUT" | grep -q "test drive in progress"; then
  PASS=$((PASS + 1)); printf '  ok   %-58s → suppressed\n' "kill switch off suppresses resume"
else
  FAIL=$((FAIL + 1)); printf '  FAIL %-58s → %s\n' "kill switch off suppresses resume" "$OUT"
fi

# --- cleared: `test-drive-mark done` ends resume detection ------------------
mark done >/dev/null
OUT=$(disp "cleared-$$-$RANDOM" "continue" | sys_message)
if ! echo "$OUT" | grep -q "test drive in progress"; then
  PASS=$((PASS + 1)); printf '  ok   %-58s → no stale resume\n' "cleared marker stops resuming"
else
  FAIL=$((FAIL + 1)); printf '  FAIL %-58s → %s\n' "cleared marker stops resuming" "$OUT"
fi

# --- self-heal: an uninstalled drive plugin can never resume ----------------
# Re-arm, then drop the plugin from the enabled set. The resume target refuses
# (and clears the now-orphaned marker) because the plugin it points at is gone.
mark start service-help-agent >/dev/null
installed_foundation_only
OUT=$(disp "uninstalled-$$-$RANDOM" "continue" | sys_message)
if ! echo "$OUT" | grep -q "test drive in progress"; then
  PASS=$((PASS + 1)); printf '  ok   %-58s → no resume without the plugin\n' "uninstalled drive plugin cannot resume"
else
  FAIL=$((FAIL + 1)); printf '  FAIL %-58s → %s\n' "uninstalled drive plugin cannot resume" "$OUT"
fi
installed_both  # restore for any future cases

echo ""
echo "  $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
