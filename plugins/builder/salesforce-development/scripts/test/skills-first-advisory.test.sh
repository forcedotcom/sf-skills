#!/bin/bash
# Decision test for `sf-context skills-first-advisory` (issue #286).
#
# The check reads a PreToolUse `tool_input` payload from stdin and routes
# bypass-prone operations (raw metadata edits, raw `sf apex/retrieve/data` calls)
# to the owning skill. Ops whose owning skill is on the `_ENFORCEABLE_SKILLS`
# allow-list (query, retrieve, apex-test-run, manifest) are BLOCKED with a
# `deny` + redirect; every other match is WARN-ONLY (`continue: true`). This test
# asserts, fully offline (no org):
#   - allow-listed bypass-prone ops deny and name the expected skill
#   - other bypass-prone ops warn and name the expected skill
#   - unrelated ops stay silent (advisory text absent), non-blocking
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
hso=d.get('hookSpecificOutput',{})
ctx=hso.get('additionalContext','')
warn='warn' if ctx else 'quiet'
decision=hso.get('permissionDecision')
# The skill name is backtick-wrapped in the advisory text (additionalContext) on
# a warn, and in permissionDecisionReason on an enforcement deny — search both.
m=re.search(r'\`([a-z][a-z0-9-]+)\`', ctx or hso.get('permissionDecisionReason',''))
skill=m.group(1) if m else '-'
if decision:
    # A blocking deny legitimately omits top-level continue (hook spec) — report
    # the decision verbatim so an enforce assertion can expect 'block'/'deny'.
    blocking=decision if decision!='deny' else 'block'
else:
    # Warn-only path: continue MUST be true; fold a violation in so it fails loudly.
    blocking='ok' if d.get('continue') is True else 'no-continue'
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

# check_deny <expected-skill> <description> <payload-json>
# An allow-listed op is BLOCKED: deny carries a permissionDecision (block) and no
# additionalContext (quiet), so the parsed triple is "quiet|<skill>|block".
check_deny() {
  local eskill="$1" desc="$2" payload="$3"
  local out got expected
  out=$(printf '%s' "$payload" | "$CTX" skills-first-advisory)
  got=$(printf '%s' "$out" | parse)
  expected="quiet|${eskill}|block"
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

# --- allow-listed raw CLI calls → DENY, name the owning skill ---
check_deny platform-apex-test-run "sf apex run test → deny" \
  '{"tool_name":"Bash","tool_input":{"command":"sf apex run test --synchronous --json"}}'

check_deny platform-metadata-retrieve "sf project retrieve → deny" \
  '{"tool_name":"Bash","tool_input":{"command":"sf project retrieve start --metadata ApexClass"}}'

check_deny platform-soql-query "sf data query → deny" \
  '{"tool_name":"Bash","tool_input":{"command":"sf data query --query \"SELECT Id FROM Account\" --json"}}'

check_deny platform-manifest-generate "sf project generate manifest → deny" \
  '{"tool_name":"Bash","tool_input":{"command":"sf project generate manifest --source-dir force-app"}}'

# --- non-allow-listed raw CLI call → warn (stays advisory) ---
check warn platform-apex-anonymous-run "sf apex run (anon)" \
  '{"tool_name":"Bash","tool_input":{"command":"sf apex run --file scripts/anon.apex"}}'

# --- hand-authoring a deploy manifest → DENY, name platform-manifest-generate ---
check_deny platform-manifest-generate "Write package.xml → deny" \
  '{"tool_name":"Write","tool_input":{"file_path":"manifest/package.xml"}}'

check_deny platform-manifest-generate "Write destructiveChanges.xml → deny" \
  '{"tool_name":"Write","tool_input":{"file_path":"manifest/destructiveChanges.xml"}}'

check quiet - "small Edit of an existing package.xml stays quiet (not authoring)" \
  '{"tool_name":"Edit","tool_input":{"file_path":"manifest/package.xml"}}'

# F4 — manifest detection by content (non-standard filename) and Windows path.
check_deny platform-manifest-generate "Write pkg.xml with Package body → deny (by content)" \
  '{"tool_name":"Write","tool_input":{"file_path":"config/pkg.xml","content":"<?xml version=\"1.0\"?><Package xmlns=\"http://soap.sforce.com/2006/04/metadata\"><version>60.0</version></Package>"}}'

check_deny platform-manifest-generate "Write Windows-path package.xml → deny" \
  '{"tool_name":"Write","tool_input":{"file_path":"manifest\\package.xml"}}'

check quiet - "Write destructiveChanges-notes.xml stays quiet (not a real manifest name)" \
  '{"tool_name":"Write","tool_input":{"file_path":"docs/destructiveChanges-notes.xml","content":"just notes"}}'

# F4 (MultiEdit) — MultiEdit's text lives in edits[].new_string, not a top-level
# content field, so content detection must read the edit bodies or a non-standard
# manifest filename slips past. Also confirm MultiEdit by-name still denies.
check_deny platform-manifest-generate "MultiEdit pkg.xml with Package body → deny (by content)" \
  '{"tool_name":"MultiEdit","tool_input":{"file_path":"config/pkg.xml","edits":[{"old_string":"","new_string":"<?xml version=\"1.0\"?><Package xmlns=\"http://soap.sforce.com/2006/04/metadata\"><version>60.0</version></Package>"}]}}'

check_deny platform-manifest-generate "MultiEdit package.xml → deny (by name)" \
  '{"tool_name":"MultiEdit","tool_input":{"file_path":"manifest/package.xml","edits":[{"old_string":"a","new_string":"b"}]}}'

check quiet - "MultiEdit non-manifest .xml (no Package body) stays quiet" \
  '{"tool_name":"MultiEdit","tool_input":{"file_path":"config/settings.xml","edits":[{"old_string":"a","new_string":"<config><setting>x</setting></config>"}]}}'

# F5 — whitespace / colon / sfdx surface variants of enforced CLI calls → deny.
check_deny platform-soql-query "sf data query with extra whitespace → deny" \
  '{"tool_name":"Bash","tool_input":{"command":"sf  data   query --query \"SELECT Id FROM Account\""}}'

check_deny platform-soql-query "sfdx force:data:soql:query → deny" \
  '{"tool_name":"Bash","tool_input":{"command":"sfdx force:data:soql:query -q \"SELECT Id FROM Account\""}}'

check_deny platform-apex-test-run "sf apex:test:run colon form → deny" \
  '{"tool_name":"Bash","tool_input":{"command":"sf apex:test:run --synchronous"}}'

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
# that skill's owned ops; a different owner still warns; a new prompt_id or
# session re-arms it. Markers live in a cwd-independent runtime namespace keyed
# by (session_id, prompt_id), so use process-unique ids to isolate this run.
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
# A session-less ledger must NOT suppress a real-session call (no cross-key bleed).
check warn platform-apex-generate "session-less ledger does not suppress a keyed session" \
  "{\"tool_name\":\"Edit\",\"tool_input\":{\"file_path\":\"force-app/main/default/classes/Foo.cls\"},\"session_id\":\"$SID-9\",\"prompt_id\":\"p-s9\"}"

# No-deadlock: once an ENFORCEABLE skill has dispatched this turn, its owned op is
# suppressed to `continue: true` (NOT denied), so the skill's own `sf` calls flow
# through and enforcement can't deadlock. Session ids are process-unique ($$)
# because the runtime namespace is a shared temp dir.
QUERY="{\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"sf data query --query \\\"SELECT Id FROM Account\\\"\"},\"session_id\":\"$SID-nd\",\"prompt_id\":\"p1\"}"
check_deny platform-soql-query "sf data query denies before dispatch" "$QUERY"
printf '%s' "{\"session_id\":\"$SID-nd\",\"prompt_id\":\"p1\",\"tool_input\":{\"skill\":\"salesforce-development:platform-soql-query\"}}" \
  | "$CTX" record-skill-dispatch >/dev/null
check quiet - "sf data query allowed through after platform-soql-query dispatch (no deadlock)" "$QUERY"

# F3 — delegate satisfies the deny: platform-soql-query delegates EXECUTION to
# platform-data-manage, so a turn where the delegate dispatched must let the raw
# `sf data query` through rather than re-deny (else the executor deadlocks).
QUERY_S3="{\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"sf data query --query \\\"SELECT Id FROM Account\\\"\"},\"session_id\":\"$SID-dg\",\"prompt_id\":\"p3\"}"
check_deny platform-soql-query "sf data query denies before any dispatch (delegate)" "$QUERY_S3"
printf '%s' "{\"session_id\":\"$SID-dg\",\"prompt_id\":\"p3\",\"tool_input\":{\"skill\":\"salesforce-development:platform-data-manage\"}}" \
  | "$CTX" record-skill-dispatch >/dev/null
check quiet - "sf data query allowed after platform-data-manage dispatch (delegate, F3)" "$QUERY_S3"

# F1 — CWD drift must not break suppression: record the dispatch, then `cd`
# elsewhere before the owning skill's own `sf` call. The cwd-independent runtime
# dir means that call still hits its own marker and is allowed through.
printf '%s' "{\"session_id\":\"$SID-cw\",\"prompt_id\":\"p4\",\"tool_input\":{\"skill\":\"salesforce-development:platform-metadata-retrieve\"}}" \
  | "$CTX" record-skill-dispatch >/dev/null
RETRIEVE_S4="{\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"sf project retrieve start --metadata ApexClass\"},\"session_id\":\"$SID-cw\",\"prompt_id\":\"p4\"}"
CWD_DRIFT="$(mktemp -d)"
pushd "$CWD_DRIFT" >/dev/null
check quiet - "retrieve allowed through after dispatch despite CWD change (F1)" "$RETRIEVE_S4"
popd >/dev/null
rm -rf "$CWD_DRIFT"

popd >/dev/null

echo ""
echo "  $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
