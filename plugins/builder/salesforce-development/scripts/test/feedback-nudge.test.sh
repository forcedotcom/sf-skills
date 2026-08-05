#!/bin/bash
# Decision test for `sf-context feedback-nudge` + `record-feedback-decision` (#277).
#
# The feedback loop is the suite's first step toward an off-machine data path, so
# its gate must be provably default-OFF and its trigger provably self-limiting.
# This test asserts, fully offline (no org, no model):
#   - gate OFF (SFDX_FEEDBACK unset) → always silent, regardless of transcript
#   - gate ON + substantive work in the transcript → exactly one nudge
#   - gate ON + same session again → silent (one nudge per session)
#   - gate ON + no substantive work → silent
#   - every response is non-blocking (continue:true, no permissionDecision)
#   - record-feedback-decision persists the opt-in choice
#
# Run: bash plugins/sfdx-core/test/feedback-nudge.test.sh

set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CTX="$ROOT/sf-context"
PASS=0
FAIL=0

# Isolate state: run everything in a throwaway cwd so the `.sf/` the command
# writes never touches the repo, and each case starts from a clean slate.
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

SUBSTANTIVE="$WORK/substantive.jsonl"
printf '%s\n' '{"role":"assistant","content":"I will run sf project deploy start --source-dir force-app now"}' > "$SUBSTANTIVE"
TRIVIAL="$WORK/trivial.jsonl"
printf '%s\n' '{"role":"assistant","content":"just listed files with ls -la, nothing else"}' > "$TRIVIAL"

# parse → "<warn|quiet>|<blocking>"
#   warn:     "warn" if additionalContext present, else "quiet"
#   blocking: "ok" normally; "block" if a permissionDecision sneaks in;
#             "no-continue" if continue isn't literally true (a hard violation)
parse() {
  python3 -c "
import json,sys
d=json.load(sys.stdin)
warn='warn' if d.get('hookSpecificOutput',{}).get('additionalContext') else 'quiet'
blocking='block' if d.get('hookSpecificOutput',{}).get('permissionDecision') else 'ok'
if d.get('continue') is not True: blocking='no-continue'
print(f'{warn}|{blocking}')
"
}

# nudge <expected-warn> <description> <env-on:0|1> <session-id> <transcript>
nudge() {
  local ewarn="$1" desc="$2" envon="$3" sid="$4" tpath="$5"
  local out got expected payload
  payload=$(printf '{"session_id":"%s","transcript_path":"%s"}' "$sid" "$tpath")
  if [ "$envon" = "1" ]; then
    out=$(cd "$WORK" && printf '%s' "$payload" | SFDX_FEEDBACK=1 "$CTX" feedback-nudge)
  else
    out=$(cd "$WORK" && printf '%s' "$payload" | env -u SFDX_FEEDBACK "$CTX" feedback-nudge)
  fi
  got=$(printf '%s' "$out" | parse)
  expected="${ewarn}|ok"
  if [ "$got" = "$expected" ]; then
    PASS=$((PASS + 1)); printf '  ok   %-46s → %s\n' "$desc" "$got"
  else
    FAIL=$((FAIL + 1)); printf '  FAIL %-46s → got "%s", expected "%s"\n' "$desc" "$got" "$expected"
    printf '       raw: %s\n' "$out"
  fi
}

echo "sf-context feedback-nudge — gate + trigger (offline, no org)"

# Gate OFF: silent even with substantive work present.
nudge quiet "gate off + substantive → silent" 0 sX "$SUBSTANTIVE"
nudge quiet "gate off + trivial → silent"     0 sY "$TRIVIAL"

# Gate ON: first substantive turn nudges; repeat in same session stays silent.
nudge warn  "gate on + substantive → nudge"        1 s1 "$SUBSTANTIVE"
nudge quiet "gate on + same session again → silent" 1 s1 "$SUBSTANTIVE"

# Gate ON but nothing substantive ran → silent (fresh session id, clean state).
rm -f "$WORK/.sf/feedback-config.json"
nudge quiet "gate on + trivial work → silent" 1 s2 "$TRIVIAL"

echo ""
echo "record-feedback-decision — opt-in persistence"
rm -f "$WORK/.sf/feedback-config.json"
on=$(cd "$WORK" && "$CTX" record-feedback-decision on)
got_on=$(printf '%s' "$on" | python3 -c "import json,sys;print(json.load(sys.stdin).get('opt_in'))")
if [ "$got_on" = "True" ]; then PASS=$((PASS+1)); printf '  ok   %-46s → %s\n' "record on → opt_in true" "$got_on"
else FAIL=$((FAIL+1)); printf '  FAIL %-46s → %s\n' "record on" "$on"; fi

bad=$(cd "$WORK" && "$CTX" record-feedback-decision bogus; echo "rc=$?")
if printf '%s' "$bad" | grep -q 'rc=1'; then PASS=$((PASS+1)); printf '  ok   %-46s → rejected\n' "record bogus → error rc=1"
else FAIL=$((FAIL+1)); printf '  FAIL %-46s → %s\n' "record bogus should error" "$bad"; fi

echo ""
echo "  $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
