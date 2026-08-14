#!/bin/bash
# validate-sarif.sh <sarif.json>
#
# Deterministic structural validation of a SARIF 2.1.0 score report emitted
# by experience-lwc-security-validate score mode. Verifies:
#   1. The file parses as JSON.
#   2. Top-level shape: {version:"2.1.0", runs:[{tool.driver.rules:[...], results:[...]}]}
#   3. Every `results[].ruleId` matches the LWS catalog pattern
#      (lws-NNN[a-z]?  |  lws-tpl-NNN  |  lws-meta-NNN).
#   4. Every `results[].ruleId` is also declared in `tool.driver.rules[].id`.
#   5. Every `results[].level` is `error` or `warning`.
#   6. Every `results[]` has a `physicalLocation.artifactLocation.uri`
#      and a `physicalLocation.region.startLine`.
#
# Prints one line per finding on stderr, then exits non-zero if any check
# failed. Exits 0 on success.
#
# Requires `jq` — the workflow already lists jq as a project prerequisite.

set -eu

if [ $# -ne 1 ]; then
  echo "usage: validate-sarif.sh <sarif.json>" >&2
  exit 2
fi

sarif="$1"

if [ ! -f "$sarif" ]; then
  echo "validate-sarif.sh: file not found: $sarif" >&2
  exit 2
fi

if ! command -v jq >/dev/null 2>&1; then
  echo "validate-sarif.sh: jq is required but not installed" >&2
  exit 2
fi

# 1. JSON parse
if ! jq empty "$sarif" >/dev/null 2>&1; then
  echo "sarif-parse=fail  file=$sarif  reason=invalid-json" >&2
  exit 1
fi

status=0

# 2. Top-level shape
version=$(jq -r '.version // ""' "$sarif")
if [ "$version" != "2.1.0" ]; then
  echo "sarif-version=fail  found='$version'  expected='2.1.0'" >&2
  status=1
fi

runs=$(jq -r '.runs | length' "$sarif" 2>/dev/null || echo 0)
if [ "$runs" -eq 0 ]; then
  echo "sarif-runs=fail  reason=empty-or-missing-runs" >&2
  exit 1
fi

# tool.driver.rules and results MUST both be present as arrays — even for an
# empty result set, the workflow requires tool.driver.rules to be declared.
# `type` yields the JSON type or "null" when the path is missing, so this
# rejects absent or non-array values instead of silently treating them as [].
rules_type=$(jq -r '.runs[0].tool.driver.rules | type' "$sarif" 2>/dev/null || echo null)
if [ "$rules_type" != "array" ]; then
  echo "sarif-rules=fail  found='$rules_type'  reason=tool.driver.rules-missing-or-not-array" >&2
  status=1
fi

results_type=$(jq -r '.runs[0].results | type' "$sarif" 2>/dev/null || echo null)
if [ "$results_type" != "array" ]; then
  echo "sarif-results=fail  found='$results_type'  reason=results-missing-or-not-array" >&2
  # No results array to walk — report and exit now.
  exit 1
fi

# Declared rules from tool.driver.rules[].id — one per line.
declared=$(jq -r '.runs[0].tool.driver.rules[]?.id // empty' "$sarif")

# Rule-ID pattern per Step 3 rules of the workflow.
rule_re='^(lws-[0-9]{3}[a-z]?|lws-tpl-[0-9]+|lws-meta-[0-9]+)$'

# 3-6. Walk results[]
result_count=$(jq -r '.runs[0].results | length' "$sarif" 2>/dev/null || echo 0)
if [ "$result_count" -eq 0 ]; then
  # Empty results array is legal (no findings) once results and
  # tool.driver.rules are both confirmed to be arrays above.
  if [ "$status" -eq 0 ]; then
    echo "sarif-validate=ok  results=0"
  fi
  exit "$status"
fi

for i in $(seq 0 $((result_count - 1))); do
  rid=$(jq -r ".runs[0].results[$i].ruleId // empty" "$sarif")
  lvl=$(jq -r ".runs[0].results[$i].level // empty" "$sarif")
  uri=$(jq -r ".runs[0].results[$i].locations[0].physicalLocation.artifactLocation.uri // empty" "$sarif")
  line=$(jq -r ".runs[0].results[$i].locations[0].physicalLocation.region.startLine // empty" "$sarif")

  if ! echo "$rid" | grep -Eq "$rule_re"; then
    echo "result[$i].ruleId=fail  found='$rid'  reason=off-catalog-pattern" >&2
    status=1
  elif ! echo "$declared" | grep -Fxq "$rid"; then
    echo "result[$i].ruleId=fail  found='$rid'  reason=not-declared-in-tool.driver.rules" >&2
    status=1
  fi

  case "$lvl" in
    error|warning) ;;
    *)
      echo "result[$i].level=fail  found='$lvl'  reason=must-be-error-or-warning" >&2
      status=1
      ;;
  esac

  if [ -z "$uri" ]; then
    echo "result[$i].physicalLocation.artifactLocation.uri=fail  reason=missing" >&2
    status=1
  fi

  if [ -z "$line" ]; then
    echo "result[$i].physicalLocation.region.startLine=fail  reason=missing" >&2
    status=1
  fi
done

if [ "$status" -eq 0 ]; then
  echo "sarif-validate=ok  results=$result_count"
fi

exit "$status"
