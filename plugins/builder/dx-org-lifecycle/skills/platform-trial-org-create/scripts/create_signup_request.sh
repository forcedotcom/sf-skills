#!/usr/bin/env bash
#
# create_signup_request.sh — Create a Salesforce trial org by inserting a
# SignupRequest sObject against an authenticated host org.
#
# This wraps the deterministic parts of the create step: enforcing the
# "exactly one of --template-id / --edition" rule, assembling and quoting the
# `sf data create record --values` payload, running the insert, and returning
# the assigned SignupRequest id (0SR...). Prose interpretation is not needed —
# the field-selection and serialization rules live here.
#
# Auth is handled by the `sf` CLI (the access token never surfaces here).
#
# Usage:
#   create_signup_request.sh --target-org <alias-or-username> \
#     --last-name <name> --email <addr> --username <email-format> \
#     --company <name> --country <ISO> \
#     ( --template-id 0TT... | --edition Developer ) \
#     [--first-name <name>]
#
# Options:
#   --target-org, -o <org>  REQUIRED. Host org alias or username to create in.
#   --last-name <name>      REQUIRED. Admin user last name.
#   --email <addr>          REQUIRED. SignupEmail — a real inbox.
#   --username <email>      REQUIRED. Admin username (email-format, globally unique).
#   --company <name>        REQUIRED. Company / org name (spaces allowed).
#   --country <ISO>         REQUIRED. ISO country code (e.g. US, GB, IN).
#   --template-id 0TT...    Trialforce template id. Mutually exclusive with --edition.
#   --edition <Edition>     Generic edition (Developer, Enterprise, ...). Mutually
#                           exclusive with --template-id.
#   --first-name <name>     Optional. Admin user first name.
#   --output-dir <dir>      On a rejected create, write the failure outcome to
#                           <dir>/signup-request-result.json (so the run still
#                           has an artifact when no org is created).
#   --json                  Emit the raw `sf` create envelope as-is (default:
#                           print the 0SR id on success, error text on failure).
#   --help, -h              Show this help.
#
# Output:
#   On success (default): the SignupRequest id (0SR...) on stdout, exit 0.
#   On success (--json):  the raw `sf data create record --json` envelope.
#   On failure:           the raw CLI error (name/code + message) on stderr, and
#                         (with --output-dir) a create-rejected artifact JSON.
#
# Exit codes:
#   0  create succeeded
#   1  create rejected by the API (validation / entitlement / access error)
#   2  bad usage or missing dependency (sf or jq)

set -uo pipefail

die() { echo "Error: $*" >&2; exit 2; }

command -v sf >/dev/null 2>&1 || die "Salesforce CLI ('sf') not found on PATH."
command -v jq >/dev/null 2>&1 || die "'jq' not found on PATH."

TARGET_ORG=""
LAST_NAME=""
EMAIL=""
USERNAME=""
COMPANY=""
COUNTRY=""
TEMPLATE_ID=""
EDITION=""
FIRST_NAME=""
OUTPUT_DIR=""
OUTPUT="id"

usage() { sed -n '2,/^set -uo/p' "$0" | sed '/^set -uo/d; s/^# \{0,1\}//; s/^#//'; }

while [ $# -gt 0 ]; do
  case "$1" in
    --target-org|-o) TARGET_ORG="${2:-}"; shift 2 ;;
    --last-name)     LAST_NAME="${2:-}"; shift 2 ;;
    --email)         EMAIL="${2:-}"; shift 2 ;;
    --username)      USERNAME="${2:-}"; shift 2 ;;
    --company)       COMPANY="${2:-}"; shift 2 ;;
    --country)       COUNTRY="${2:-}"; shift 2 ;;
    --template-id)   TEMPLATE_ID="${2:-}"; shift 2 ;;
    --edition)       EDITION="${2:-}"; shift 2 ;;
    --first-name)    FIRST_NAME="${2:-}"; shift 2 ;;
    --output-dir)    OUTPUT_DIR="${2:-}"; shift 2 ;;
    --json)          OUTPUT="json"; shift ;;
    --help|-h)       usage; exit 0 ;;
    *)               die "Unknown argument: $1" ;;
  esac
done

# --- required-field validation ------------------------------------------
[ -n "$TARGET_ORG" ] || die "--target-org is required (host org alias or username)."
[ -n "$LAST_NAME" ]  || die "--last-name is required."
[ -n "$EMAIL" ]      || die "--email is required."
[ -n "$USERNAME" ]   || die "--username is required."
[ -n "$COMPANY" ]    || die "--company is required."
[ -n "$COUNTRY" ]    || die "--country is required (ISO code, e.g. US)."

# --- exactly-one-of rule (TemplateId XOR Edition) -----------------------
if [ -n "$TEMPLATE_ID" ] && [ -n "$EDITION" ]; then
  die "Send exactly one of --template-id or --edition, not both (would fail with redundantTemplateId)."
fi
if [ -z "$TEMPLATE_ID" ] && [ -z "$EDITION" ]; then
  die "Send exactly one of --template-id or --edition (neither given would fail with missingEdition)."
fi

# --- reject values 'sf --values' cannot represent -----------------------
# A value containing BOTH a single and a double quote cannot be expressed in the
# space-separated --values string, whose parser honors only one quote style per
# token. Check here in the main scope: a guard inside sf_quote would run inside
# $(...) command substitution, where `exit` kills only the subshell and (with no
# `set -e`) the script would carry on and issue a malformed create.
for v in "$LAST_NAME" "$EMAIL" "$USERNAME" "$COMPANY" "$COUNTRY" \
         "$FIRST_NAME" "$TEMPLATE_ID" "$EDITION"; do
  case "$v" in
    *\'*\"* | *\"*\'*) die "Value contains both single and double quotes, which 'sf --values' cannot represent: $v" ;;
  esac
done

# --- assemble the --values payload --------------------------------------
# `sf data create record --values` takes ONE space-separated string of
# Field=Value pairs and re-splits it on whitespace, honoring only quotes that
# appear *inside* that string (see plugin-data's stringToDictionary parser).
# So any value containing whitespace (e.g. Company="Acme Corporation") must be
# quoted within the payload, or sf mis-parses it into separate tokens. Quote
# each value: single-quote by default; switch to double quotes when the value
# itself contains a single quote (e.g. a last name like O'Brien). Values with
# both quote types are already rejected above.
sf_quote() {
  case "$1" in
    *\'*) printf '"%s"' "$1" ;;
    *)    printf "'%s'" "$1" ;;
  esac
}

PAIRS=(
  "LastName=$(sf_quote "$LAST_NAME")"
  "SignupEmail=$(sf_quote "$EMAIL")"
  "Username=$(sf_quote "$USERNAME")"
  "Company=$(sf_quote "$COMPANY")"
  "Country=$(sf_quote "$COUNTRY")"
)
[ -n "$FIRST_NAME" ]  && PAIRS+=("FirstName=$(sf_quote "$FIRST_NAME")")
[ -n "$TEMPLATE_ID" ] && PAIRS+=("TemplateId=$(sf_quote "$TEMPLATE_ID")")
[ -n "$EDITION" ]     && PAIRS+=("Edition=$(sf_quote "$EDITION")")

# Join the quoted pairs into the single space-separated string sf expects.
VALUES_STR="${PAIRS[*]}"

# --- run the insert ------------------------------------------------------
RESP="$(sf data create record --target-org "$TARGET_ORG" --sobject SignupRequest \
  --values "$VALUES_STR" --json 2>/dev/null)"

STATUS="$(printf '%s' "$RESP" | jq -r '.status // 1' 2>/dev/null)"

if [ "$STATUS" != "0" ]; then
  # Surface the raw CLI error verbatim (name/code + message) — do not diagnose.
  NAME="$(printf '%s' "$RESP" | jq -r '.name // .code // "ERROR"')"
  MSG="$(printf '%s' "$RESP" | jq -r '.message // "unknown error"')"
  printf '%s: %s\n' "$NAME" "$MSG" >&2
  # No org is created on a rejected create, so get_signup_request.sh never runs.
  # Still leave the run an artifact when --output-dir is given: capture the
  # create-rejected outcome and the raw error verbatim (no diagnosis).
  if [ -n "$OUTPUT_DIR" ]; then
    mkdir -p "$OUTPUT_DIR"
    jq -n --arg name "$NAME" --arg msg "$MSG" \
      '{outcome: "create-rejected", error: {name: $name, message: $msg}, CreatedOrgId: null, Status: null}' \
      > "$OUTPUT_DIR/signup-request-result.json"
  fi
  exit 1
fi

if [ "$OUTPUT" = "json" ]; then
  printf '%s\n' "$RESP"
else
  printf '%s\n' "$(printf '%s' "$RESP" | jq -r '.result.id')"
fi
