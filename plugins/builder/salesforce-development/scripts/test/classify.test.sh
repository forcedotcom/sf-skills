#!/bin/bash
# Offline classification test for sf-deploy-gate (issue #259).
#
# Feeds `sf org display --json`-shaped fixtures into `sf-deploy-gate classify`
# and asserts the org bucket. No live org required — this is the documented
# regression guard for the trial-org-as-production mis-classification.
#
# Run: bash plugins/sfdx-deploy/test/classify.test.sh

set -uo pipefail

GATE="$(cd "$(dirname "$0")/.." && pwd)/sf-deploy-gate"
PASS=0
FAIL=0

# assert_bucket <expected> <description> <json-on-stdin>
assert_bucket() {
  local expected="$1" desc="$2" json="$3"
  local got
  got=$(printf '%s' "$json" | "$GATE" classify)
  if [ "$got" = "$expected" ]; then
    PASS=$((PASS + 1))
    printf '  ok   %-46s → %s\n' "$desc" "$got"
  else
    FAIL=$((FAIL + 1))
    printf '  FAIL %-46s → got "%s", expected "%s"\n' "$desc" "$got" "$expected"
  fi
}

echo "sf-deploy-gate classify — offline fixtures"

# --- The #259 regression: trial/dev orgs must NOT be production ---------------
# OrgFarm trial: isSandbox/isScratch null, host has no '--' marker. Pre-fix this
# fell through to "production" and over-blocked the deploy.
assert_bucket trial "OrgFarm trial (null flags, orgfarm host)" \
  '{"result":{"isSandbox":null,"isScratch":null,"instanceUrl":"https://orgfarm-abc123.develop.my.salesforce.com"}}'

assert_bucket trial "Developer Edition (.develop.my host)" \
  '{"result":{"isSandbox":false,"isScratch":false,"instanceUrl":"https://mydomain.develop.my.salesforce.com"}}'

assert_bucket trial "pc-rnd internal dev host" \
  '{"result":{"isSandbox":null,"isScratch":null,"instanceUrl":"https://na1.pc-rnd.salesforce.com"}}'

assert_bucket trial "trial via trialExpirationDate field" \
  '{"result":{"isSandbox":false,"isScratch":false,"instanceUrl":"https://example.my.salesforce.com","trialExpirationDate":"2026-09-01T00:00:00.000+0000"}}'

# --- Genuine production must still be gated -----------------------------------
assert_bucket production "Enterprise prod (my.salesforce.com)" \
  '{"result":{"isSandbox":false,"isScratch":false,"instanceUrl":"https://acme.my.salesforce.com"}}'

assert_bucket production "Classic prod (login host)" \
  '{"result":{"isSandbox":false,"isScratch":false,"instanceUrl":"https://na1.salesforce.com"}}'

# --- Existing non-prod buckets preserved --------------------------------------
assert_bucket sandbox "Sandbox via isSandbox flag" \
  '{"result":{"isSandbox":true,"isScratch":false,"instanceUrl":"https://acme--dev.sandbox.my.salesforce.com"}}'

assert_bucket sandbox "Sandbox via -- host marker (flag null)" \
  '{"result":{"isSandbox":null,"isScratch":null,"instanceUrl":"https://acme--uat.my.salesforce.com"}}'

assert_bucket sandbox "Classic sandbox (test.salesforce.com)" \
  '{"result":{"isSandbox":true,"instanceUrl":"https://test.salesforce.com"}}'

assert_bucket scratch "Scratch org" \
  '{"result":{"isSandbox":false,"isScratch":true,"instanceUrl":"https://random-scratch.scratch.my.salesforce.com"}}'

assert_bucket devhub "DevHub (not scratch, not trial)" \
  '{"result":{"isSandbox":false,"isScratch":false,"isDevHub":true,"instanceUrl":"https://acme.my.salesforce.com"}}'

# --- Degenerate input ---------------------------------------------------------
assert_bucket unknown "empty / unparseable result" \
  '{}'

echo ""
echo "  $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
