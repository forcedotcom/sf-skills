#!/bin/bash
# Command self-gate test for bin/lsp-precheck.
#
# The PR added a self-gate so the Node cold-start (the bundled Apex diagnostics
# entrypoint) is paid ONLY on a `sf project deploy start|validate`. Some Claude
# Code builds ignore the plugin.json `if:` matcher and fire every PreToolUse Bash
# hook on every command, so a non-deploy must fail open (continue:true) WITHOUT
# invoking node. The match is whitespace-flexible (so `sf  project  deploy start`
# is not missed) and sub-command-scoped (so a `grep "sf project deploy"` or a
# `deploy report` is not mistaken for a file-pushing deploy).
#
# Run: bash plugins/builder/salesforce-development/scripts/test/lsp-precheck-gate.test.sh
set -uo pipefail

PLUGIN_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
LSP="$PLUGIN_ROOT/bin/lsp-precheck"
PASS=0
FAIL=0

# Stub `node` on PATH: record that it was invoked (the cold-start we want to avoid
# on non-deploys) and print a valid PreToolUse allow so the wrapper output is JSON.
STUB_DIR=$(mktemp -d)
SENTINEL="$STUB_DIR/node-invoked"
trap 'rm -rf "$STUB_DIR"' EXIT
cat > "$STUB_DIR/node" <<STUB
#!/bin/bash
touch "$SENTINEL"
echo '{"continue": true}'
STUB
chmod +x "$STUB_DIR/node"
export PATH="$STUB_DIR:$PATH"

# check <expected-node: yes|no> <description> <json-input-on-stdin>
check() {
  local expect_node="$1" desc="$2" input="$3"
  rm -f "$SENTINEL"
  local out node_called="no"
  out=$(printf '%s' "$input" | "$LSP")
  [ -f "$SENTINEL" ] && node_called="yes"
  local ok=1
  printf '%s' "$out" | grep -q '"continue": true' || ok=0
  [ "$node_called" = "$expect_node" ] || ok=0
  if [ "$ok" = "1" ]; then
    PASS=$((PASS + 1)); printf '  ok   %-48s node=%s\n' "$desc" "$node_called"
  else
    FAIL=$((FAIL + 1)); printf '  FAIL %-48s node=%s (want %s) out=%s\n' "$desc" "$node_called" "$expect_node" "$out"
  fi
}

echo "lsp-precheck — command self-gate (stubbed node)"

# Non-deploy commands: allow, and NEVER pay the node cold-start.
check no  "non-deploy (cd/ls) -> allow, no node"       '{"tool_input":{"command":"cd /tmp && ls"}}'
check no  "empty stdin -> allow, no node"              ''
check no  "grep mentioning deploy -> allow, no node"   '{"tool_input":{"command":"grep -r \"sf project deploy\" ."}}'
# #1030 adversarial review (finding 3): a QUOTED mention of the full `... deploy
# start` phrase used to false-positive (the earlier test above dodged it by omitting
# `start`), paying a needless node cold-start. Quoted spans are now stripped first.
check no  "grep mentioning deploy start -> allow, no node" '{"tool_input":{"command":"grep -r \"sf project deploy start\" ."}}'
check no  "echo mentioning deploy validate -> allow, no node" '{"tool_input":{"command":"echo \"run sf project deploy validate first\""}}'
check no  "deploy report (no files) -> allow, no node" '{"tool_input":{"command":"sf project deploy report"}}'

# Deploy start/validate: run the precheck (node invoked). Whitespace-flexible.
check yes "deploy start -> node invoked"               '{"tool_input":{"command":"sf project deploy start -o dev"}}'
check yes "deploy validate -> node invoked"            '{"tool_input":{"command":"sf project deploy validate -o dev"}}'
check yes "multi-space deploy start -> node invoked"   '{"tool_input":{"command":"sf  project   deploy start -o dev"}}'
# Quote-stripping must not hide a REAL deploy that carries a quoted arg value.
check yes "deploy start w/ quoted arg -> node invoked" '{"tool_input":{"command":"sf project deploy start -o dev --metadata \"ApexClass:Foo\""}}'

echo ""
echo "  $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
