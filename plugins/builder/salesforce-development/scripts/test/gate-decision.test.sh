#!/bin/bash
# End-to-end decision test for sf-deploy-gate (issue #259).
#
# Stubs `sf` on PATH so the full prod-check / destructive path runs offline —
# no live org. Asserts the hook's JSON decision (allow vs. deny) for each org
# bucket, proving the #259 fix end-to-end: a trial org must ALLOW, not block.
#
# Run: bash plugins/sfdx-deploy/test/gate-decision.test.sh

set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
GATE="$ROOT/sf-deploy-gate"
PASS=0
FAIL=0

# Build a temp dir with a fake `sf` whose `org display` / `config get` output we
# control via env vars, then put it first on PATH.
STUB_DIR=$(mktemp -d)
trap 'rm -rf "$STUB_DIR"' EXIT
cat > "$STUB_DIR/sf" <<'STUB'
#!/bin/bash
# Minimal sf stub: only the two subcommands the gate calls.
case "$*" in
  "config get target-org --json")
    printf '{"result":[{"name":"target-org","value":"%s"}]}' "${STUB_DEFAULT_ORG:-stuborg}"
    ;;
  "org display --target-org "*" --json"|"org display "*"--json")
    printf '%s' "${STUB_ORG_JSON:-{\}}"
    ;;
  *) printf '{}' ;;
esac
STUB
chmod +x "$STUB_DIR/sf"
export PATH="$STUB_DIR:$PATH"

# decision <expected: allow|deny> <description> <command> <org-json>
decision() {
  local expected="$1" desc="$2" cmd="$3" org_json="$4"
  export STUB_ORG_JSON="$org_json"
  local out got
  out=$(printf '{"tool_input":{"command":"%s"}}' "$cmd" | "$GATE" prod-check)
  got=$(printf '%s' "$out" | python3 -c "
import json,sys
d=json.load(sys.stdin)
print('deny' if d.get('hookSpecificOutput',{}).get('permissionDecision')=='deny' else 'allow')
")
  if [ "$got" = "$expected" ]; then
    PASS=$((PASS + 1)); printf '  ok   %-46s → %s\n' "$desc" "$got"
  else
    FAIL=$((FAIL + 1)); printf '  FAIL %-46s → got "%s", expected "%s"\n' "$desc" "$got" "$expected"
    printf '       raw: %s\n' "$out"
  fi
}

echo "sf-deploy-gate prod-check — end-to-end decision (stubbed sf)"

# The #259 case: OrgFarm trial must ALLOW (was wrongly denied as production).
decision allow "trial OrgFarm → allow" \
  "sf project deploy start --source-dir force-app --target-org mytrial" \
  '{"result":{"isSandbox":null,"isScratch":null,"instanceUrl":"https://orgfarm-x.develop.my.salesforce.com"}}'

decision allow "dry-run against trial → allow" \
  "sf project deploy start --dry-run -o mytrial" \
  '{"result":{"isSandbox":false,"isScratch":false,"instanceUrl":"https://my.develop.my.salesforce.com"}}'

decision allow "sandbox → allow" \
  "sf project deploy start --target-org sbx" \
  '{"result":{"isSandbox":true,"instanceUrl":"https://acme--dev.sandbox.my.salesforce.com"}}'

decision allow "scratch → allow" \
  "sf project deploy start --target-org scr" \
  '{"result":{"isSandbox":false,"isScratch":true,"instanceUrl":"https://x.scratch.my.salesforce.com"}}'

# Genuine production still blocks.
decision deny "production → deny" \
  "sf project deploy start --target-org prod" \
  '{"result":{"isSandbox":false,"isScratch":false,"instanceUrl":"https://acme.my.salesforce.com"}}'

# Production WITH explicit confirmation flag → allow (override path preserved).
decision allow "production + CONFIRM_PROD=1 → allow" \
  "CONFIRM_PROD=1 sf project deploy start --target-org prod" \
  '{"result":{"isSandbox":false,"isScratch":false,"instanceUrl":"https://acme.my.salesforce.com"}}'

# --- Destructive-changes deploys (#407) -------------------------------------
# A destructiveChanges manifest reaches the gate as an ordinary deploy, but has
# the blast radius of `sf project delete` and must be gated like one on prod.
decision deny "destructive manifest → prod → deny" \
  "sf project deploy start --manifest destructiveChanges.xml --target-org prod" \
  '{"result":{"isSandbox":false,"isScratch":false,"instanceUrl":"https://acme.my.salesforce.com"}}'

# CONFIRM_PROD does NOT override a destructive prod deploy — it routes to the skill.
decision deny "destructive + CONFIRM_PROD=1 → prod → deny" \
  "CONFIRM_PROD=1 sf project deploy start --post-destructive-changes destructiveChanges.xml -o prod" \
  '{"result":{"isSandbox":false,"isScratch":false,"instanceUrl":"https://acme.my.salesforce.com"}}'

# Non-prod destructive deploys are advised, not blocked.
decision allow "destructive manifest → sandbox → allow" \
  "sf project deploy start --pre-destructive-changes destructiveChanges.xml --target-org sbx" \
  '{"result":{"isSandbox":true,"instanceUrl":"https://acme--dev.sandbox.my.salesforce.com"}}'

# Ordinary (non-destructive) prod deploy still uses the standard confirmation path.
decision deny "ordinary deploy → prod → deny (unchanged)" \
  "sf project deploy start --source-dir force-app --target-org prod" \
  '{"result":{"isSandbox":false,"isScratch":false,"instanceUrl":"https://acme.my.salesforce.com"}}'

# --- Command self-gate ------------------------------------------------------
# Some Claude Code builds ignore the plugin.json `if:` matcher and fire every
# PreToolUse Bash hook on every command. A NON-deploy command must ALLOW without
# classifying — even against a production org (the gate never even reads it).
decision allow "non-deploy command → allow (self-gated, prod org ignored)" \
  "cd /tmp && grep -r foo ." \
  '{"result":{"isSandbox":false,"isScratch":false,"instanceUrl":"https://acme.my.salesforce.com"}}'

# #1030 review: a merely QUOTED mention of the deploy command in an unrelated
# command must ALLOW without classifying — the regex self-gate wrongly matched the
# quoted substring and denied the grep against a prod org. Quote/position-aware now.
decision allow "quoted deploy mention → allow (not gated)" \
  'grep -r \"sf project deploy start\" .' \
  '{"result":{"isSandbox":false,"isScratch":false,"instanceUrl":"https://acme.my.salesforce.com"}}'

decision allow "deploy string in echo → allow (not gated)" \
  'echo \"remember: sf project deploy start\"' \
  '{"result":{"isSandbox":false,"isScratch":false,"instanceUrl":"https://acme.my.salesforce.com"}}'

# Sub-command scope: a check-only `validate` is NOT a prod-mutating deploy, so it
# must ALLOW (self-gated off) even against a prod org — the gate is scoped to
# start/quick, matching plugin.json. (A bare-substring self-gate wrongly denied it.)
decision allow "validate against prod → allow (not gated)" \
  "sf project deploy validate --target-org prod" \
  '{"result":{"isSandbox":false,"isScratch":false,"instanceUrl":"https://acme.my.salesforce.com"}}'

# Whitespace-flexible self-gate: `sf` accepts arbitrary spacing, so an unusual-but-
# valid multi-space deploy must still be GATED — a single-space substring would
# miss it and fail OPEN on the production gate.
decision deny "multi-space deploy start → prod → deny" \
  "sf  project   deploy start --target-org prod" \
  '{"result":{"isSandbox":false,"isScratch":false,"instanceUrl":"https://acme.my.salesforce.com"}}'

# #1030 review (thread 4): a prod deploy wrapped by a shell builtin or a control
# structure still EXECUTES the deploy, so the command-position matcher must unwrap
# `command`/`time`/`then …` etc. and still reach the production gate.
decision deny "command-wrapped deploy → prod → deny" \
  "command sf project deploy start --target-org prod" \
  '{"result":{"isSandbox":false,"isScratch":false,"instanceUrl":"https://acme.my.salesforce.com"}}'

decision deny "control-structure-wrapped deploy → prod → deny" \
  "if true; then sf project deploy start --target-org prod; fi" \
  '{"result":{"isSandbox":false,"isScratch":false,"instanceUrl":"https://acme.my.salesforce.com"}}'

# #1030 review (follow-up): a deploy used AS the control CONDITION (segment leads
# with `if`/`while`/`until`, not `then`) still executes — must still reach the gate.
decision deny "deploy as if-condition → prod → deny" \
  "if sf project deploy start --target-org prod; then :; fi" \
  '{"result":{"isSandbox":false,"isScratch":false,"instanceUrl":"https://acme.my.salesforce.com"}}'

decision deny "deploy as while-condition → prod → deny" \
  "while sf project deploy start --target-org prod; do :; done" \
  '{"result":{"isSandbox":false,"isScratch":false,"instanceUrl":"https://acme.my.salesforce.com"}}'

# #1030 adversarial review (finding 1): shlex defaulted to commenters='#', so a bare
# '#' truncated the line and dropped a trailing '&& sf project deploy start' — the
# deploy then slipped the gate ungated. Must still DENY against prod now.
decision deny "deploy after '#' comment → prod → deny" \
  "curl http://example.com/a#b && sf project deploy start --target-org prod" \
  '{"result":{"isSandbox":false,"isScratch":false,"instanceUrl":"https://acme.my.salesforce.com"}}'

# #1030 adversarial review (finding 2): a heredoc-delivered deploy tokenizes with the
# heredoc delimiter word shielding the real first command. Per-line scan closes it.
decision deny "heredoc-delivered deploy → prod → deny" \
  "bash <<EOF\nsf project deploy start --target-org prod\nEOF" \
  '{"result":{"isSandbox":false,"isScratch":false,"instanceUrl":"https://acme.my.salesforce.com"}}'

# #1030 adversarial verification (family A1): bash ANSI-C $'...' quoting. shlex reads
# $'start' as the token $start and missed it; bash runs it as start. The leading $ is
# now stripped so a prod deploy hidden this way still DENIES.
decision deny "ANSI-C \$'start' deploy → prod → deny" \
  "sf project deploy \$'start' --target-org prod" \
  '{"result":{"isSandbox":false,"isScratch":false,"instanceUrl":"https://acme.my.salesforce.com"}}'

# #1030 adversarial verification (family A2): bash locale $"..." quoting, same root
# cause / same fix (leading $ stripped). Must DENY against prod.
decision deny 'locale $"start" deploy → prod → deny' \
  'sf project deploy $\"start\" --target-org prod' \
  '{"result":{"isSandbox":false,"isScratch":false,"instanceUrl":"https://acme.my.salesforce.com"}}'

# Same for the destructive subcommand: a non-delete command must ALLOW.
NON_DELETE_OUT=$(printf '{"tool_input":{"command":"ls -la"}}' | \
  STUB_ORG_JSON='{"result":{"instanceUrl":"https://acme.my.salesforce.com"}}' "$GATE" destructive)
if printf '%s' "$NON_DELETE_OUT" | grep -q '"continue": true'; then
  PASS=$((PASS + 1)); printf '  ok   %-46s → allow\n' "destructive: non-delete → allow (self-gated)"
else
  FAIL=$((FAIL + 1)); printf '  FAIL %-46s raw: %s\n' "destructive: non-delete → allow (self-gated)" "$NON_DELETE_OUT"
fi

# #1030 review: a quoted mention of `sf project delete` in an unrelated command
# must ALLOW without classifying (quote/position-aware self-gate).
QUOTED_DELETE_OUT=$(printf '{"tool_input":{"command":"grep -r \\"sf project delete\\" ."}}' | \
  STUB_ORG_JSON='{"result":{"instanceUrl":"https://acme.my.salesforce.com"}}' "$GATE" destructive)
if printf '%s' "$QUOTED_DELETE_OUT" | grep -q '"continue": true'; then
  PASS=$((PASS + 1)); printf '  ok   %-46s → allow\n' "destructive: quoted mention → allow (self-gated)"
else
  FAIL=$((FAIL + 1)); printf '  FAIL %-46s raw: %s\n' "destructive: quoted mention → allow (self-gated)" "$QUOTED_DELETE_OUT"
fi

# #1030 review (thread 4): the same unwrap fix must cover the destructive gate —
# a shell-wrapped `sf project delete` against prod must still DENY.
WRAPPED_DELETE_OUT=$(printf '{"tool_input":{"command":"command sf project delete --target-org prod"}}' | \
  STUB_ORG_JSON='{"result":{"instanceUrl":"https://acme.my.salesforce.com"}}' "$GATE" destructive)
if printf '%s' "$WRAPPED_DELETE_OUT" | grep -q '"deny"'; then
  PASS=$((PASS + 1)); printf '  ok   %-46s → deny\n' "destructive: command-wrapped delete → deny"
else
  FAIL=$((FAIL + 1)); printf '  FAIL %-46s raw: %s\n' "destructive: command-wrapped delete → deny" "$WRAPPED_DELETE_OUT"
fi

# #1030 adversarial review (finding 1, broadened): the '#'-comment bypass also hit
# the destructive gate — a delete after a bare '#' against prod must still DENY.
COMMENT_DELETE_OUT=$(printf '{"tool_input":{"command":"echo see #issue && sf project delete source --target-org prod"}}' | \
  STUB_ORG_JSON='{"result":{"instanceUrl":"https://acme.my.salesforce.com"}}' "$GATE" destructive)
if printf '%s' "$COMMENT_DELETE_OUT" | grep -q '"deny"'; then
  PASS=$((PASS + 1)); printf '  ok   %-46s → deny\n' "destructive: delete after '#' comment → deny"
else
  FAIL=$((FAIL + 1)); printf '  FAIL %-46s raw: %s\n' "destructive: delete after '#' comment → deny" "$COMMENT_DELETE_OUT"
fi

# #1030 adversarial review (finding 2): heredoc-delivered delete against prod → DENY.
HEREDOC_DELETE_OUT=$(printf '{"tool_input":{"command":"bash <<EOF\\nsf project delete source --target-org prod\\nEOF"}}' | \
  STUB_ORG_JSON='{"result":{"instanceUrl":"https://acme.my.salesforce.com"}}' "$GATE" destructive)
if printf '%s' "$HEREDOC_DELETE_OUT" | grep -q '"deny"'; then
  PASS=$((PASS + 1)); printf '  ok   %-46s → deny\n' "destructive: heredoc-delivered delete → deny"
else
  FAIL=$((FAIL + 1)); printf '  FAIL %-46s raw: %s\n' "destructive: heredoc-delivered delete → deny" "$HEREDOC_DELETE_OUT"
fi

# --- Parser-divergence families A3 & B (adversarial verification, #1030) ----------
# These payloads carry a real backslash-newline (line continuation) that bash deletes
# when reading the line — even MID-WORD. The JSON is built with a quoted-heredoc python
# so the exact bytes (backslash 0x5C + newline 0x0A) reach the gate unmangled by shell
# quoting. gate_expect <mode> <expect-deny|allow> <desc> <json-on-stdin>.
gate_expect() {
  local mode="$1" want="$2" desc="$3" json="$4" out got
  out=$(printf '%s' "$json" | STUB_ORG_JSON='{"result":{"instanceUrl":"https://acme.my.salesforce.com"}}' "$GATE" "$mode")
  if printf '%s' "$out" | grep -q '"deny"'; then got=deny; else got=allow; fi
  if [ "$got" = "$want" ]; then
    PASS=$((PASS + 1)); printf '  ok   %-46s → %s\n' "$desc" "$got"
  else
    FAIL=$((FAIL + 1)); printf '  FAIL %-46s → got "%s" want "%s" raw: %s\n' "$desc" "$got" "$want" "$out"
  fi
}

# A3: backslash-newline BETWEEN words ('deploy \<nl>start' -> 'deploy start').
A3_DEPLOY_JSON=$(python3 <<'PY'
import json
print(json.dumps({"tool_input": {"command": "sf project deploy \\\nstart --target-org prod"}}))
PY
)
gate_expect prod-check deny "A3 deploy backslash-newline start → deny" "$A3_DEPLOY_JSON"

# A3: backslash-newline MID-WORD in the delete verb ('del\<nl>ete' -> 'delete').
A3_DELETE_JSON=$(python3 <<'PY'
import json
print(json.dumps({"tool_input": {"command": "sf project del\\\nete --target-org prod"}}))
PY
)
gate_expect destructive deny "A3 del<bslash-nl>ete midword → deny" "$A3_DELETE_JSON"

# B: heredoc body whose deploy is split by a backslash-newline continuation — defeats
# BOTH the delimiter-shielded whole scan and a naive per-line scan unless the
# continuation is joined first.
B_HEREDOC_JSON=$(python3 <<'PY'
import json
print(json.dumps({"tool_input": {"command": "bash <<EOF\nsf project \\\ndeploy start --target-org prod\nEOF"}}))
PY
)
gate_expect prod-check deny "B heredoc + continuation → deny" "$B_HEREDOC_JSON"

echo ""
echo "  $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
