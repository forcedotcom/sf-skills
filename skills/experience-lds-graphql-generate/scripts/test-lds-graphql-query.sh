#!/usr/bin/env bash
#
# LDS GraphQL Query Tester
#
# Executes a GraphQL query or mutation against the LDS endpoint of a connected
# Salesforce org and prints the raw JSON response. Use this to validate a
# generated query end-to-end before handing it to the developer.
#
# Usage:
#   test-lds-graphql-query.sh USERNAME_OR_ALIAS 'GRAPHQL_QUERY' ['VARIABLES_JSON'] [API_VERSION] [OPERATION_NAME]
#
# Arguments:
#   $1  usernameOrAlias    SF CLI alias or username for the target org (required)
#   $2  query              Complete GraphQL query or mutation string (required)
#   $3  variables          Variables JSON object (default: {})
#   $4  apiVersion         API version (default: 66.0, matching the legacy
#                          test_lds_graphql_query MCP tool's DEFAULT_API_VERSION)
#   $5  operationName      Operation to run when the query string defines
#                          multiple named operations (default: omitted)
#
# Exit codes:
#   0  Query executed and returned HTTP 200 (the response itself may still
#      contain a GraphQL `errors` field; the caller categorizes those)
#   1  Argument error
#   2  Salesforce CLI missing
#   3  Auth or HTTP failure

set -euo pipefail

if [ $# -lt 2 ]; then
  echo "Usage: $0 USERNAME_OR_ALIAS 'GRAPHQL_QUERY' ['VARIABLES_JSON'] [API_VERSION] [OPERATION_NAME]" >&2
  exit 1
fi

ALIAS="$1"
QUERY="$2"
VARIABLES="${3-}"
[ -z "$VARIABLES" ] && VARIABLES='{}'
API_VERSION="${4:-66.0}"
OPERATION_NAME="${5-}"

# Mutation guard: this script's name says "tester" — by default we refuse to
# execute write operations (`mutation`) since they have side effects on the
# connected org. Set LDS_ALLOW_MUTATIONS=1 to opt in when intentionally
# testing a mutation.
#
# Detection runs in python3 so we can:
#   1. Strip line comments (`# ...`) before scanning, so a `# mutation note`
#      comment doesn't trip the guard.
#   2. Anchor on operation-start (`^mutation` or `}\smutation`), not bash
#      word-class boundaries — bash's `[[:space:]]|\{|$` boundary class
#      missed `mutation(...)` (variables), `mutation@auth` (directives),
#      and `mutation#comment`, all of which are valid GraphQL.
#   3. Avoid the `query { mutation: get }` field-alias false positive:
#      `mutation` only counts when followed by name / vars / directive /
#      `{`, not by `:` (alias) or `=` (default value).
if [ "${LDS_ALLOW_MUTATIONS:-0}" != "1" ]; then
  if ! printf '%s' "$QUERY" | python3 -c '
import re, sys
src = sys.stdin.read()
# Strip GraphQL line comments (`# ...` to end of line) before scanning.
src = re.sub(r"#[^\n]*", "", src)
# Trim leading whitespace so the `^` anchor below sees the first real
# token. Heredocs, file-read queries, and multiline shell strings often
# carry leading newlines/spaces that would otherwise hide a top-level
# `mutation` from the `^mutation` branch.
src = src.lstrip()
# Match `mutation` only at operation-start: either at the start of the
# stripped source, or after a `}` that closes a previous operation. The
# trailing class accepts every valid follow-up for a mutation operation:
# identifier (name), `(` (variables), `@` (directive), `{` (anonymous
# body), whitespace, or end-of-input. This deliberately excludes `:`
# (field alias, e.g. `query { mutation: get }`) and `=` (default value).
if re.search(r"(?:^|\}\s*)mutation(?:\s|$|[A-Za-z_(@{])", src):
    sys.exit(2)
sys.exit(0)
'; then
    echo "ERROR: refusing to execute a mutation — this script is a read-only tester by default." >&2
    echo "       To intentionally run a mutation, re-invoke with LDS_ALLOW_MUTATIONS=1:" >&2
    echo "         LDS_ALLOW_MUTATIONS=1 $0 ..." >&2
    exit 1
  fi
fi

if ! command -v sf &>/dev/null; then
  echo "ERROR: Salesforce CLI (sf) is not installed." >&2
  exit 2
fi

GRAPHQL_PATH="/services/data/v${API_VERSION}/graphql"

REQUEST_BODY=$(python3 -c '
import sys, json
body = {"query": sys.argv[1], "variables": json.loads(sys.argv[2].strip())}
if sys.argv[3]:
    body["operationName"] = sys.argv[3]
print(json.dumps(body))
' "$QUERY" "$VARIABLES" "$OPERATION_NAME")

RESPONSE_FILE=$(mktemp)
BODY_FILE=$(mktemp)
trap 'rm -f "$RESPONSE_FILE" "$BODY_FILE"' EXIT
printf '%s' "$REQUEST_BODY" >"$BODY_FILE"

# Use `sf api request rest`, which authenticates internally from the CLI's
# stored credentials — the access token never enters this script's process
# arguments, environment, or shell history (Prizm S1). Body is passed via a
# temp file (`--body @file`) so the query text also stays out of the argv.
if ! sf api request rest "$GRAPHQL_PATH" \
  --target-org "$ALIAS" \
  --method POST \
  --header "Content-Type: application/json" \
  --header "X-Chatter-Entity-Encoding: false" \
  --body "@${BODY_FILE}" \
  >"$RESPONSE_FILE" 2>"${RESPONSE_FILE}.err"; then
  # `sf api request rest` exits non-zero on auth failure or HTTP >= 400.
  # Don't echo the response/error body — Salesforce error payloads can carry
  # request headers or signed URLs we don't want surfacing in shared logs.
  echo "ERROR: GraphQL request failed for org '${ALIAS}'." >&2
  echo "       If authentication expired, re-authenticate: sf org login web --alias $ALIAS" >&2
  echo "       Diagnostic output left at: ${RESPONSE_FILE}.err" >&2
  echo "       Inspect with: head -c 500 \"${RESPONSE_FILE}.err\" (and remove when done)" >&2
  trap 'rm -f "$BODY_FILE"' EXIT  # leave response + err in place for the user
  exit 3
fi
rm -f "${RESPONSE_FILE}.err"

cat "$RESPONSE_FILE"
