#!/bin/bash
# Regression test for the Windows batch-shim metacharacter guard in
# sf-deploy-gate (PR #6 review). Sources the gate (which defines its functions
# without dispatching) and asserts:
#   1. _has_cmd_metachars flags every cmd.exe metacharacter and passes clean args
#      (kept consistent with the Python resolver's _CMD_ARG_METACHARACTERS).
#   2. sf_cli, on a `.cmd` shim, REFUSES a metacharacter arg and never invokes
#      COMSPEC; with clean args it does invoke COMSPEC. This exercises the
#      COMSPEC branch offline using a fake `sf.cmd` on PATH and a fake COMSPEC,
#      without a real Windows/cmd.exe.
#
# Run: bash plugins/sfdx-deploy/test/win-shim-guard.test.sh

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
GATE="$ROOT/sf-deploy-gate"
PASS=0
FAIL=0

# shellcheck source=/dev/null
source "$GATE"
set +e  # the gate enables `set -e`-adjacent opts; relax for assertion flow

ok()   { PASS=$((PASS + 1)); printf '  ok   %s\n' "$1"; }
bad()  { FAIL=$((FAIL + 1)); printf '  FAIL %s\n' "$1"; }

echo "sf-deploy-gate — Windows batch-shim metacharacter guard"

# --- 1. _has_cmd_metachars unit checks --------------------------------------
for meta in 'a&b' 'a|b' 'a<b' 'a>b' 'a^b' 'a%b' 'a"b' 'a!b' 'a(b' 'a)b'; do
  if _has_cmd_metachars "$meta"; then ok "flags metacharacter arg: $meta"
  else bad "should flag metacharacter arg: $meta"; fi
done

for clean in 'my-scratch' 'org' 'display' '--target-org' 'a.b_c-123'; do
  if _has_cmd_metachars "$clean"; then bad "should NOT flag clean arg: $clean"
  else ok "passes clean arg: $clean"; fi
done

# metacharacter in a LATER arg is still caught
if _has_cmd_metachars org display --target-org 'a&b'; then ok "flags metachar in a later arg"
else bad "should flag metachar in a later arg"; fi

# --- 2. sf_cli COMSPEC-branch refusal (offline, fake shim + fake COMSPEC) ----
STUB_DIR=$(mktemp -d)
MARKER="$STUB_DIR/comspec-was-called"
# A fake `sf.cmd` on PATH so `command -v sf.cmd` resolves and the .cmd branch runs.
: > "$STUB_DIR/sf.cmd"; chmod +x "$STUB_DIR/sf.cmd"
# A fake COMSPEC that records it was invoked.
cat > "$STUB_DIR/fake-cmd" <<STUB
#!/bin/bash
echo called > "$MARKER"
STUB
chmod +x "$STUB_DIR/fake-cmd"

# Restrict PATH so `command -v sf` (bare) fails and only sf.cmd resolves.
# metacharacter arg → refused (return 1), COMSPEC NOT invoked.
rm -f "$MARKER"
( PATH="$STUB_DIR"; COMSPEC="$STUB_DIR/fake-cmd"; sf_cli org display --target-org 'a&b' ) >/dev/null 2>&1
rc=$?
if [ "$rc" -ne 0 ] && [ ! -f "$MARKER" ]; then ok "metachar arg refused, COMSPEC not invoked"
else bad "metachar arg should be refused without invoking COMSPEC (rc=$rc, marker=$( [ -f "$MARKER" ] && echo yes || echo no ))"; fi

# clean args → COMSPEC IS invoked.
rm -f "$MARKER"
( PATH="$STUB_DIR"; COMSPEC="$STUB_DIR/fake-cmd"; sf_cli org display --target-org clean ) >/dev/null 2>&1
if [ -f "$MARKER" ]; then ok "clean args invoke COMSPEC"
else bad "clean args should invoke COMSPEC"; fi

rm -rf "$STUB_DIR"

echo ""
echo "  $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
