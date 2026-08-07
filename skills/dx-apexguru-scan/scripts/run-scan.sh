#!/usr/bin/env bash
# Submit a zip to the ApexGuru SFAP Scan API and poll to completion.
#
# Usage:
#   bash run-scan.sh <zip-path> <raw-result-out.json> [--org <alias>] [--fast]
#                    [--max-polls N] [--interval SEC]
#   The endpoint (prod/stage/dev host) is chosen by resolve-token.sh from the
#   token's environment; customers on a prod org always hit api.salesforce.com.
#
# Steps:
#   1. resolve-token.sh → baseUrl + JWT
#   2. POST {baseUrl}/scan  (multipart file upload) → 202 {scanId, status}
#   3. GET  {baseUrl}/scan/{scanId} every ~15s until SUCCEEDED/FAILED
#   4. Write the final raw SUCCEEDED body verbatim to <raw-result-out.json>
#      (report stays base64-encoded here; decode-report.js handles it).
#
# Progress lines go to STDERR so stdout stays a single clean JSON summary:
#   {"scanId":"...","status":"SUCCEEDED","analysisMode":"static|full",
#    "violationCount":N,"filesScanned":N,"rawResult":"<path>"}
# On failure: {"error":"...","status":"...","httpStatus":NNN,"hint":"..."} exit 1.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

ZIP_PATH="${1:-}"
RAW_OUT="${2:-}"
shift 2 2>/dev/null || true

FAST=""
ORG_ALIAS=""
MAX_POLLS=40          # 40 * 15s = 10 min ceiling
INTERVAL=15
while [ $# -gt 0 ]; do
  case "$1" in
    --org) ORG_ALIAS="${2:-}"; shift 2 ;;
    --fast) FAST="true"; shift ;;
    --max-polls) MAX_POLLS="${2:-40}"; shift 2 ;;
    --interval) INTERVAL="${2:-15}"; shift 2 ;;
    *) shift ;;
  esac
done

err() { # msg httpStatus status hint
  jq -cn --arg m "$1" --argjson h "${2:-0}" --arg s "${3:-}" --arg hint "${4:-}" \
    '{error:$m, httpStatus:$h, status:$s, hint:$hint}'
  exit 1
}

[ -n "$ZIP_PATH" ] && [ -f "$ZIP_PATH" ] || err "zip not found: $ZIP_PATH" 0 "" "run build-zip.sh first"
[ -n "$RAW_OUT" ] || err "missing raw output path" 0 "" "usage: run-scan.sh <zip> <raw-out.json>"

# --- 1. token ---
RESOLVE_ARGS=()
[ -n "$ORG_ALIAS" ] && RESOLVE_ARGS+=(--org "$ORG_ALIAS")
CREDS="$(bash "$SCRIPT_DIR/resolve-token.sh" ${RESOLVE_ARGS[@]+"${RESOLVE_ARGS[@]}"})" || {
  echo "$CREDS" >&2; exit 1;
}
BASE_URL="$(echo "$CREDS" | jq -r '.baseUrl')"
# The JWT is a secret: resolve-token.sh returns a 0600 file PATH, never the token
# itself. Read it into memory and delete the file right away so it never lingers.
TOKEN_FILE="$(echo "$CREDS" | jq -r '.tokenFile')"
TOKEN=""
if [ -n "$TOKEN_FILE" ] && [ -f "$TOKEN_FILE" ]; then
  TOKEN="$(cat "$TOKEN_FILE")"
  rm -f "$TOKEN_FILE"
fi
[ -n "$TOKEN" ] || err "could not read resolved token" 0 "" "re-run; if it persists, resolve the token manually via APEXGURU_SFAP_TOKEN"

hint_for_status() { # maps HTTP status → actionable hint (see references/error-handling.md)
  case "$1" in
    401) echo "Token bad or expired. Re-authenticate the Salesforce org (or supply a fresh sfap_api JWT) and retry." ;;
    403) echo "Scan owned by a different org. The token's tnk-claim org must match the scan owner." ;;
    404) echo "Unknown scanId, or the scan was archived (~30-day GC). Re-submit." ;;
    400) echo "Malformed zip, no Apex inside, or over size limit (200MB compressed / 1GB decompressed)." ;;
    *)   echo "See references/error-handling.md." ;;
  esac
}

# Auto-enable fast mode if >10 Apex files (unless explicitly disabled)
if [ -z "$FAST" ]; then
  # grep -c exits non-zero when there are no matches; capture the count without
  # letting that non-zero status trip `set -e`, and default an empty result to 0.
  FILE_COUNT=$(unzip -l "$ZIP_PATH" 2>/dev/null | grep -c '\.cls$' || true)
  FILE_COUNT=${FILE_COUNT:-0}
  if [ "$FILE_COUNT" -gt 10 ]; then
    FAST="true"
    echo "Auto-enabling fast mode (detected $FILE_COUNT Apex files)" >&2
  fi
fi

# --- 2. submit ---
echo "Submitting scan to $BASE_URL/scan ..." >&2
SUBMIT_BODY="$(mktemp)"
FAST_ARG=()
[ -n "$FAST" ] && FAST_ARG=(-F "fastMode=true")

HTTP=$(curl -sS -o "$SUBMIT_BODY" -w '%{http_code}' -X POST "$BASE_URL/scan" \
  -H "Authorization: Bearer $TOKEN" \
  -H "x-apexguru-client: ApexGuru-Skill" \
  -F "file=@${ZIP_PATH};type=application/zip" \
  ${FAST_ARG[@]+"${FAST_ARG[@]}"}) || err "network error submitting scan" 0 "" "check connectivity to the API host"

if [ "$HTTP" != "202" ] && [ "$HTTP" != "200" ]; then
  MSG="$(jq -r '.message // .error // empty' "$SUBMIT_BODY" 2>/dev/null || true)"
  rm -f "$SUBMIT_BODY"
  err "submit failed: ${MSG:-HTTP $HTTP}" "$HTTP" "" "$(hint_for_status "$HTTP")"
fi

SCAN_ID="$(jq -r '.scanId // empty' "$SUBMIT_BODY")"
rm -f "$SUBMIT_BODY"
[ -n "$SCAN_ID" ] || err "no scanId in submit response" "$HTTP" "" "unexpected API response shape"
echo "Accepted. scanId=$SCAN_ID (polling every ${INTERVAL}s, up to $MAX_POLLS times)..." >&2

# --- 3. poll ---
POLL_BODY="$(mktemp)"
STATUS="QUEUED"
i=0
while [ "$i" -lt "$MAX_POLLS" ]; do
  i=$((i + 1))
  sleep "$INTERVAL"
  HTTP=$(curl -sS -o "$POLL_BODY" -w '%{http_code}' -X GET "$BASE_URL/scan/$SCAN_ID" \
    -H "Authorization: Bearer $TOKEN" \
    -H "x-apexguru-client: ApexGuru-Skill") || { echo "poll $i: network hiccup, retrying" >&2; continue; }

  if [ "$HTTP" != "200" ]; then
    MSG="$(jq -r '.message // .error // empty' "$POLL_BODY" 2>/dev/null || true)"
    rm -f "$POLL_BODY"
    err "poll failed: ${MSG:-HTTP $HTTP}" "$HTTP" "$STATUS" "$(hint_for_status "$HTTP")"
  fi

  STATUS="$(jq -r '.status // "UNKNOWN"' "$POLL_BODY")"
  echo "poll $i/$MAX_POLLS: $STATUS" >&2

  case "$STATUS" in
    SUCCEEDED)
      cp "$POLL_BODY" "$RAW_OUT"
      rm -f "$POLL_BODY"
      jq -c '{status, violationCount, filesScanned, rawResult: "'"$RAW_OUT"'"}' "$RAW_OUT"
      exit 0
      ;;
    FAILED)
      MSG="$(jq -r '.message // "scan reported FAILED"' "$POLL_BODY")"
      rm -f "$POLL_BODY"
      err "$MSG" "$HTTP" "FAILED" "Inspect the message; re-submit after addressing it."
      ;;
    QUEUED|RUNNING) : ;; # keep polling
    *) echo "poll $i: unexpected status '$STATUS', continuing" >&2 ;;
  esac
done

rm -f "$POLL_BODY"
err "scan did not finish within $((MAX_POLLS * INTERVAL))s (last status: $STATUS)" 0 "$STATUS" \
  "Large projects can take longer — re-run with --max-polls higher, or use --fast."
