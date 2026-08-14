#!/usr/bin/env bash
#
# LDS GraphQL Schema Fetcher
#
# Fetches the Salesforce LDS GraphQL schema for a connected org by POSTing a
# full introspection query to /services/data/vX/graphql, then renders the
# response as SDL on disk so the skill can introspect it with targeted grep
# calls. (LDS does not expose a /graphql/sdl endpoint — introspection is the
# only path.)
#
# The schema content never enters the chat context — only the file path is
# returned to the user.
#
# Usage:
#   fetch-lds-graphql-schema.sh USERNAME_OR_ALIAS [OUTPUT_PATH] [API_VERSION]
#
# Arguments:
#   $1  usernameOrAlias    SF CLI alias or username for the target org (required)
#   $2  outputPath         File to write SDL to (default: schema.graphql)
#   $3  apiVersion         API version (default: 62.0, matching the legacy
#                          fetch_lds_graphql_schema MCP tool's DEFAULT_API_VERSION)
#
# Exit codes:
#   0  Schema written successfully
#   1  Argument error
#   2  Salesforce CLI missing
#   3  Auth or HTTP failure
#   4  Schema response was empty, contained errors, or had no types

set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: $0 USERNAME_OR_ALIAS [OUTPUT_PATH] [API_VERSION]" >&2
  exit 1
fi

ALIAS="$1"
OUTPUT_PATH="${2:-schema.graphql}"
API_VERSION="${3:-62.0}"

# Skip the fetch when a non-empty schema file is already on disk. Re-fetching
# is a 30-90s introspection round-trip, so a deterministic short-circuit keeps
# repeated invocations idempotent. Set LDS_FETCH_FORCE=1 to override.
if [ -s "$OUTPUT_PATH" ] && [ "${LDS_FETCH_FORCE:-0}" != "1" ]; then
  echo "Schema already present at ${OUTPUT_PATH} — skipping introspection." >&2
  echo "Set LDS_FETCH_FORCE=1 to re-fetch." >&2
  exit 0
fi

# Output-path containment: refuse paths that escape the current working
# directory (e.g. ../../etc/passwd, /tmp/foo, symlinks pointing outside).
# Uses python3's os.path.realpath to resolve `..`, `.`, and symlinks even
# when intermediate directories don't exist yet — the previous bash-`pwd`
# approach was bypassable in two ways:
#   1. when the parent didn't exist, the fallback `$PWD/$(dirname ...)`
#      kept `..` segments uncollapsed (e.g. `nonexistent/../../etc` would
#      string-prefix-match `$PWD` even though it escapes);
#   2. bash's `cd` returns the *logical* path, so a symlink under `$PWD`
#      pointing outside would prefix-match `$PWD` while the real target
#      sat elsewhere on disk.
PWD_REAL=$(python3 -c 'import os; print(os.path.realpath("."))')
OUTPUT_REAL=$(python3 -c 'import os, sys; print(os.path.realpath(sys.argv[1]))' "$OUTPUT_PATH")
case "$OUTPUT_REAL/" in
  "$PWD_REAL"/*) ;;
  *)
    echo "ERROR: refusing to write to '$OUTPUT_PATH' — resolved path '$OUTPUT_REAL' escapes \$PWD ($PWD_REAL)." >&2
    echo "       Pass an output path that resolves under the current working directory." >&2
    exit 1
    ;;
esac

if ! command -v sf &>/dev/null; then
  echo "ERROR: Salesforce CLI (sf) is not installed." >&2
  echo "Install: https://developer.salesforce.com/tools/salesforcecli" >&2
  exit 2
fi

GRAPHQL_PATH="/services/data/v${API_VERSION}/graphql"

echo "Fetching LDS GraphQL schema for org '${ALIAS}' (api v${API_VERSION})..." >&2
echo "Introspection can take 30-90s for large orgs." >&2

INTROSPECTION_QUERY='{"query":"query IntrospectionQuery { __schema { queryType { name } mutationType { name } subscriptionType { name } types { kind name description fields(includeDeprecated: true) { name description args { name description type { kind name ofType { kind name ofType { kind name ofType { kind name ofType { kind name ofType { kind name ofType { kind name } } } } } } } defaultValue } type { kind name ofType { kind name ofType { kind name ofType { kind name ofType { kind name ofType { kind name ofType { kind name } } } } } } } isDeprecated deprecationReason } inputFields { name description type { kind name ofType { kind name ofType { kind name ofType { kind name ofType { kind name ofType { kind name ofType { kind name } } } } } } } defaultValue } interfaces { kind name ofType { kind name } } enumValues(includeDeprecated: true) { name description isDeprecated deprecationReason } possibleTypes { kind name } } } }","variables":{},"operationName":"IntrospectionQuery"}'

INTROSPECTION_FILE=$(mktemp)
trap 'rm -f "$INTROSPECTION_FILE"' EXIT

# Use `sf api request rest`, which authenticates internally from the CLI's
# stored credentials — the access token never enters this script's process
# arguments, environment, or shell history (Prizm S1). Body is passed via a
# temp file (`--body @file`) so the query text also stays out of the argv.
BODY_FILE=$(mktemp)
trap 'rm -f "$INTROSPECTION_FILE" "$BODY_FILE"' EXIT
printf '%s' "$INTROSPECTION_QUERY" >"$BODY_FILE"

if ! sf api request rest "$GRAPHQL_PATH" \
  --target-org "$ALIAS" \
  --method POST \
  --header "Content-Type: application/json" \
  --header "X-Chatter-Entity-Encoding: false" \
  --body "@${BODY_FILE}" \
  >"$INTROSPECTION_FILE" 2>"${INTROSPECTION_FILE}.err"; then
  # `sf api request rest` exits non-zero on auth failure or HTTP >= 400.
  # Don't echo the response/error body — Salesforce error payloads can carry
  # request headers or signed front-door URLs we don't want in shared logs.
  echo "ERROR: Introspection request failed for org '${ALIAS}'." >&2
  echo "       If authentication expired, re-authenticate: sf org login web --alias $ALIAS" >&2
  echo "       Diagnostic output left at: ${INTROSPECTION_FILE}.err" >&2
  echo "       Inspect with: head -c 500 \"${INTROSPECTION_FILE}.err\" (and remove when done)" >&2
  trap 'rm -f "$BODY_FILE"' EXIT  # leave response + err in place for the user
  exit 3
fi
rm -f "${INTROSPECTION_FILE}.err"

if [ ! -s "$INTROSPECTION_FILE" ]; then
  echo "ERROR: Empty introspection response." >&2
  exit 4
fi

OUTPUT_DIR="$(dirname "$OUTPUT_PATH")"
[ -n "$OUTPUT_DIR" ] && mkdir -p "$OUTPUT_DIR"

python3 - "$INTROSPECTION_FILE" "$OUTPUT_PATH" <<'PYEOF'
import json, sys

intro_path, out_path = sys.argv[1], sys.argv[2]

with open(intro_path) as f:
    payload = json.load(f)

errors = payload.get("errors") or []
schema = (payload.get("data") or {}).get("__schema") or {}
types = schema.get("types") or []

if errors:
    print(f"ERROR: introspection returned {len(errors)} errors. First: {errors[0]}", file=sys.stderr)
    sys.exit(4)
if not types:
    print("ERROR: introspection returned zero types.", file=sys.stderr)
    sys.exit(4)


def render_type_ref(t):
    """Recursively render a type reference like NonNull(List(NonNull(Account)))."""
    if t is None:
        return "Unknown"
    kind = t.get("kind")
    if kind == "NON_NULL":
        return render_type_ref(t.get("ofType")) + "!"
    if kind == "LIST":
        return "[" + render_type_ref(t.get("ofType")) + "]"
    return t.get("name") or "Unknown"


def render_args(args):
    if not args:
        return ""
    rendered = []
    for a in args:
        s = f"{a['name']}: {render_type_ref(a.get('type'))}"
        if a.get("defaultValue") is not None:
            s += f" = {a['defaultValue']}"
        rendered.append(s)
    return "(" + ", ".join(rendered) + ")"


def render_fields(fields):
    out = []
    for f in fields or []:
        line = f"  {f['name']}{render_args(f.get('args'))}: {render_type_ref(f.get('type'))}"
        if f.get("isDeprecated"):
            reason = (f.get("deprecationReason") or "").replace('"', '\\"')
            line += f' @deprecated(reason: "{reason}")'
        out.append(line)
    return "\n".join(out)


def render_input_fields(fields):
    out = []
    for f in fields or []:
        line = f"  {f['name']}: {render_type_ref(f.get('type'))}"
        if f.get("defaultValue") is not None:
            line += f" = {f['defaultValue']}"
        out.append(line)
    return "\n".join(out)


# Render in stable order; skip GraphQL builtin __ types (introspection meta-types).
chunks = []
for t in sorted(types, key=lambda x: (x.get("name") or "")):
    name = t.get("name") or ""
    kind = t.get("kind")
    if name.startswith("__"):
        continue
    if kind == "OBJECT":
        interfaces = t.get("interfaces") or []
        impl = ""
        if interfaces:
            impl = " implements " + " & ".join(i["name"] for i in interfaces if i.get("name"))
        body = render_fields(t.get("fields"))
        chunks.append(f"type {name}{impl} {{\n{body}\n}}")
    elif kind == "INTERFACE":
        body = render_fields(t.get("fields"))
        chunks.append(f"interface {name} {{\n{body}\n}}")
    elif kind == "INPUT_OBJECT":
        body = render_input_fields(t.get("inputFields"))
        chunks.append(f"input {name} {{\n{body}\n}}")
    elif kind == "ENUM":
        values = "\n".join(f"  {v['name']}" for v in (t.get("enumValues") or []))
        chunks.append(f"enum {name} {{\n{values}\n}}")
    elif kind == "UNION":
        members = " | ".join(p["name"] for p in (t.get("possibleTypes") or []) if p.get("name"))
        chunks.append(f"union {name} = {members}")
    elif kind == "SCALAR":
        # Skip the standard scalars; emit only org-defined ones.
        if name in ("String", "Int", "Float", "Boolean", "ID"):
            continue
        chunks.append(f"scalar {name}")

with open(out_path, "w") as f:
    f.write("\n\n".join(chunks))
    f.write("\n")

# Sanity: count Record-implementing types so the caller can sanity-check the output.
record_count = sum(1 for t in types if any((i.get("name") == "Record") for i in (t.get("interfaces") or [])))
print(f"types_total={len(types)} types_implementing_Record={record_count}", file=sys.stderr)
PYEOF

LINE_COUNT=$(wc -l <"$OUTPUT_PATH" | tr -d ' ')
echo "Schema written to ${OUTPUT_PATH} (${LINE_COUNT} lines)." >&2
