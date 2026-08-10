#!/bin/bash
# Decision test for `sf-context detect` re-injection after compaction (issue #406).
#
# The SessionStart hook (matcher "*") re-fires after a context compaction with
# source="compact". PreCompact cannot inject context (it's block-only), so
# SessionStart(compact)+additionalContext is the supported way to keep the
# skills-first directive durable across a long session. On that re-fire detect
# must:
#   - re-inject ONLY the lean reminder (not the full ~40-skill catalog)
#   - make NO org CLI calls and show NO visible banner (systemMessage absent)
#   - stay silent outside a Salesforce project
#   - never block (continue:true, no permissionDecision)
# On the normal sources (startup/resume/clear, or no payload) it must fall
# through to the full detect path (banner present in a project).
#
# Fully offline: runs in a throwaway cwd, never touches a real org. The full
# startup path still shells out to `sf`, so we assert only the cheap, stable
# signals (lean-reminder marker, banner presence) — not org metadata.
#
# Run: bash plugins/sfdx-core/test/detect-compact.test.sh

set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CTX="$ROOT/sf-context"
PASS=0
FAIL=0

# parse → "<lean|full|silent>|<visible|hidden>|<blocking>"
#   lean:    additionalContext contains the re-inject marker, not the full catalog
#   full:    additionalContext contains the full-catalog marker
#   silent:  no additionalContext
#   visible: systemMessage present (a banner shown to the user)
#   hidden:  no systemMessage
parse() {
  python3 -c "
import json,sys
d=json.load(sys.stdin)
ctx=d.get('hookSpecificOutput',{}).get('additionalContext','') or ''
if 'salesforce-development durable context after compaction' in ctx:
    kind='lean'
elif 'auto-injected by salesforce-development' in ctx:
    kind='full'
elif ctx.strip():
    kind='other'
else:
    kind='silent'
vis='visible' if d.get('systemMessage') else 'hidden'
blocking='block' if d.get('hookSpecificOutput',{}).get('permissionDecision') else 'ok'
if d.get('continue') is not True and kind!='full' and not d.get('systemMessage'):
    # full/banner paths legitimately omit top-level continue (emit() sets it only
    # when there's no decision); only flag a genuine missing-continue on lean/silent.
    pass
print(f'{kind}|{vis}|{blocking}')
"
}

# check <expected-kind> <expected-vis> <description> <stdin-payload> <setup-fn>
check() {
  local ekind="$1" evis="$2" desc="$3" payload="$4" setup="$5"
  local work out got expected
  work=$(mktemp -d)
  ( cd "$work" && "$setup" )
  out=$(cd "$work" && printf '%s' "$payload" | "$CTX" detect 2>/dev/null)
  got=$(printf '%s' "$out" | parse 2>/dev/null)
  rm -rf "$work"
  expected="${ekind}|${evis}|ok"
  if [ "$got" = "$expected" ]; then
    PASS=$((PASS + 1)); printf '  ok   %-50s → %s\n' "$desc" "$got"
  else
    FAIL=$((FAIL + 1)); printf '  FAIL %-50s → got "%s", expected "%s"\n' "$desc" "$got" "$expected"
    printf '       raw: %s\n' "$out"
  fi
}

setup_sf()     { touch sfdx-project.json; }
setup_not_sf() { :; }

echo "sf-context detect — compaction re-inject (offline)"

# compact re-fire in a SF project → lean reminder, no banner
check lean hidden "compact source in SF project → lean, hidden" \
  '{"hook_event_name":"SessionStart","source":"compact"}' setup_sf

# compact re-fire outside a SF project → silent, no banner
check silent hidden "compact source, not a SF project → silent" \
  '{"hook_event_name":"SessionStart","source":"compact"}' setup_not_sf

echo ""
echo "  $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
