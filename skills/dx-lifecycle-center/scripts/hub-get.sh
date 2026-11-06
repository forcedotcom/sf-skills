#!/usr/bin/env bash
# Read-only GET against the Lifecycle Center org through the DX Inspector credential (ALMDevOpsCenterHub).
# No workspace alias and no record change: the call runs as the signed-in user, from the source org.
#
# Usage: hub-get.sh <source-org-alias> </services/data/vNN.N/...path?query>
# Prints the response body (JSON) on stdout. Exit codes: 0 HTTP 2xx, 1 usage / not 2xx / call failed.
set -uo pipefail

command -v jq >/dev/null || { echo "jq required" >&2; exit 1; }
SRC="${1:-}"; REQ="${2:-}"
[ -n "$SRC" ] && [ -n "$REQ" ] || { echo "usage: hub-get.sh <source-org-alias> </services/data/vNN.N/...>" >&2; exit 1; }
case "$REQ" in */../*|*/..|*%2e%2e*|*%2E%2E*) echo "path must not contain .." >&2; exit 1 ;; esac
printf '%s' "$REQ" | grep -Eq '^/services/data/v[0-9]+\.[0-9]+/' || { echo "path must start with /services/data/v<version>/" >&2; exit 1; }
# The path goes into an Apex string literal: allow only URL-safe characters (no quotes, backslashes, or whitespace).
printf '%s' "$REQ" | grep -Eq "^[A-Za-z0-9/._~%+=&?,:*()-]+$" || { echo "path has characters that are not allowed (encode spaces as %20 and quotes as %27)" >&2; exit 1; }

apex=$(mktemp "${TMPDIR:-/tmp}/hub-get.XXXXXX") || exit 1
trap 'rm -f "$apex"' EXIT
cat > "$apex" <<APEX
HttpRequest r = new HttpRequest();
r.setEndpoint('callout:ALMDevOpsCenterHub${REQ}');
r.setMethod('GET');
r.setHeader('Accept', 'application/json');
HttpResponse s = new Http().send(r);
System.debug('HUBGET ' + s.getStatusCode() + ' ' + EncodingUtil.base64Encode(Blob.valueOf(s.getBody())));
APEX
# One retry after a short pause covers a refreshing session or a transient hub error.
for attempt in 1 2; do
  out=$(env FORCE_COLOR=0 SF_CLI_DISABLE_AUTOUPDATE=true sf apex run --file "$apex" --target-org "$SRC" --json 2>/dev/null) && \
    line=$(printf '%s' "$out" | jq -r '.result.logs // ""' | grep -o 'HUBGET [0-9]* [A-Za-z0-9+/=]*' | head -1) || line=""
  case "$line" in "HUBGET 5"*|"HUBGET 408"*|"") [ "$attempt" = 1 ] && { sleep 3; continue; } ;; esac
  break
done
[ -n "$line" ] || { echo "no response captured; the callout failed (session expired, Apex not permitted, or the credential is not usable for this user): $(printf '%s' "$out" | jq -r '.result.exceptionMessage // .message // "unknown"' 2>/dev/null | head -c 200)" >&2; exit 1; }
code=$(printf '%s' "$line" | cut -d' ' -f2)
b64=$(printf '%s' "$line" | cut -d' ' -f3)
body=$(printf '%s' "$b64" | base64 -d 2>/dev/null || printf '%s' "$b64" | base64 -D 2>/dev/null)
# A truncated debug log decodes to partial JSON: never return it as a success.
printf '%s' "$body" | jq -e . >/dev/null 2>&1 || { echo "response was cut off or is not JSON; narrow the query (add LIMIT)" >&2; exit 1; }
printf '%s\n' "$body"
case "$code" in 2??) exit 0 ;; *) echo "hub returned HTTP $code" >&2; exit 1 ;; esac
