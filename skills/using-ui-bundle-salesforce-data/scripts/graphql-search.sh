#!/usr/bin/env bash
set -euo pipefail  # exit on error (-e), undefined vars (-u), and propagate pipeline failures (-o pipefail)
# graphql-search.sh — Look up one or more Salesforce entities in schema.graphql.
#
# Run from the SFDX project root (where schema.graphql lives):
#   bash scripts/graphql-search.sh Account
#   bash scripts/graphql-search.sh Account Contact Opportunity
#
# Pass a custom schema path with -s / --schema:
#   bash scripts/graphql-search.sh -s /path/to/schema.graphql Account
#   bash scripts/graphql-search.sh --schema ./other/schema.graphql Account Contact
#
# Output sections per entity:
#   1. Type definition          — all fields and relationships
#   2. Filter options           — <Entity>_Filter input (for `where:`)
#   3. Sort options             — <Entity>_OrderBy input (for `orderBy:`)
#   4. Create mutation wrapper  — <Entity>CreateInput
#   5. Create mutation fields   — <Entity>CreateRepresentation (for create mutations)
#   6. Update mutation wrapper  — <Entity>UpdateInput
#   7. Update mutation fields   — <Entity>UpdateRepresentation (for update mutations)

SCHEMA="./schema.graphql"

# ── Argument parsing ─────────────────────────────────────────────────────────

while [[ $# -gt 0 ]]; do
  case "$1" in
    -s|--schema)
      if [[ -z "${2-}" || "$2" == -* ]]; then
        echo "ERROR: --schema requires a file path argument"
        exit 1
      fi
      SCHEMA="$2"
      shift 2
      ;;
    --)
      shift
      break
      ;;
    -*)
      echo "ERROR: Unknown option: $1"
      echo "Usage: bash $0 [-s <schema-path>] <EntityName> [EntityName2 ...]"
      exit 1
      ;;
    *)
      break
      ;;
  esac
done

if [ $# -eq 0 ]; then
  echo "Usage: bash $0 [-s <schema-path>] <EntityName> [EntityName2 ...]"
  echo "Example: bash $0 Account"
  echo "Example: bash $0 Account Contact Opportunity"
  echo "Example: bash $0 --schema /path/to/schema.graphql Account"
  exit 1
fi

if [ ! -f "$SCHEMA" ]; then
  echo "ERROR: schema.graphql not found at $SCHEMA"
  echo "  Make sure you are running from the SFDX project root, or pass the path explicitly:"
  echo "    bash $0 --schema <path/to/schema.graphql> <EntityName>"
  echo "  If the file is missing entirely, generate it from the UI bundle dir:"
  echo "    cd force-app/main/default/uiBundles/<app-name> && npm run graphql:schema"
  exit 1
fi

if [ ! -r "$SCHEMA" ]; then
  echo "ERROR: schema.graphql is not readable at $SCHEMA"
  echo "  Check file permissions: ls -la $SCHEMA"
  exit 1
fi

if [ ! -s "$SCHEMA" ]; then
  echo "ERROR: schema.graphql is empty at $SCHEMA"
  echo "  Regenerate it from the UI bundle dir:"
  echo "    cd force-app/main/default/uiBundles/<app-name> && npm run graphql:schema"
  exit 1
fi

# ── Helper: extract lines from a grep match through the closing brace ────────
# Prints up to MAX_LINES lines after (and including) the first match of PATTERN.
# Uses a generous line count — blocks are always closed by a "}" line.

extract_block() {
  local label="$1"
  local pattern="$2"
  local max_lines="$3"

  local match
  local grep_exit=0
  match=$(grep -nE "$pattern" "$SCHEMA" | head -1) || grep_exit=$?

  if [ "$grep_exit" -eq 2 ]; then
    echo "  ERROR: grep failed on pattern: $pattern" >&2
    return 1
  fi

  if [ -z "$match" ]; then
    echo "  (not found: $pattern)"
    return 3
  fi

  echo "### $label"
  grep -E "$pattern" "$SCHEMA" -A "$max_lines" | \
    awk '/^\}$/{print; exit} {print}' | \
    head -n "$max_lines" || true
  echo ""
}

# ── Main loop ────────────────────────────────────────────────────────────────

for ENTITY in "$@"; do
  # Validate entity name: must be a valid PascalCase identifier (letters, digits, underscores)
  if [[ ! "$ENTITY" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]]; then
    echo "ERROR: Invalid entity name: '$ENTITY'"
    echo "  Entity names must start with a letter or underscore, followed by letters, digits, or underscores."
    echo "  Examples: Account, My_Custom_Object__c"
    continue
  fi

  echo ""
  echo "======================================================================"
  echo "  SCHEMA LOOKUP: $ENTITY"
  echo "======================================================================"
  echo ""

  found=0

  # Helper: call extract_block, track matches, surface errors
  try_extract() {
    local rc=0
    extract_block "$@" || rc=$?
    if [ "$rc" -eq 0 ]; then
      found=$((found + 1))
    elif [ "$rc" -eq 1 ]; then
      echo "  Aborting lookup for '$ENTITY' due to grep error" >&2
    fi
    # rc=3 is not-found — continue silently (already printed by extract_block)
  }

  # 1. Type definition — all fields and relationships
  try_extract \
    "Type definition — fields and relationships" \
    "^type ${ENTITY} implements Record" \
    200

  # 2. Filter input — used in `where:` arguments
  try_extract \
    "Filter options — use in where: { ... }" \
    "^input ${ENTITY}_Filter" \
    100

  # 3. OrderBy input — used in `orderBy:` arguments
  try_extract \
    "Sort options — use in orderBy: { ... }" \
    "^input ${ENTITY}_OrderBy" \
    60

  # 4. Create mutation wrapper
  try_extract \
    "Create mutation wrapper — ${ENTITY}CreateInput" \
    "^input ${ENTITY}CreateInput" \
    10

  # 5. Create mutation fields
  try_extract \
    "Create mutation fields — ${ENTITY}CreateRepresentation" \
    "^input ${ENTITY}CreateRepresentation" \
    100

  # 6. Update mutation wrapper
  try_extract \
    "Update mutation wrapper — ${ENTITY}UpdateInput" \
    "^input ${ENTITY}UpdateInput" \
    10

  # 7. Update mutation fields
  try_extract \
    "Update mutation fields — ${ENTITY}UpdateRepresentation" \
    "^input ${ENTITY}UpdateRepresentation" \
    100

  if [ "$found" -eq 0 ]; then
    echo "WARNING: No schema entries found for '$ENTITY'."
    echo "  - Names are PascalCase (e.g., 'Account' not 'account')"
    echo "  - Custom objects may need deployment first"
  fi

  echo ""
done
