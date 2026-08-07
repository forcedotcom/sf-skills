#!/usr/bin/env bash
# Resolve the SFAP access token (JWT, sfap_api scope) and API base URL for the
# ApexGuru SFAP Scan API, then print them as a single JSON object to stdout.
#
# Usage: bash resolve-token.sh [--org <alias>]
#
# The base URL is derived from the token's own environment (prod/stage/dev),
# detected from its tnk claim by validate-token.js: prod → api.salesforce.com,
# stage → stage.api.salesforce.com, dev → dev.api.salesforce.com. So a prod org
# hits prod and an internal dev/scratch org hits dev, with no extra config.
#
# Output (stdout, single line JSON): {"baseUrl":"...","tokenFile":"...","source":"..."}
# The SFAP JWT is a secret, so it is NEVER printed to stdout. Instead it is
# written to a caller-owned 0600 temp file and the PATH is returned in
# `tokenFile`; the caller (run-scan.sh) reads it into memory and deletes the
# file immediately. Only non-secret fields (baseUrl/source/env) go to stdout.
# On failure: prints a JSON object {"error":"...","hint":"..."} and exits 1.
#
# Token resolution order (first hit wins):
#   1. APEXGURU_SFAP_TOKEN         env var — the raw JWT (most portable; CI/headless)
#   2. APEXGURU_SFAP_TOKEN_FILE    env var — path to a file holding the JWT
#   3. sf CLI + <instanceUrl>/ide/auth — derive the JWT from an authenticated org
#      (per Tharun's interim guide). Org alias from --org or APEXGURU_SF_ORG;
#      omit to use the CLI's default/target org.
#
# NOTE: the /ide/auth derivation (3) is Tharun's INTERIM approach; the Code
# Analyzer team may provide a cleaner path later. This script is the ONLY place
# that changes when it does — everything downstream consumes the token opaquely.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Per-environment ApexGuru API hosts. The one used is chosen from the token's
# detected env below, so the endpoint always matches the org the token came from.
PROD_HOST="api.salesforce.com"
STAGE_HOST="stage.api.salesforce.com"
DEV_HOST="dev.api.salesforce.com"
API_PATH="platform/scale/v1-beta.1/apex-guru"

ORG_ALIAS="${APEXGURU_SF_ORG:-}"
while [ $# -gt 0 ]; do
  case "$1" in
    --org) ORG_ALIAS="${2:-}"; shift 2 ;;
    *) shift ;;
  esac
done

TOKEN=""
SOURCE=""

# Priority 1: explicit env var (most portable; works headless / in CI).
if [ -n "${APEXGURU_SFAP_TOKEN:-}" ]; then
  TOKEN="${APEXGURU_SFAP_TOKEN}"
  SOURCE="env:APEXGURU_SFAP_TOKEN"
fi

# Priority 2: a token file the user points us at (avoids leaking into shell history).
if [ -z "$TOKEN" ] && [ -n "${APEXGURU_SFAP_TOKEN_FILE:-}" ] && [ -f "${APEXGURU_SFAP_TOKEN_FILE}" ]; then
  TOKEN="$(tr -d '[:space:]' < "${APEXGURU_SFAP_TOKEN_FILE}")"
  SOURCE="file:${APEXGURU_SFAP_TOKEN_FILE}"
fi

# Priority 3: derive the JWT from an authenticated sf CLI org via <instanceUrl>/ide/auth
# (Tharun's interim guide). Needs `sf` + `jq`. Errors here are non-fatal — we fall
# through to the "no token" message below so the env-var paths still work standalone.
#
# IMPORTANT: `sf org display --json` REDACTS `accessToken` (CLI >= ~2.14x), so it
# CANNOT be used as the session token — sending it yields a bare 401 "No session
# ID sent". The live, unredacted session id is obtained instead from a frontdoor
# URL (`sf org open --url-only`): visiting it sets a `sid` cookie, which /ide/auth
# accepts as a Bearer token and exchanges for the SFAP JWT. The sid is a secret —
# it lives only in a 0600 temp cookie jar that we delete on exit; never echoed.
if [ -z "$TOKEN" ] && command -v sf >/dev/null 2>&1 && command -v jq >/dev/null 2>&1 && command -v curl >/dev/null 2>&1; then
  ORG_ARGS=()
  [ -n "$ORG_ALIAS" ] && ORG_ARGS=(--target-org "$ORG_ALIAS")

  # instanceUrl is NOT redacted; grab it (accessToken from this call is useless — redacted).
  # ${ORG_ARGS[@]+...} guards empty-array expansion under `set -u` on bash 3.2 (macOS).
  INSTANCE_URL=""
  if ORG_JSON="$(sf org display ${ORG_ARGS[@]+"${ORG_ARGS[@]}"} --json 2>/dev/null)"; then
    INSTANCE_URL="$(printf '%s' "$ORG_JSON" | jq -r '.result.instanceUrl // empty')"
  fi

  # frontdoor URL carries a one-time pad; following it mints the real `sid` cookie.
  FRONTDOOR_URL=""
  if OPEN_JSON="$(sf org open ${ORG_ARGS[@]+"${ORG_ARGS[@]}"} --url-only --json 2>/dev/null)"; then
    FRONTDOOR_URL="$(printf '%s' "$OPEN_JSON" | jq -r '.result.url // empty')"
  fi

  if [ -n "$INSTANCE_URL" ] && [ -n "$FRONTDOOR_URL" ]; then
    COOKIE_JAR="$(mktemp "${TMPDIR:-/tmp}/apexguru-sid.XXXXXX")"
    chmod 600 "$COOKIE_JAR"
    trap 'rm -f "$COOKIE_JAR"' EXIT
    # Follow the frontdoor to capture the session cookie; discard the HTML body.
    curl -sS -c "$COOKIE_JAR" -L -o /dev/null "$FRONTDOOR_URL" 2>/dev/null || true
    SID="$(awk -F'\t' 'tolower($6)=="sid"{print $7}' "$COOKIE_JAR" 2>/dev/null | head -1)"

    if [ -n "$SID" ]; then
      # Exchange the session id for the SFAP JWT. Response: {"jwt":"...","message":"..."}.
      AUTH_JSON="$(curl -sS "${INSTANCE_URL%/}/ide/auth" -H "Authorization: Bearer $SID" 2>/dev/null || true)"
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
  printf '{"error":"no SFAP token found","hint":"Sign in to an authorized Salesforce org to run an ApexGuru scan and compare your code against production performance data."}\n'
  exit 1
fi

# Local sanity check (no network): catch the two things that cause almost every
# 401 — missing sfap_api scope, expired — and detect the token's environment
# BEFORE we zip/upload. The token is piped on stdin (never argv) so it stays out
# of the process list. Only provable failures block; anything unreadable is a
# non-fatal warning.
DETECTED_ENV=""
if command -v node >/dev/null 2>&1; then
  if ! VALIDATION="$(printf '%s' "$TOKEN" | node "$SCRIPT_DIR/validate-token.js")"; then
    # validate-token.js already printed {"ok":false,"error","hint"} to stdout.
    echo "$VALIDATION"
    exit 1
  fi
  DETECTED_ENV="$(printf '%s' "$VALIDATION" | jq -r '.detectedEnv // empty' 2>/dev/null || true)"
fi

# Route to the host matching the token's env; default to prod when undetectable.
case "$DETECTED_ENV" in
  dev)   API_HOST="$DEV_HOST" ;;
  stage) API_HOST="$STAGE_HOST" ;;
  *)     API_HOST="$PROD_HOST" ;;
esac
BASE_URL="https://${API_HOST}/${API_PATH}"

# The token is a secret: write it to a 0600 temp file and return only the PATH,
# never the token itself. This keeps it out of stdout (which is visible to the
# agent when this script is invoked directly, per the skill's script index).
# The caller reads the file and deletes it. `printf` avoids a trailing newline.
TOKEN_FILE="$(mktemp "${TMPDIR:-/tmp}/apexguru-jwt.XXXXXX")"
chmod 600 "$TOKEN_FILE"
printf '%s' "$TOKEN" > "$TOKEN_FILE"

# Emit only non-secret fields. jq handles escaping. `env` reflects the token's
# detected environment (prod when undetectable), matching the chosen baseUrl.
ENV_LABEL="${DETECTED_ENV:-prod}"
jq -cn --arg baseUrl "$BASE_URL" --arg tokenFile "$TOKEN_FILE" --arg source "$SOURCE" --arg env "$ENV_LABEL" \
  '{baseUrl:$baseUrl, tokenFile:$tokenFile, source:$source, env:$env}'
