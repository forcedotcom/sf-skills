#!/bin/bash
# Regression gate for the live sidecar churn-guard key (WIN-033/WIN-040 review).
#
# The live bridge rewrites `.sf/mcp-health/<slug>.json` only when its churn-guard
# key changes, so an inactive server that 404s on every message doesn't rewrite
# an identical sidecar per message. That key MUST be (org, state), not state
# alone: an in-session `sf config set target-org` rebuilds the session against a
# new org, and if the new org has the SAME state as the old one (commonly both
# `ok`) a state-only key would match and skip the write — leaving the sidecar
# stamped with the OLD org (review P2 #1).
#
# The proxy auto-runs main() only when invoked as a script; require()'d it skips
# main() and exports the pure helpers, so we exercise healthWriteKey directly
# against the SHIPPED bundle (no live org / upstream needed).
#
# Run: bash plugins/builder/salesforce-development/scripts/test/mcp-health-churn-guard.test.sh
set -uo pipefail

REPO="$(cd "$(dirname "$0")/../../../../.." && pwd)"
PROXY="$REPO/plugins/builder/salesforce-development/scripts/sf-mcp-proxy.bundled.js"
NODE_BIN="${NODE_BIN:-node}"

echo "mcp-health churn-guard — $("$NODE_BIN" -v)"

# Drive all assertions inside one node process against the required bundle. It
# exits non-zero (with a message) on the first failed assertion.
"$NODE_BIN" -e '
  const assert = require("assert");
  const { classifyUpstream, healthWriteKey } = require(process.argv[1]);
  let n = 0;
  const ok = (cond, desc) => { assert.ok(cond, desc); n++; console.log("  ok   " + desc); };

  // Sanity: helpers are exported (require did not run main()).
  ok(typeof healthWriteKey === "function", "bundle exports healthWriteKey (require did not start the proxy)");
  ok(typeof classifyUpstream === "function", "bundle exports classifyUpstream");

  // Core of review P2 #1: same state, different org -> DIFFERENT key -> a write
  // fires on org switch, so the new org gets a correctly-attributed sidecar.
  ok(healthWriteKey("orgA", "ok") !== healthWriteKey("orgB", "ok"),
     "switching orgs at the same state changes the key (org switch rewrites)");

  // Churn guard still holds within one org: identical (org, state) -> SAME key
  // -> no needless rewrite per message.
  ok(healthWriteKey("orgA", "inactive") === healthWriteKey("orgA", "inactive"),
     "same org + same state keeps the key (no per-message churn)");

  // State transition within one org still rewrites.
  ok(healthWriteKey("orgA", "ok") !== healthWriteKey("orgA", "unreachable"),
     "state change within one org changes the key");

  // A real org switch that ALSO changes state is naturally distinct.
  ok(healthWriteKey("orgA", "ok") !== healthWriteKey("orgB", "inactive"),
     "org+state both changing changes the key");

  console.log("\nPASS (" + n + " checks)");
' "$PROXY"
rc=$?
[ "$rc" -eq 0 ] || { echo "FAIL (assertion failed, exit $rc)"; exit 1; }
