#!/usr/bin/env bash
# Resolve an SFAP access token (JWT, sfap_api scope) for SFAP AI Gateway calls.
# Adapted from the dx-apexguru-scan skill's resolve-token.sh.
#
# Usage: bash resolve-token.sh [--org <alias>] [--core-tenant-id <id>]
#
# --core-tenant-id sets coreTenantId as given, for an org whose id the rules below do not build.
#
# Output (stdout, single line JSON):
#   {"baseUrl":"https://test.api.salesforce.com/ai/gpt/v1","tokenFile":"/tmp/...","source":"...","env":"...","coreTenantId":"..."}
# The JWT itself is written to a 0600 temp file (path in tokenFile); never printed to stdout.
# On failure: {"error":"...","hint":"..."} and exit 1.
set -euo pipefail

ORG_ALIAS=""
CORE_TENANT_OVERRIDE=""
while [ $# -gt 0 ]; do
  case "$1" in
    --org) ORG_ALIAS="${2:-}"; shift 2 ;;
    --core-tenant-id) CORE_TENANT_OVERRIDE="${2:-}"; shift 2 ;;
    *) shift ;;
  esac
done

TOKEN=""
SOURCE=""

# Derive JWT from sf CLI org via <instanceUrl>/ide/auth
if command -v sf >/dev/null 2>&1 && command -v jq >/dev/null 2>&1 && command -v curl >/dev/null 2>&1; then
  ORG_ARGS=()
  [ -n "$ORG_ALIAS" ] && ORG_ARGS=(--target-org "$ORG_ALIAS")

  INSTANCE_URL=""
  ORG_ID=""
  if ORG_JSON="$(sf org display ${ORG_ARGS[@]+"${ORG_ARGS[@]}"} --json 2>/dev/null)"; then
    INSTANCE_URL="$(printf '%s' "$ORG_JSON" | jq -r '.result.instanceUrl // empty')"
    ORG_ID="$(printf '%s' "$ORG_JSON" | jq -r '.result.id // empty')"
  fi

  FRONTDOOR_URL=""
  if OPEN_JSON="$(sf org open ${ORG_ARGS[@]+"${ORG_ARGS[@]}"} --url-only --json 2>/dev/null)"; then
    FRONTDOOR_URL="$(printf '%s' "$OPEN_JSON" | jq -r '.result.url // empty')"
  fi

  if [ -n "$INSTANCE_URL" ] && [ -n "$FRONTDOOR_URL" ]; then
    COOKIE_JAR="$(mktemp "${TMPDIR:-/tmp}/offexp-sid.XXXXXX")"
    chmod 600 "$COOKIE_JAR"
    trap 'rm -f "$COOKIE_JAR"' EXIT

    curl -sS -c "$COOKIE_JAR" -L -o /dev/null "$FRONTDOOR_URL" 2>/dev/null || true
    SID="$(awk -F'\t' 'tolower($6)=="sid"{print $7}' "$COOKIE_JAR" 2>/dev/null | head -1)"

    if [ -n "$SID" ]; then
      AUTH_JSON="$(printf 'Authorization: Bearer %s' "$SID" | curl -sS "${INSTANCE_URL%/}/ide/auth" -H @- 2>/dev/null || true)"
      CANDIDATE="$(printf '%s' "$AUTH_JSON" | jq -r '.jwt // empty' 2>/dev/null || true)"
      if [ -n "$CANDIDATE" ] && [ "$CANDIDATE" != "null" ]; then
        TOKEN="$CANDIDATE"
        SOURCE="sf-cli:/ide/auth${ORG_ALIAS:+ (org=$ORG_ALIAS)}"
      fi
    fi
    rm -f "$COOKIE_JAR"; trap - EXIT
  fi
fi

if [ -z "$TOKEN" ]; then
  printf '{"error":"no SFAP token found","hint":"Authenticate to an org first: sf org login web -a <alias>"}\n'
  exit 1
fi

# Detect environment from the JWT's issuer or sfap_rh claim
PAYLOAD=$(printf '%s' "$TOKEN" | cut -d. -f2 | tr '_-' '/+')
MOD=$((${#PAYLOAD} % 4))
if [ $MOD -eq 2 ]; then PAYLOAD="${PAYLOAD}=="; elif [ $MOD -eq 3 ]; then PAYLOAD="${PAYLOAD}="; fi
DECODED=$(printf '%s' "$PAYLOAD" | base64 -d 2>/dev/null || printf '%s' "$PAYLOAD" | base64 -D 2>/dev/null)

ISS=$(printf '%s' "$DECODED" | jq -r '.iss // empty' 2>/dev/null || true)
SFAP_RH=$(printf '%s' "$DECODED" | jq -r '.sfap_rh // empty' 2>/dev/null || true)

# Determine environment and base URL
DETECTED_ENV=""
if echo "$ISS$SFAP_RH" | grep -qi 'test1\|test\b'; then
  DETECTED_ENV="test"
elif echo "$ISS$SFAP_RH" | grep -qi 'stage'; then
  DETECTED_ENV="stage"
elif echo "$ISS$SFAP_RH" | grep -qi 'dev\b'; then
  DETECTED_ENV="dev"
elif [ -n "$ISS$SFAP_RH" ]; then
  DETECTED_ENV="prod"
fi

if [ -z "$DETECTED_ENV" ]; then
  printf '{"error":"cannot detect SFAP environment from JWT claims (issuer and sfap_rh are both empty)","hint":"set SFAP_BASE_URL or check the org authentication"}\n'
  exit 1
fi

case "$DETECTED_ENV" in
  test)  API_HOST="test.api.salesforce.com" ;;
  stage) API_HOST="stage.api.salesforce.com" ;;
  dev)   API_HOST="dev.api.salesforce.com" ;;
  *)     API_HOST="api.salesforce.com" ;;
esac
BASE_URL="https://${API_HOST}/ai/gpt/v1"

# Build core tenant ID from the org's instance name
INSTANCE_NAME=""
if [ -n "$ISS" ]; then
  # Extract instance hint from issuer URL (e.g. test1 from orgfarm-xxx.test1.my.pc-rnd.salesforce.com;
  # test2 and the other test instances the same way)
  INSTANCE_NAME=$(echo "$ISS" | grep -oE '(test[0-9]+|na[0-9]+|cs[0-9]+|eu[0-9]+)' | head -1 || true)
fi
CORE_TENANT_ID=""
if [ -n "$CORE_TENANT_OVERRIDE" ]; then
  CORE_TENANT_ID="$CORE_TENANT_OVERRIDE"
elif [ -n "$ORG_ID" ] && [ -n "$INSTANCE_NAME" ]; then
  CORE_TENANT_ID="core/falcon${INSTANCE_NAME}-core4/${ORG_ID}"
elif [ -n "$ORG_ID" ] && [ "$DETECTED_ENV" = "prod" ]; then
  # A production org whose issuer names no instance (a Hyperforce org or sandbox, e.g. instance USA874S)
  CORE_TENANT_ID="core/prod/${ORG_ID}"
fi

# Write JWT to secure temp file
TOKEN_FILE="$(mktemp "${TMPDIR:-/tmp}/offexp-jwt.XXXXXX")"
chmod 600 "$TOKEN_FILE"
printf '%s' "$TOKEN" > "$TOKEN_FILE"

jq -cn --arg baseUrl "$BASE_URL" --arg tokenFile "$TOKEN_FILE" --arg source "$SOURCE" \
  --arg env "$DETECTED_ENV" --arg coreTenantId "$CORE_TENANT_ID" \
  '{baseUrl:$baseUrl, tokenFile:$tokenFile, source:$source, env:$env, coreTenantId:$coreTenantId}'
