#!/bin/bash
# Project gate for the MCP-health sidecar (WIN-033/WIN-040 review follow-up).
#
# The sf-mcp-proxy plugin loads GLOBALLY, so `--probe` (and the live bridge) can
# be launched from any cwd. writeHealthSidecar must only persist into a Salesforce
# project (cwd has sfdx-project.json); otherwise it litters `.sf/mcp-health` into
# arbitrary directories. This asserts both directions against the committed bundle:
#   1. no sfdx-project.json  -> --probe writes NO .sf/ dir (still prints its JSON line)
#   2. with sfdx-project.json -> --probe DOES write the sidecar
#
# Run: bash plugins/builder/salesforce-development/scripts/test/mcp-health-project-gate.test.sh
set -uo pipefail

REPO="$(cd "$(dirname "$0")/../../../../.." && pwd)"
PROXY="$REPO/plugins/builder/salesforce-development/scripts/sf-mcp-proxy.bundled.js"
NODE_BIN="${NODE_BIN:-node}"
PASS=0
FAIL=0

check() {
  local cond="$1" desc="$2"
  if [ "$cond" = "0" ]; then
    PASS=$((PASS + 1)); printf '  ok   %s\n' "$desc"
  else
    FAIL=$((FAIL + 1)); printf '  FAIL %s\n' "$desc"
  fi
}

echo "mcp-health project gate — $("$NODE_BIN" -v)"

# (1) No project: probe must NOT create .sf/. It has no org/project, so it
# classifies env-not-ready and prints one JSON line — but persists nothing.
EMPTY="$(mktemp -d)"
(
  cd "$EMPTY"
  out="$("$NODE_BIN" "$PROXY" --probe metadata-experts 2>/dev/null)"
  # still prints exactly one JSON line
  printf '%s' "$out" | grep -q '"state"'
)
gate_out=$?
[ ! -d "$EMPTY/.sf" ]; no_sf=$?
check "$gate_out" "probe outside a project still prints its JSON line"
check "$no_sf" "probe outside a project writes NO .sf/ dir"
rm -rf "$EMPTY"

# (2) In a project: probe DOES write the sidecar (env-not-ready is fine — the
# point is the file lands when cwd is a project). No org is set, so state is
# env-not-ready, but the sidecar must be persisted.
PROJ="$(mktemp -d)"
printf '{"packageDirectories":[{"path":"force-app","default":true}],"sourceApiVersion":"62.0"}\n' > "$PROJ/sfdx-project.json"
(
  cd "$PROJ"
  # Unset any inherited default org so this stays a deterministic env-not-ready/
  # offline path (no network), while still exercising the project gate.
  SF_TARGET_ORG="" SFDX_TARGET_ORG="" "$NODE_BIN" "$PROXY" --probe metadata-experts >/dev/null 2>&1
)
[ -f "$PROJ/.sf/mcp-health/metadata-experts.json" ]; wrote=$?
check "$wrote" "probe inside a project writes the sidecar"
rm -rf "$PROJ"

echo
if [ "$FAIL" -eq 0 ]; then
  echo "PASS ($PASS checks)"; exit 0
else
  echo "FAIL ($FAIL failed, $PASS passed)"; exit 1
fi
