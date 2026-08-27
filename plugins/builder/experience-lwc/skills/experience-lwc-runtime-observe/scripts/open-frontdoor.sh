#!/usr/bin/env bash
# Captures the Salesforce front-door URL into a mode-0600 tempfile without
# printing it to stdout OR stderr, then hands the browser driver the path.
# This keeps the OTP-bearing URL out of agent tool traces (S1: no auth
# tokens in context).
#
# Usage (capture output first so a helper failure aborts the caller —
# `eval "$(...)"` alone swallows the helper's nonzero exit status):
#   frontdoor_env="$(scripts/open-frontdoor.sh <org-alias> <preview-url>)" || exit 1
#   eval "$frontdoor_env"
#   # now $FRONTDOOR_URL_FILE and $PREVIEW_URL are exported for children
#
# The browser automation driver must read the URL from the tempfile,
# navigate to it, then delete the file. Do NOT `cat` this file into your
# agent's stdout.

set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "usage: $0 <org-alias> <preview-url>" >&2
  exit 2
fi

ORG_ALIAS="$1"
PREVIEW_URL="$2"

TMP_URL_FILE="$(mktemp -t sf-frontdoor.XXXXXX)"
chmod 600 "$TMP_URL_FILE"

# Redirect BOTH stdout and stderr from sf and python3 so no URL fragment,
# progress message, or JSON error trace can reach the agent's tool-output
# stream. Only the extracted URL lands in $TMP_URL_FILE.
if ! sf org open --url-only --json --target-org "$ORG_ALIAS" 2>/dev/null \
     | python3 -c 'import json,sys; print(json.load(sys.stdin)["result"]["url"])' 2>/dev/null \
     > "$TMP_URL_FILE"
then
  rm -f "$TMP_URL_FILE"
  echo "error: failed to capture front-door URL for org '$ORG_ALIAS'" >&2
  exit 1
fi

# Emit `export` assignments so the caller must `eval` the output to make
# the variables reach child processes (the browser driver). No token material
# is printed — only the tempfile path and the preview URL.
printf 'export FRONTDOOR_URL_FILE=%q\n' "$TMP_URL_FILE"
printf 'export PREVIEW_URL=%q\n' "$PREVIEW_URL"
