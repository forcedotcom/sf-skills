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
# If the environment cannot be detected the script exits with an error rather than
# defaulting to prod; set APEXGURU_ENV=prod|stage|dev to choose explicitly.
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

  # Host part of an https URL (lowercased, no port/userinfo); empty if not https.
  url_host() {
    case "$1" in
      https://*) printf '%s' "$1" | sed -e 's#^https://##' -e 's#[/?\#].*$##' -e 's#^.*@##' -e 's#:[0-9]*$##' | tr 'A-Z' 'a-z' ;;
      *) printf '' ;;
    esac
  }
  INSTANCE_HOST="$(url_host "$INSTANCE_URL")"
  FRONTDOOR_HOST="$(url_host "$FRONTDOOR_URL")"

  # Only proceed when both URLs are https and the frontdoor is on the org's own host.
  if [ -n "$INSTANCE_HOST" ] && [ -n "$FRONTDOOR_HOST" ] && [ "$INSTANCE_HOST" = "$FRONTDOOR_HOST" ]; then
    COOKIE_JAR="$(mktemp "${TMPDIR:-/tmp}/apexguru-sid.XXXXXX")"
    HDR_FILE="$(mktemp "${TMPDIR:-/tmp}/apexguru-sidhdr.XXXXXX")"
    chmod 600 "$COOKIE_JAR" "$HDR_FILE"
    trap 'rm -f "$COOKIE_JAR" "$HDR_FILE"' EXIT
    # Follow the frontdoor (bounded, https-only redirects) to capture the session
    # cookie; discard the HTML body. The URL carries a one-time pad, so it is passed
    # via a curl config on stdin (-K -) rather than on the command line.
    printf 'url = "%s"\n' "$FRONTDOOR_URL" | curl -sS -K - -c "$COOKIE_JAR" \
      -L --max-redirs 5 --proto =https --proto-redir =https \
      --connect-timeout 15 --max-time 60 -o /dev/null 2>/dev/null || true

    # Cookie jar columns: domain, subdomains, path, secure, expiry, name, value.
    # HttpOnly cookies have their domain prefixed with "#HttpOnly_".
    SID="$(awk -F'\t' 'tolower($6)=="sid"{print $7}' "$COOKIE_JAR" 2>/dev/null | head -1)"
    SID_DOMAIN="$(awk -F'\t' 'tolower($6)=="sid"{d=$1; sub(/^#HttpOnly_/,"",d); sub(/^\./,"",d); print tolower(d)}' "$COOKIE_JAR" 2>/dev/null | head -1)"
    # Accept the sid only if it was issued for the org's own host (or a parent domain of it).
    if [ -n "$SID" ]; then
      case "$INSTANCE_HOST" in
        "$SID_DOMAIN"|*".$SID_DOMAIN") : ;;
        *) echo "Unexpected sid cookie domain '$SID_DOMAIN' for $INSTANCE_HOST; ignoring it." >&2; SID="" ;;
      esac
      [ -n "$SID_DOMAIN" ] || SID=""
    fi

    if [ -n "$SID" ]; then
      # Exchange the session id for the SFAP JWT. Response: {"jwt":"...","message":"..."}.
      # The sid goes in a 0600 header file (-H @file), never on the command line.
      printf 'Authorization: Bearer %s' "$SID" > "$HDR_FILE"
      AUTH_JSON="$(curl -sS --connect-timeout 15 --max-time 60 "${INSTANCE_URL%/}/ide/auth" -H @"$HDR_FILE" 2>/dev/null || true)"
      CANDIDATE="$(printf '%s' "$AUTH_JSON" | jq -r '.jwt // empty' 2>/dev/null || true)"
      if [ -n "$CANDIDATE" ] && [ "$CANDIDATE" != "null" ]; then
        TOKEN="$CANDIDATE"
        SOURCE="sf-cli:/ide/auth${ORG_ALIAS:+ (org=$ORG_ALIAS)}"
      fi
    fi
    rm -f "$COOKIE_JAR" "$HDR_FILE"; trap - EXIT
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

# Route to the host matching the token's env. APEXGURU_ENV (prod|stage|dev) overrides
# detection. An undetectable env is an error: we never silently send an org token to prod.
TOKEN_ENV="${APEXGURU_ENV:-$DETECTED_ENV}"
case "$TOKEN_ENV" in
  prod)  API_HOST="$PROD_HOST" ;;
  dev)   API_HOST="$DEV_HOST" ;;
  stage) API_HOST="$STAGE_HOST" ;;
  *)
    jq -cn --arg env "$TOKEN_ENV" \
      '{error:("could not determine token environment (got: \($env | if . == "" then "none" else . end))"), hint:"Set APEXGURU_ENV=prod|stage|dev explicitly."}'
    exit 1
    ;;
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
# environment, matching the chosen baseUrl.
jq -cn --arg baseUrl "$BASE_URL" --arg tokenFile "$TOKEN_FILE" --arg source "$SOURCE" --arg env "$TOKEN_ENV" \
  '{baseUrl:$baseUrl, tokenFile:$tokenFile, source:$source, env:$env}'
