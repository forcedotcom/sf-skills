#!/usr/bin/env bash
# Query a DevOps Center async request and determine the true outcome. Runs a
# single check (--once) or polls until the request reaches a terminal state.
# Read-only: issues only `sf devops request status` queries; never mutates.
#
# IMPORTANT — two-level semantics:
#   .result.status is the async REQUEST status (uppercase, operation-prefixed:
#   PROMOTE_SUCCESS / PROMOTE_IN_PROGRESS / DEPLOY_FAILED / ...). It reports
#   whether the request finished processing, NOT whether the underlying deploy
#   succeeded. A request can show a *SUCCESS* status while the deployment itself
#   FAILED — that failure lives in .result.errorDetails (an escaped JSON string
#   with errorType/errorMessage). errorDetails is the outcome oracle: non-null
#   => the operation failed.
#
# Usage:
#   poll-status.sh --once <request-token> <target-org-alias>
#   poll-status.sh <request-token> <target-org-alias> [interval-seconds] [timeout-seconds]
#
# Exit codes:
#   0  request reached a terminal state AND the operation succeeded (errorDetails null)
#   1  usage error / missing dependency / status query failed
#   2  request reached a terminal state BUT the operation failed (errorDetails set,
#      or status suffix *FAILED*/*ERROR*/*CANCELED*/*ABORTED*)
#   3  timeout reached before a terminal state (poll mode only)
#   4  request is still processing (--once mode only — not yet terminal)
set -euo pipefail

ONCE=0
if [ "${1:-}" = "--once" ]; then
  ONCE=1
  shift
fi

REQUEST_TOKEN="${1:-}"
TARGET_ORG="${2:-}"
INTERVAL="${3:-10}"
TIMEOUT="${4:-1800}"

usage() {
  echo "Usage: poll-status.sh [--once] <request-token> <target-org-alias> [interval-seconds] [timeout-seconds]" >&2
  exit 1
}

[ -z "$REQUEST_TOKEN" ] && usage
[ -z "$TARGET_ORG" ] && usage

# Reject non-numeric interval/timeout up front so the bounded loop stays bounded.
# (Under `set -e`, an arithmetic test against a non-numeric value errors but the
# loop could otherwise keep running — validate before we ever enter it.)
is_positive_int() { case "$1" in ''|*[!0-9]*) return 1;; *) [ "$1" -gt 0 ];; esac; }
if ! is_positive_int "$INTERVAL"; then
  echo "interval-seconds must be a positive integer, got: $INTERVAL" >&2; usage
fi
if ! is_positive_int "$TIMEOUT"; then
  echo "timeout-seconds must be a positive integer, got: $TIMEOUT" >&2; usage
fi

command -v sf >/dev/null 2>&1 || { echo "sf CLI not found on PATH" >&2; exit 1; }
command -v jq >/dev/null 2>&1 || { echo "jq not found on PATH" >&2; exit 1; }

# Enforce a 5-second minimum polling interval (DOCe API rate limits).
if [ "$INTERVAL" -lt 5 ]; then INTERVAL=5; fi

# Query once and classify the outcome. Echoes a human-readable line and returns:
#   0 succeeded, 2 failed (operation), 3 still processing, 1 query error.
# `.result.status` is operation-PREFIXED — match on the suffix with globs so any
# prefix is handled. Order matters: check failure suffixes before success so a
# *_FAILED never falls through to the success arm.
classify() {
  local status_json req_status err_details message detail
  if ! status_json=$(sf devops request status --request-token "$REQUEST_TOKEN" --target-org "$TARGET_ORG" --json 2>/dev/null); then
    echo "Status query failed for request $REQUEST_TOKEN (org $TARGET_ORG)" >&2
    return 1
  fi
  req_status=$(printf '%s' "$status_json" | jq -r '.result.status // "UNKNOWN"')
  # errorDetails is an escaped JSON string (or null). "null"/"" => no error.
  err_details=$(printf '%s' "$status_json" | jq -r '.result.errorDetails // ""')
  message=$(printf '%s' "$status_json" | jq -r '.result.message // ""')

  case "$req_status" in
    *FAILED*|*FAILURE*|*ERROR*|*CANCELED*|*CANCELLED*|*ABORTED*)
      detail=$(printf '%s' "$err_details" | jq -r '"\(.errorType): \(.errorMessage)"' 2>/dev/null || printf '%s' "$err_details")
      echo "Request $REQUEST_TOKEN failed (request status: $req_status). $message ${detail:+— $detail}" >&2
      return 2
      ;;
    *SUCCESS*|*SUCCEEDED*|*COMPLETED*)
      # Terminal request state — but a "success" request can still carry a failed
      # operation. errorDetails is the outcome oracle: non-null => failure.
      if [ -n "$err_details" ]; then
        detail=$(printf '%s' "$err_details" | jq -r '"\(.errorType): \(.errorMessage)"' 2>/dev/null || printf '%s' "$err_details")
        echo "Request $REQUEST_TOKEN failed (request status: $req_status, but errorDetails set). $message ${detail:+— $detail}" >&2
        return 2
      fi
      echo "Request $REQUEST_TOKEN completed successfully (request status: $req_status). $message"
      return 0
      ;;
    *)
      # Non-terminal (*_IN_PROGRESS / *_PENDING / *_QUEUED / *_STARTED /
      # *_RUNNING / *_NEW / UNKNOWN) — still processing.
      echo "Request $REQUEST_TOKEN status: $req_status (still processing). $message"
      return 3
      ;;
  esac
}

# --once: single query, no waiting. Map "still processing" (3) to exit 4.
if [ "$ONCE" -eq 1 ]; then
  set +e; classify; rc=$?; set -e
  [ "$rc" -eq 3 ] && exit 4
  exit "$rc"
fi

# Track WALL-CLOCK time, not accumulated sleep — otherwise the per-poll CLI
# latency inside classify() is invisible to the timeout and the real deadline
# drifts past TIMEOUT by the summed query time. $SECONDS is bash's seconds-since-
# shell-start counter; snapshot it now and measure elapsed against that.
start=$SECONDS
while :; do
  set +e; classify; rc=$?; set -e
  case "$rc" in
    0|1|2) exit "$rc" ;;   # terminal (succeeded/failed) or query error — done
  esac
  # rc == 3: still processing. Honor timeout-seconds as a true wall-clock cap.
  elapsed=$((SECONDS - start))
  if [ "$elapsed" -ge "$TIMEOUT" ]; then
    echo "Timeout after ${elapsed}s — request $REQUEST_TOKEN still processing" >&2
    exit 3
  fi
  remaining=$((TIMEOUT - elapsed))
  wait_for=$INTERVAL
  if [ "$remaining" -lt "$wait_for" ]; then wait_for=$remaining; fi
  echo "Waiting ${wait_for}s (elapsed ${elapsed}s, timeout ${TIMEOUT}s)..."
  sleep "$wait_for"
done
