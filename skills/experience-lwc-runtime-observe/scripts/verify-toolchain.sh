#!/usr/bin/env bash
# Verifies the toolchain required for Lightning Preview: `sf` CLI on PATH,
# `@salesforce/plugin-lightning-dev` installed, and the specified target
# org alias authenticated and Connected. Exits nonzero with an actionable
# message on failure so the agent can surface a single, deterministic
# error instead of parsing prose from three separate commands.
#
# Usage:
#   <skill_dir>/scripts/verify-toolchain.sh <orgAlias>

set -euo pipefail

fail() {
  echo "verify-toolchain: $*" >&2
  exit 1
}

if [ "$#" -lt 1 ] || [ -z "${1:-}" ]; then
  fail "usage: $0 <orgAlias>"
fi
alias="$1"

command -v sf >/dev/null 2>&1 \
  || fail "Salesforce CLI (\`sf\`) not found on PATH. Install via https://developer.salesforce.com/tools/salesforcecli then re-run."

sf version >/dev/null 2>&1 \
  || fail "\`sf version\` failed. Reinstall the Salesforce CLI."

if ! sf plugins --core 2>/dev/null | grep -Eq '(^|[[:space:]])@salesforce/plugin-lightning-dev([[:space:]]|$)'; then
  if ! sf plugins 2>/dev/null | grep -Eq '(^|[[:space:]])@salesforce/plugin-lightning-dev([[:space:]]|$)'; then
    fail "Plugin \`@salesforce/plugin-lightning-dev\` is not installed. Install via: sf plugins install @salesforce/plugin-lightning-dev"
  fi
fi

if ! sf org display --target-org "$alias" --json 2>/dev/null \
     | python3 -c 'import json,sys
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(1)
if d.get("status") != 0:
    sys.exit(1)
r = d.get("result", {}) or {}
sys.exit(0 if r.get("connectedStatus") == "Connected" else 1)'; then
  fail "Target org alias \`$alias\` is not authenticated or not Connected. Run \`sf org login web --alias $alias\` and re-run."
fi

echo "verify-toolchain: OK ($alias)"
