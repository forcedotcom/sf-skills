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

# Hermetic installed-plugin set: the tier-2 assertions below exercise the two
# uninstalled candidates in the checked-in catalog (`agentforce-adlc` and
# `experience-cms`). Whether the other registered plugins (experience-lwc /
# experience-react) count as installed depends on the developer's real
# ~/.claude/settings.json `enabledPlugins`, which varies by machine — so pin it:
# point CLAUDE_CONFIG_DIR at a throwaway settings.json that marks both existing
# experience plugins enabled. `salesforce-development` is always excluded as the
# plugin running this code.
CFG="$(mktemp -d)"
printf '{"enabledPlugins":{"experience-lwc@salesforce":true,"experience-react@salesforce":true}}' \
  > "$CFG/settings.json"
export CLAUDE_CONFIG_DIR="$CFG"
trap 'rm -rf "$CFG" "${PROJDIR:-}" "${NONPROJ:-}"' EXIT

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

# --- plugin-catalog gap detection (tier 2 — uninstalled plugin match) ------
# When no installed skill owns the bypass op, `_plugin_catalog_match` scores
# the captured user prompt against the uninstalled-plugin catalog. The real
# checked-in catalog has two uninstalled candidates (`agentforce-adlc` and
# `experience-cms`; `salesforce-development` is filtered out as the plugin
# running this code).
# Prompt capture is exercised via the real `prompt-dispatch` (UserPromptSubmit)
# path, not a fallback, so this covers the actual production wiring.
echo ""
echo "  plugin-catalog gap detection (tier 2):"

HIGH_PROMPT="I need to author, discover, scaffold, deploy, test, secure, and optimize Agentforce .agent files for a new employee agent"
# One real owning-domain anchor term, but not enough evidence for proactive
# HIGH. Generic request scaffolding is intentionally ignored by the matcher,
# and a domain-sounding word that isn't one of the plugin's own anchor terms
# (e.g. "employee") no longer carries a match at all -- see anchorTerms.
MEDIUM_PROMPT="curious about agentforce for this"
GENERIC_PROMPT="calculate seven factorial"
DEPLOY_BYPASS_CMD="sf project deploy start --source-dir force-app"

capture_prompt() {
  # capture_prompt <session_id> <prompt_id> <prompt-text>
  printf '{"session_id":"%s","prompt_id":"%s","prompt":"%s"}' "$1" "$2" "$3" \
    | "$CTX" prompt-dispatch >/dev/null
}

# Project gate: tier-2 plugin proposals are scoped to a Salesforce project. From a
# directory with no sfdx-project.json a high-confidence match must stay SILENT —
# outside a project the plugin is global and must not presume (mirrors the SessionStart
# hint + cmd_detect gate). Prove suppression from an explicit non-project temp dir with
# its own session (no marker is written when the gate short-circuits) — the runner cwd
# itself is a DX project (the repo root has sfdx-project.json), so we cannot rely on it.
NONPROJ="$(mktemp -d)"
cd "$NONPROJ" || exit 1
SID_OUTSIDE="skills-first-pr-outside-$$"
capture_prompt "$SID_OUTSIDE" "p1" "$HIGH_PROMPT"
DEPLOY_OUTSIDE="{\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"$DEPLOY_BYPASS_CMD\"},\"session_id\":\"$SID_OUTSIDE\",\"prompt_id\":\"p1\"}"
check quiet - "high-confidence plugin match stays silent OUTSIDE a project (gate)" "$DEPLOY_OUTSIDE"

# THEN cd into a throwaway project dir so the remaining tier-2 checks exercise the
# in-project path (gate open).
PROJDIR="$(mktemp -d)"
printf '{"packageDirectories":[{"path":"force-app","default":true}]}' > "$PROJDIR/sfdx-project.json"
cd "$PROJDIR" || exit 1

# UserPromptSubmit now proposes a high-confidence match before any tool call and
# opens the session decision workflow. Until the user completes/declines it or
# submits a new substantive task, the later bypass gate must stay fully quiet —
# it cannot inject a second recommendation into the active workflow.
SID_HIGH="skills-first-pr-high-$$"
capture_prompt "$SID_HIGH" "p1" "$HIGH_PROMPT"
DEPLOY_HIGH="{\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"$DEPLOY_BYPASS_CMD\"},\"session_id\":\"$SID_HIGH\",\"prompt_id\":\"p1\"}"
check quiet - "active prompt proposal suppresses later bypass recommendation" "$DEPLOY_HIGH"

# Same session, same workflow remains quiet on every later tool call.
check quiet - "active workflow suppresses repeat bypass recommendation" "$DEPLOY_HIGH"

# Medium-confidence input does not open a proactive prompt workflow, so the
# later reactive bypass may still surface it as a warning (never a deny).
SID_MED="skills-first-pr-medium-$$"
capture_prompt "$SID_MED" "p1" "$MEDIUM_PROMPT"
DEPLOY_MED="{\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"$DEPLOY_BYPASS_CMD\"},\"session_id\":\"$SID_MED\",\"prompt_id\":\"p1\"}"
check warn agentforce-adlc "medium-confidence plugin match warns, never denies" "$DEPLOY_MED"

# Generic prompt, no catalog entry clears the threshold → silent, identical
# to today's no-match behavior.
SID_GEN="skills-first-pr-generic-$$"
capture_prompt "$SID_GEN" "p1" "$GENERIC_PROMPT"
DEPLOY_GEN="{\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"$DEPLOY_BYPASS_CMD\"},\"session_id\":\"$SID_GEN\",\"prompt_id\":\"p1\"}"
check quiet - "generic prompt with no plugin match stays silent" "$DEPLOY_GEN"

# Live decline regression: the model correctly invokes the plugin's guarded
# control command after an explicit decline. That internal command must not be
# rescored as a raw implementation bypass, or the advisory denies it and turns
# words in the decline prompt into unrelated replacement plugin proposals.
SID_DECLINE="skills-first-pr-decline-$$"
capture_prompt "$SID_DECLINE" "p1" "$HIGH_PROMPT"
capture_prompt "$SID_DECLINE" "p2" \
  "no thanks, do not install agentforce-adlc"
DECLINE_CONTROL="{\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"$CTX plugin-install agentforce-adlc --decline\"},\"session_id\":\"$SID_DECLINE\",\"prompt_id\":\"p2\"}"
check quiet - "internal plugin decline command bypasses task advisory" "$DECLINE_CONTROL"

# The exemption is whole-command and grammar-bound. Appending a raw owned
# operation makes the command a compound, so normal tier-1 enforcement still
# detects and denies the Salesforce CLI bypass.
DECLINE_COMPOUND="{\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"$CTX plugin-install agentforce-adlc --decline; sf data query --query x\"},\"session_id\":\"$SID_DECLINE\",\"prompt_id\":\"p2\"}"
check_deny platform-soql-query \
  "compound command cannot inherit plugin-install control exemption" \
  "$DECLINE_COMPOUND"

# Tier-1 precedence: an installed-skill-owned op takes the enforcement deny
# path even when the captured prompt would also clear the tier-2 threshold —
# tier 2 is only reached when tier 1 finds no owner.
SID_T1="skills-first-pr-tier1-$$"
capture_prompt "$SID_T1" "p1" "$HIGH_PROMPT"
APEX_TEST_T1="{\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"sf apex run test --synchronous --json\"},\"session_id\":\"$SID_T1\",\"prompt_id\":\"p1\"}"
check_deny platform-apex-test-run "installed-skill enforcement still wins over a tier-2 plugin match" "$APEX_TEST_T1"

# Cross-surface lock: UserPromptSubmit proposes first; an explicit discovery
# query may inspect the same candidate, but the later bypass gate still cannot
# add recommendation text while the decision workflow is active.
SID_CROSS="skills-first-pr-cross-$$"
capture_prompt "$SID_CROSS" "p1" "$HIGH_PROMPT"
"$CTX" plugin-match --session-id "$SID_CROSS" "$HIGH_PROMPT" >/dev/null
DEPLOY_CROSS="{\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"$DEPLOY_BYPASS_CMD\"},\"session_id\":\"$SID_CROSS\",\"prompt_id\":\"p1\"}"
check quiet - "active workflow suppresses bypass after discovery reuse" "$DEPLOY_CROSS"

echo ""
echo "  $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
