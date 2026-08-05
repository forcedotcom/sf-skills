#!/bin/bash
# scan-lwc-components.sh — Scan local SFDX project for LWC components matching a query.
#
# Usage: scripts/scan-lwc-components.sh <query> [packageDirectory]
#
# Arguments:
#   query             — User intent keywords (e.g., "expense tracker")
#   packageDirectory  — SFDX package directory path (default: read from sfdx-project.json)
#
# Output: Ranked JSON array of matches with confidence scores.
#   [{"name": "expenseTracker", "score": 75, "confidence": "high"}]
#
# Confidence tiers:
#   high   (≥70%): auto-select, confirm with user
#   medium (40-69%): present ranked list for user selection
#   low    (<40%): skip, proceed to Tier 2

set -euo pipefail

QUERY="${1:-}"
PKG_DIR="${2:-}"

if [ -z "$QUERY" ]; then
  echo "Usage: $0 <query> [packageDirectory]" >&2
  exit 1
fi

# Resolve package directory from sfdx-project.json if not provided
if [ -z "$PKG_DIR" ]; then
  if [ -f "sfdx-project.json" ]; then
    PKG_DIR=$(python3 -c "
import json, sys
with open('sfdx-project.json') as f:
    data = json.load(f)
    dirs = data.get('packageDirectories', [])
    if dirs:
        print(dirs[0].get('path', 'force-app'))
    else:
        print('force-app')
" 2>/dev/null || echo "force-app")
  else
    PKG_DIR="force-app"
  fi
fi

# Check if package directory exists
if [ ! -d "$PKG_DIR" ]; then
  echo "[]"
  exit 0
fi

# Tokenize query: lowercase, split on spaces
IFS=' ' read -ra QUERY_TOKENS <<< "$(echo "$QUERY" | tr '[:upper:]' '[:lower:]')"

# Find all LWC component directories
RESULTS="["
FIRST=true

while IFS= read -r dir; do
  COMP_NAME=$(basename "$dir")

  # Tokenize camelCase component name: split on uppercase boundaries → lowercase
  COMP_TOKENS=$(echo "$COMP_NAME" | sed 's/\([a-z]\)\([A-Z]\)/\1 \2/g' | tr '[:upper:]' '[:lower:]')
  IFS=' ' read -ra TOKENS <<< "$COMP_TOKENS"
  TOTAL=${#TOKENS[@]}

  if [ "$TOTAL" -eq 0 ]; then
    continue
  fi

  # Count matched tokens
  MATCHED=0
  for qt in "${QUERY_TOKENS[@]}"; do
    for ct in "${TOKENS[@]}"; do
      if [ "$qt" = "$ct" ]; then
        MATCHED=$((MATCHED + 1))
        break
      fi
    done
  done

  # Calculate score
  SCORE=$(( (MATCHED * 100) / TOTAL ))

  # Determine confidence tier
  if [ "$SCORE" -ge 70 ]; then
    CONFIDENCE="high"
  elif [ "$SCORE" -ge 40 ]; then
    CONFIDENCE="medium"
  else
    CONFIDENCE="low"
  fi

  # Only include medium and high confidence matches
  if [ "$SCORE" -ge 40 ]; then
    if [ "$FIRST" = true ]; then
      FIRST=false
    else
      RESULTS+=","
    fi
    RESULTS+="{\"name\":\"$COMP_NAME\",\"score\":$SCORE,\"confidence\":\"$CONFIDENCE\"}"
  fi
done < <(find "$PKG_DIR" -path "*/lwc/*" -type d -maxdepth 5 | grep -v "__tests__")

RESULTS+="]"

# Sort by score descending (using python for JSON sorting)
echo "$RESULTS" | python3 -c "
import json, sys
data = json.load(sys.stdin)
data.sort(key=lambda x: x['score'], reverse=True)
print(json.dumps(data, indent=2))
" 2>/dev/null || echo "$RESULTS"
