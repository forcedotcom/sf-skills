#!/bin/bash
# Decision test for `sf-context post-deploy-failure` (issue #405).
#
# Claude Code routes a FAILED tool call to the distinct `PostToolUseFailure`
# event (verified empirically on the installed version). On a failed
# `sf project deploy*`, this advisory routes to the owning skill. Critically,
# the failure payload carries only `tool_input.command` + a terse `error` —
# NOT the deploy's stdout/stderr — so the advisory branches on the deploy
# SUB-COMMAND and hands the model a decision tree to match against the error it
# already has. It is advisory-only (never blocks) and fail-open (silent allow on
# a non-deploy command or garbled payload).
#
# This test asserts, fully offline (no org):
#   - deploy start / validate / quick each name their owning skill
#   - a non-deploy command stays silent (fail-open)
#   - a garbled / empty payload stays silent (fail-open)
#   - every response is non-blocking (continue:true, no permissionDecision)
#
# Run: bash plugins/sfdx-core/test/post-deploy-failure.test.sh

set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CTX="$ROOT/sf-context"
PASS=0
FAIL=0

# parse → "<advise|quiet>|<skill-or->|<blocking>"
parse() {
  python3 -c "
import json,sys,re
d=json.load(sys.stdin)
ctx=d.get('hookSpecificOutput',{}).get('additionalContext','') or ''
advise='advise' if ctx else 'quiet'
# The PRIMARY routed skill is the first backtick-name after 'Route to'.
m=re.search(r'Route to \`([a-z][a-z0-9-]+)\`', ctx)
skill=m.group(1) if m else '-'
blocking='block' if d.get('hookSpecificOutput',{}).get('permissionDecision') else 'ok'
if d.get('continue') is not True: blocking='no-continue'
print(f'{advise}|{skill}|{blocking}')
"
}

# check <expected-advise> <expected-skill> <description> <payload-json>
check() {
  local eadv="$1" eskill="$2" desc="$3" payload="$4"
  local out got expected
  out=$(printf '%s' "$payload" | "$CTX" post-deploy-failure)
  got=$(printf '%s' "$out" | parse)
  expected="${eadv}|${eskill}|ok"
  if [ "$got" = "$expected" ]; then
    PASS=$((PASS + 1)); printf '  ok   %-46s → %s\n' "$desc" "$got"
  else
    FAIL=$((FAIL + 1)); printf '  FAIL %-46s → got "%s", expected "%s"\n' "$desc" "$got" "$expected"
    printf '       raw: %s\n' "$out"
  fi
}

echo "sf-context post-deploy-failure — decision (offline, no org)"

# --- failed deploys → advise, name the owning skill ---
check advise platform-metadata-deploy "deploy start failure → platform-metadata-deploy" \
  '{"hook_event_name":"PostToolUseFailure","tool_name":"Bash","tool_input":{"command":"sf project deploy start --source-dir force-app --json"},"error":"Exit code 1"}'

check advise platform-deploy-validate "deploy validate failure → platform-deploy-validate" \
  '{"hook_event_name":"PostToolUseFailure","tool_name":"Bash","tool_input":{"command":"sf project deploy validate --source-dir force-app --json"},"error":"Exit code 1"}'

check advise platform-quick-deploy "deploy quick failure → platform-quick-deploy" \
  '{"hook_event_name":"PostToolUseFailure","tool_name":"Bash","tool_input":{"command":"sf project deploy quick --job-id 0Af000 --json"},"error":"Exit code 1"}'

# --- non-deploy failures → quiet (fail-open) ---
check quiet - "non-deploy sf command stays quiet" \
  '{"hook_event_name":"PostToolUseFailure","tool_name":"Bash","tool_input":{"command":"sf org list --json"},"error":"Exit code 1"}'

check quiet - "unrelated bash failure stays quiet" \
  '{"hook_event_name":"PostToolUseFailure","tool_name":"Bash","tool_input":{"command":"npm test"},"error":"Exit code 1"}'

# --- garbled / empty payloads → quiet (fail-open) ---
check quiet - "empty payload stays quiet" '{}'
check quiet - "garbled payload stays quiet" 'not json at all'

echo ""
echo "  $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
