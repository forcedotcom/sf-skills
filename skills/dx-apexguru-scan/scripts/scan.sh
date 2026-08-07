#!/usr/bin/env bash
# One-shot ApexGuru performance scan: package → submit+poll → decode+present.
#
# This wrapper runs all three steps of the workflow in a single command so the
# scan cannot be left half-finished (a bare run-scan.sh already prints a
# violation count, which can read as "done" and tempt an early stop before the
# report is decoded). The FINAL stdout of this script is the ready-to-present
# markdown report from decode-report.js --present — print that to the user
# verbatim.
#
# Usage:
#   bash scan.sh <project-root> [--out <report.md>]
#                [--org <alias>] [--fast] [--raw <raw-out.json>]
#
#   <project-root>  folder that contains Apex somewhere beneath it (defaults to
#                   CWD if omitted or given as "."). build-zip.sh collects every
#                   .cls/.trigger under it, any layout.
#   --out FILE      also write the presented markdown to FILE (e.g. report.md).
#   --org ALIAS     forwarded to run-scan.sh (which sf org to derive the JWT from).
#   --fast          forwarded to run-scan.sh (skip LLM-heavy fix generation).
#   --raw FILE      keep the raw SUCCEEDED JSON at FILE (default: a temp file).
#
# The endpoint (prod/stage/dev) is chosen from the token's env by resolve-token.sh;
# customers on a prod org always hit api.salesforce.com.
#
# Progress for each step streams to STDERR; only the final presented markdown
# goes to STDOUT. On any step failure, the failing step's JSON error/hint is
# surfaced to stderr and the script exits non-zero.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PROJECT_ROOT=""
OUT_FILE=""
RAW_OUT=""
ORG_ALIAS=""
FAST=""

# First non-flag arg is the project root.
while [ $# -gt 0 ]; do
  case "$1" in
    --out) OUT_FILE="${2:-}"; shift 2 ;;
    --raw) RAW_OUT="${2:-}"; shift 2 ;;
    --org) ORG_ALIAS="${2:-}"; shift 2 ;;
    --fast) FAST="--fast"; shift ;;
    *) [ -z "$PROJECT_ROOT" ] && PROJECT_ROOT="$1"; shift ;;
  esac
done

[ -n "$PROJECT_ROOT" ] || PROJECT_ROOT="$(pwd)"
[ "$PROJECT_ROOT" = "." ] && PROJECT_ROOT="$(pwd)"

TS="$(date +%Y%m%d-%H%M%S)"
WORK_DIR="$(mktemp -d)"
ZIP_PATH="$WORK_DIR/apexguru-${TS}.zip"
[ -n "$RAW_OUT" ] || RAW_OUT="$WORK_DIR/apexguru-raw-${TS}.json"

cleanup() { [ -n "${WORK_DIR:-}" ] && rm -rf "$WORK_DIR" 2>/dev/null || true; }
trap cleanup EXIT

# --- Step 1: package the project's Apex into a zip ---
echo "[scan] Step 1/3: packaging $PROJECT_ROOT ..." >&2
ZIP_JSON="$(bash "$SCRIPT_DIR/build-zip.sh" "$PROJECT_ROOT" "$ZIP_PATH")" || {
  echo "$ZIP_JSON" >&2
  echo "[scan] packaging failed — see the error/hint above." >&2
  exit 1
}
echo "[scan] packaged: $(echo "$ZIP_JSON" | jq -r '.humanSize // "?"') → $(echo "$ZIP_JSON" | jq -r '.zip')" >&2

# --- Step 2: submit + poll to completion ---
echo "[scan] Step 2/3: submitting and polling the scan ..." >&2
RUN_ARGS=("$ZIP_PATH" "$RAW_OUT")
[ -n "$ORG_ALIAS" ] && RUN_ARGS+=(--org "$ORG_ALIAS")
[ -n "$FAST" ] && RUN_ARGS+=("$FAST")
RUN_JSON="$(bash "$SCRIPT_DIR/run-scan.sh" "${RUN_ARGS[@]}")" || {
  echo "$RUN_JSON" >&2
  echo "[scan] scan failed — see the error/hint above." >&2
  exit 1
}
echo "[scan] scan complete: $(echo "$RUN_JSON" | jq -r '.violationCount // "?"') violations" >&2

# --- Step 3: decode + present (this is the deliverable) ---
echo "[scan] Step 3/3: decoding and presenting the report ..." >&2
PRESENTED="$(node "$SCRIPT_DIR/decode-report.js" "$RAW_OUT" --present)" || {
  echo "[scan] decoding failed against $RAW_OUT" >&2
  exit 1
}

# Optionally persist the presented markdown (e.g. so it survives temp cleanup).
if [ -n "$OUT_FILE" ]; then
  printf '%s\n' "$PRESENTED" > "$OUT_FILE"
  echo "[scan] report also written to $OUT_FILE" >&2
fi

# FINAL stdout: the ready-to-present markdown. Print this to the user verbatim.
printf '%s\n' "$PRESENTED"
