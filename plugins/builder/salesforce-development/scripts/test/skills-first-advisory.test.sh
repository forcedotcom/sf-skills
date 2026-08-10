#!/bin/bash
# Decision test for `sf-context skills-first-advisory` (issue #286).
#
# The advisory reads a PreToolUse `tool_input` payload from stdin and emits a
# WARN-ONLY nudge toward the owning skill on bypass-prone operations (raw
# metadata edits, raw `sf apex/retrieve/data` calls). It must NEVER block — every
# response carries `continue: true`. This test asserts, fully offline (no org):
#   - bypass-prone ops emit an advisory naming the expected skill
#   - unrelated ops stay silent (advisory text absent)
#   - every response is non-blocking (continue:true, no permissionDecision)
#
# Run: bash plugins/sfdx-core/test/skills-first-advisory.test.sh

set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CTX="$ROOT/sf-context"
PASS=0
FAIL=0

# Parse the hook JSON, print a compact "<has-advisory>|<skill-or->|<blocking>" triple:
#   has-advisory: "warn" if additionalContext present, else "quiet"
#   skill:        first `skill-name` mentioned in the advisory (backtick-wrapped), or "-"
#   blocking:     "block" if a permissionDecision is present, else "ok"
parse() {
  python3 -c "
import json,sys,re
d=json.load(sys.stdin)
ctx=d.get('hookSpecificOutput',{}).get('additionalContext','')
warn='warn' if ctx else 'quiet'
m=re.search(r'\`([a-z][a-z0-9-]+)\`', ctx)
skill=m.group(1) if m else '-'
blocking='block' if d.get('hookSpecificOutput',{}).get('permissionDecision') else 'ok'
cont=d.get('continue')
# continue must always be true; fold a violation into the blocking field so it fails loudly
if cont is not True: blocking='no-continue'
print(f'{warn}|{skill}|{blocking}')
"
}

# check <expected-warn> <expected-skill> <description> <payload-json>
check() {
  local ewarn="$1" eskill="$2" desc="$3" payload="$4"
  local out got expected
  out=$(printf '%s' "$payload" | "$CTX" skills-first-advisory)
  got=$(printf '%s' "$out" | parse)
  expected="${ewarn}|${eskill}|ok"
  if [ "$got" = "$expected" ]; then
    PASS=$((PASS + 1)); printf '  ok   %-44s → %s\n' "$desc" "$got"
  else
    FAIL=$((FAIL + 1)); printf '  FAIL %-44s → got "%s", expected "%s"\n' "$desc" "$got" "$expected"
    printf '       raw: %s\n' "$out"
  fi
}

echo "sf-context skills-first-advisory — decision (offline, no org)"

# --- bypass-prone Apex source edits → warn, name platform-apex-generate (#413) ---
check warn platform-apex-generate "Apex .cls edit" \
  '{"tool_name":"Edit","tool_input":{"file_path":"force-app/main/default/classes/MyService.cls"}}'

check warn platform-apex-test-generate "Apex *Test.cls edit" \
  '{"tool_name":"Write","tool_input":{"file_path":"force-app/main/default/classes/MyServiceTest.cls"}}'

check warn platform-apex-generate "Apex .trigger edit" \
  '{"tool_name":"Edit","tool_input":{"file_path":"force-app/main/default/triggers/AccountTrigger.trigger"}}'

check quiet - "Apex .cls-meta.xml sidecar stays quiet" \
  '{"tool_name":"Edit","tool_input":{"file_path":"force-app/main/default/classes/MyService.cls-meta.xml"}}'

# --- bypass-prone metadata edits → warn, name the owning platform metadata skill ---
check warn platform-custom-field-generate "custom field-meta.xml edit" \
  '{"tool_name":"Edit","tool_input":{"file_path":"force-app/main/default/objects/Account/fields/Foo__c.field-meta.xml"}}'

check warn platform-custom-object-generate "custom object-meta.xml edit" \
  '{"tool_name":"Write","tool_input":{"file_path":"force-app/main/default/objects/Widget__c/Widget__c.object-meta.xml"}}'

check warn platform-permission-set-generate "permissionset-meta.xml edit" \
  '{"tool_name":"Edit","tool_input":{"file_path":"force-app/main/default/permissionsets/Admin.permissionset-meta.xml"}}'

check warn automation-flow-generate "flow-meta.xml edit" \
  '{"tool_name":"Edit","tool_input":{"file_path":"force-app/main/default/flows/My_Flow.flow-meta.xml"}}'

# --- report metadata now has an owning skill (#445) ---
check warn platform-report-generate "report-meta.xml edit" \
  '{"tool_name":"Edit","tool_input":{"file_path":"force-app/main/default/reports/ComplianceReports/Cases_By_Month.report-meta.xml"}}'

# --- owner-less metadata types stay quiet (no phantom-skill nudge, #445 item 3) ---
check quiet - "reportFolder-meta.xml has no owning skill" \
  '{"tool_name":"Write","tool_input":{"file_path":"force-app/main/default/reports/ComplianceReports.reportFolder-meta.xml"}}'

check quiet - "labels-meta.xml has no owning skill" \
  '{"tool_name":"Edit","tool_input":{"file_path":"force-app/main/default/labels/CustomLabels.labels-meta.xml"}}'

check quiet - "layout-meta.xml has no owning skill" \
  '{"tool_name":"Edit","tool_input":{"file_path":"force-app/main/default/layouts/Account-Account Layout.layout-meta.xml"}}'

# --- bypass-prone raw CLI calls → warn, name the owning skill ---
check warn platform-apex-test-run "sf apex run test" \
  '{"tool_name":"Bash","tool_input":{"command":"sf apex run test --synchronous --json"}}'

check warn platform-apex-anonymous-run "sf apex run (anon)" \
  '{"tool_name":"Bash","tool_input":{"command":"sf apex run --file scripts/anon.apex"}}'

check warn platform-metadata-retrieve "sf project retrieve" \
  '{"tool_name":"Bash","tool_input":{"command":"sf project retrieve start --metadata ApexClass"}}'

check warn platform-soql-query "sf data query" \
  '{"tool_name":"Bash","tool_input":{"command":"sf data query --query \"SELECT Id FROM Account\" --json"}}'

# --- unrelated ops → quiet (no advisory) ---
check quiet - "non-metadata Edit (README)" \
  '{"tool_name":"Edit","tool_input":{"file_path":"README.md"}}'

check quiet - "unrelated Bash (ls)" \
  '{"tool_name":"Bash","tool_input":{"command":"ls -la"}}'

check quiet - "deploy is handled by verify-org, not here" \
  '{"tool_name":"Bash","tool_input":{"command":"sf project deploy start --source-dir force-app"}}'

check quiet - "empty payload" '{}'

# --- turn-aware suppression (#415) -------------------------------------------
# Once the owning skill has dispatched THIS turn, the advisory stays quiet for
# that skill's owned ops; a different owner still warns; a new prompt_id or a
# different session re-arms it. Prompt markers live in a cwd-independent private
# runtime namespace, so use process-unique ids to keep this run isolated.
echo ""
echo "  turn-aware suppression (#415):"
TMPDIR_415="$(mktemp -d)"
trap 'rm -rf "$TMPDIR_415"' EXIT
pushd "$TMPDIR_415" >/dev/null

SID="skills-first-$$"
CLS="{\"tool_name\":\"Edit\",\"tool_input\":{\"file_path\":\"force-app/main/default/classes/Foo.cls\"},\"session_id\":\"$SID\",\"prompt_id\":\"prompt-1\"}"
PSET="{\"tool_name\":\"Edit\",\"tool_input\":{\"file_path\":\"force-app/main/default/permissionsets/Admin.permissionset-meta.xml\"},\"session_id\":\"$SID\",\"prompt_id\":\"prompt-1\"}"

# Clean slate: no ledger → first .cls edit warns.
check warn platform-apex-generate "1st .cls edit warns (no dispatch yet)" "$CLS"

# Record a platform-apex-generate dispatch for session s1 (the Skill-tool hook's job).
# The Skill tool carries a plugin-qualified name; the hook normalizes on the last
# ":"-segment, so the plugin prefix here is our plugin, not the upstream sfdx-apex.
printf '%s' "{\"session_id\":\"$SID\",\"prompt_id\":\"prompt-1\",\"tool_input\":{\"skill\":\"salesforce-development:platform-apex-generate\"}}" \
  | "$CTX" record-skill-dispatch >/dev/null

# Same skill, same turn → quiet.
check quiet - "2nd .cls edit quiet after platform-apex-generate dispatch" "$CLS"

# Different owner (permission set) → still warns (per-skill scope).
check warn platform-permission-set-generate "permissionset edit still warns (per-skill scope)" "$PSET"

# Different session → warns (no cross-session suppression).
check warn platform-apex-generate ".cls edit in another session warns" \
  "{\"tool_name\":\"Edit\",\"tool_input\":{\"file_path\":\"force-app/main/default/classes/Foo.cls\"},\"session_id\":\"$SID-other\",\"prompt_id\":\"prompt-1\"}"

# New native prompt id → re-arms the nudge without resetting shared state.
check warn platform-apex-generate ".cls edit warns again in prompt 2" \
  "{\"tool_name\":\"Edit\",\"tool_input\":{\"file_path\":\"force-app/main/default/classes/Foo.cls\"},\"session_id\":\"$SID\",\"prompt_id\":\"prompt-2\"}"

# Hardening: malformed unkeyed state must never suppress a session-less advisory.
printf '%s' '{"tool_input":{"skill":"platform-apex-generate"}}' | "$CTX" record-skill-dispatch >/dev/null
check warn platform-apex-generate "session-less ledger does not suppress session-less call" \
  '{"tool_name":"Edit","tool_input":{"file_path":"force-app/main/default/classes/Foo.cls"}}'

popd >/dev/null

echo ""
echo "  $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
