#!/usr/bin/env bash
set -euo pipefail

ORG="${1:-}"

if ! command -v sf >/dev/null 2>&1; then
  echo "Salesforce CLI (sf) is not installed or not on PATH." >&2
  exit 1
fi

if ! sf data360 man >/dev/null 2>&1; then
  echo "The community 'sf data360' runtime is not available." >&2
  echo "Run bash ~/.claude/skills/orchestrating-datacloud/scripts/bootstrap-plugin.sh first." >&2
  exit 1
fi

echo "✓ sf data360 runtime detected"

if [[ -n "${ORG}" ]]; then
  if sf org display -o "${ORG}" >/dev/null 2>&1; then
    echo "✓ org alias '${ORG}' is authenticated"
  else
    echo "Org alias '${ORG}' is not authenticated." >&2
    exit 1
  fi

  if sf data360 doctor -o "${ORG}" >/dev/null 2>&1; then
    echo "✓ sf data360 doctor completed for '${ORG}'"
  else
    echo "! sf data360 doctor did not complete cleanly for '${ORG}'. Falling back to read-only smoke checks." >&2

    smoke_passed=0
    while IFS='|' read -r label command; do
      [[ -z "${label}" ]] && continue
      if bash -lc "${command}" >/dev/null 2>&1; then
        echo "✓ ${label} smoke check passed for '${ORG}'"
        smoke_passed=1
      fi
    done <<EOF
connectors|sf data360 connection connector-list -o "${ORG}"
dmos|sf data360 dmo list --all -o "${ORG}"
segments|sf data360 segment list -o "${ORG}"
data-action-targets|sf data360 data-action-target list -o "${ORG}"
EOF

    if [[ "${smoke_passed}" -ne 1 ]]; then
      echo "No fallback Data Cloud smoke checks succeeded for '${ORG}'. Check org access and Data Cloud provisioning." >&2
      exit 1
    fi

    echo "! Doctor remains advisory for partially provisioned orgs; at least one read-only Data Cloud command succeeded." >&2
  fi
fi

echo "Verification complete."
if [[ -n "${ORG}" ]]; then
  echo "Next: node ~/.claude/skills/orchestrating-datacloud/scripts/diagnose-org.mjs -o '${ORG}' --json"
fi
