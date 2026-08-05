#!/bin/bash
# Regression test for the python3 preflight guards added to scripts/sf-context,
# scripts/sf-deploy-gate, and bin/lsp-precheck. All three shell out to python3
# for their real logic (org detection/classification, JSON parsing); without a
# guard, a missing python3 surfaces as a raw "command not found" instead of a
# diagnosable message, and (for sf-deploy-gate/lsp-precheck, which back
# PreToolUse/PostToolUse hooks) can break the hook's expected JSON-on-stdout
# contract entirely.
#
# Simulates "python3 missing" by running each script with PATH restricted to a
# stub directory containing only the couple of external commands each script
# needs BEFORE it reaches the python3 check (dirname, cat) — deliberately
# omitting python3 so `command -v python3` fails for real, not just at runtime.
#
# Run: bash plugins/builder/salesforce-development/scripts/test/python3-guard.test.sh
set -uo pipefail

PLUGIN_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SF_CONTEXT="$PLUGIN_ROOT/scripts/sf-context"
SF_DEPLOY_GATE="$PLUGIN_ROOT/scripts/sf-deploy-gate"
LSP_PRECHECK="$PLUGIN_ROOT/bin/lsp-precheck"
PASS=0
FAIL=0

ok()  { PASS=$((PASS + 1)); printf '  ok   %s\n' "$1"; }
bad() { FAIL=$((FAIL + 1)); printf '  FAIL %s\n' "$1"; }

# PATH with no python3 on it at all — only the bare commands each wrapper
# needs before its guard runs (dirname, cat). Real symlinks, not stubs, so the
# scripts behave exactly as they normally would up to the python3 check.
STUB_DIR=$(mktemp -d)
trap 'rm -rf "$STUB_DIR"' EXIT
ln -s "$(command -v dirname)" "$STUB_DIR/dirname"
ln -s "$(command -v cat)" "$STUB_DIR/cat"

echo "python3 preflight guards — sf-context, sf-deploy-gate, lsp-precheck"

# --- 1. sf-context: fails closed with a clear message ------------------------
OUT=$(PATH="$STUB_DIR" "$SF_CONTEXT" detect 2>&1)
RC=$?
if [ "$RC" -ne 0 ] && printf '%s' "$OUT" | grep -qi "python3 not found"; then
  ok "sf-context: missing python3 -> non-zero exit with clear stderr message"
else
  bad "sf-context: missing python3 -> expected non-zero exit + message (rc=$RC out=$OUT)"
fi

# --- 2. sf-deploy-gate classify: fails OPEN as 'unknown' ----------------------
OUT=$(printf '' | PATH="$STUB_DIR" "$SF_DEPLOY_GATE" classify 2>&1)
RC=$?
if [ "$RC" -eq 0 ] && printf '%s' "$OUT" | grep -q "unknown" && printf '%s' "$OUT" | grep -qi "python3 not found"; then
  ok "sf-deploy-gate classify: missing python3 -> 'unknown', exit 0, stderr note"
else
  bad "sf-deploy-gate classify: missing python3 -> expected 'unknown'/exit 0/stderr note (rc=$RC out=$OUT)"
fi

# --- 3. sf-deploy-gate prod-check: fails OPEN with a valid allow decision -----
OUT=$(PATH="$STUB_DIR" "$SF_DEPLOY_GATE" prod-check < /dev/null 2>&1)
RC=$?
if [ "$RC" -eq 0 ] && printf '%s' "$OUT" | grep -q '"continue": true'; then
  ok "sf-deploy-gate prod-check: missing python3 -> allows (continue:true)"
else
  bad "sf-deploy-gate prod-check: missing python3 -> expected continue:true (rc=$RC out=$OUT)"
fi

# --- 4. lsp-precheck: fails OPEN, never attempts the node cold-start ---------
OUT=$(printf '%s' '{"tool_input":{"command":"sf project deploy start"}}' | PATH="$STUB_DIR" "$LSP_PRECHECK" 2>&1)
RC=$?
if [ "$RC" -eq 0 ] && printf '%s' "$OUT" | grep -q '"continue": true'; then
  ok "lsp-precheck: missing python3 -> allows (continue:true), no node cold-start"
else
  bad "lsp-precheck: missing python3 -> expected continue:true (rc=$RC out=$OUT)"
fi

# --- 5. Normal behavior is unaffected when python3 IS present ----------------
OUT=$("$SF_CONTEXT" __python3_guard_test_unknown_cmd__ 2>&1)
RC=$?
if [ "$RC" -ne 0 ] && printf '%s' "$OUT" | grep -qi "Unknown command" && ! printf '%s' "$OUT" | grep -qi "python3 not found"; then
  ok "sf-context: python3 present -> guard does not fire, real dispatch runs"
else
  bad "sf-context: python3 present -> guard should not fire (rc=$RC out=$OUT)"
fi

OUT=$(printf '{}' | "$SF_DEPLOY_GATE" classify 2>&1)
RC=$?
if [ "$RC" -eq 0 ] && printf '%s' "$OUT" | grep -q "unknown" && ! printf '%s' "$OUT" | grep -qi "python3 not found"; then
  ok "sf-deploy-gate classify: python3 present -> guard does not fire"
else
  bad "sf-deploy-gate classify: python3 present -> guard should not fire (rc=$RC out=$OUT)"
fi

OUT=$(printf '%s' '{"tool_input":{"command":"ls"}}' | "$LSP_PRECHECK" 2>&1)
RC=$?
if [ "$RC" -eq 0 ] && printf '%s' "$OUT" | grep -q '"continue": true' && ! printf '%s' "$OUT" | grep -qi "python3 not found"; then
  ok "lsp-precheck: python3 present -> guard does not fire"
else
  bad "lsp-precheck: python3 present -> guard should not fire (rc=$RC out=$OUT)"
fi

echo ""
echo "  $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
