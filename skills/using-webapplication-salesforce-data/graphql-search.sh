#!/usr/bin/env bash
# graphql-search.sh — Look up one or more Salesforce entities in schema.graphql.
#
# Run from the SFDX project root (where schema.graphql lives):
#   bash .a4drules/skills/using-salesforce-data/graphql-search.sh Account
#   bash .a4drules/skills/using-salesforce-data/graphql-search.sh Account Contact Opportunity
#
# Pass a custom schema path with -s / --schema:
#   bash .a4drules/skills/using-salesforce-data/graphql-search.sh -s /path/to/schema.graphql Account
#   bash .a4drules/skills/using-salesforce-data/graphql-search.sh --schema ./other/schema.graphql Account Contact
#
# Output sections per entity:
#   1. Type definition   — all fields and relationships
#   2. Filter options    — <Entity>_Filter input (for `where:`)
#   3. Sort options      — <Entity>_OrderBy input (for `orderBy:`)
#   4. Create input      — <Entity>CreateRepresentation (for create mutations)
#   5. Update input      — <Entity>UpdateRepresentation (for update mutations)

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
  echo "  If the file is missing entirely, generate it from the webapp dir:"
  echo "    cd force-app/main/default/webapplications/<app-name> && npm run graphql:schema"
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
  match=$(grep -nE "$pattern" "$SCHEMA" | head -1)

  if [ -z "$match" ]; then
    echo "  (not found: $pattern)"
    return
  fi

  echo "### $label"
  grep -E "$pattern" "$SCHEMA" -A "$max_lines" | \
    awk '/^\}$/{print; exit} {print}' | \
    head -n "$max_lines"
  echo ""
}

# ── Main loop ────────────────────────────────────────────────────────────────

for ENTITY in "$@"; do
  echo ""
  echo "======================================================================"
  echo "  SCHEMA LOOKUP: $ENTITY"
  echo "======================================================================"
  echo ""

  # 1. Type definition — all fields and relationships
  extract_block \
    "Type definition — fields and relationships" \
    "^type ${ENTITY} implements Record" \
    200

  # 2. Filter input — used in `where:` arguments
  extract_block \
    "Filter options — use in where: { ... }" \
    "^input ${ENTITY}_Filter" \
    100

  # 3. OrderBy input — used in `orderBy:` arguments
  extract_block \
    "Sort options — use in orderBy: { ... }" \
    "^input ${ENTITY}_OrderBy" \
    60

  # 4. Create mutation inputs
  extract_block \
    "Create mutation wrapper — ${ENTITY}CreateInput" \
    "^input ${ENTITY}CreateInput" \
    10

  extract_block \
    "Create mutation fields — ${ENTITY}CreateRepresentation" \
    "^input ${ENTITY}CreateRepresentation" \
    100

  # 5. Update mutation inputs
  extract_block \
    "Update mutation wrapper — ${ENTITY}UpdateInput" \
    "^input ${ENTITY}UpdateInput" \
    10

  extract_block \
    "Update mutation fields — ${ENTITY}UpdateRepresentation" \
    "^input ${ENTITY}UpdateRepresentation" \
    100

  echo ""
done
