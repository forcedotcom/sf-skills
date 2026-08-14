#!/bin/bash
# Counts remaining sharing rule elements in a .sharingRules-meta.xml file.
# Usage: count-remaining-rules.sh <file>
# Output: integer count of rule elements found
# Exit behavior: exits 0 with count; exits 1 if file not found, xmllint missing, or XML parse fails

FILE="$1"
if [ ! -f "$FILE" ]; then
  echo "Error: File not found: $FILE" >&2
  exit 1
fi

if ! command -v xmllint &>/dev/null; then
  echo "Error: xmllint is not installed or not in PATH" >&2
  exit 1
fi

XMLLINT_ERR=$(mktemp)
COUNT=$(xmllint --xpath 'count(//*[local-name()="sharingCriteriaRules" or local-name()="sharingOwnerRules" or local-name()="sharingGuestRules"])' "$FILE" 2>"$XMLLINT_ERR")
STATUS=$?
if [ $STATUS -ne 0 ]; then
  echo "Error: xmllint failed to parse $FILE (exit $STATUS): $(cat "$XMLLINT_ERR")" >&2
  rm -f "$XMLLINT_ERR"
  exit 1
fi
rm -f "$XMLLINT_ERR"

if ! [[ "$COUNT" =~ ^[0-9]+\.?[0-9]*$ ]]; then
  echo "Error: xmllint returned non-numeric output for $FILE: $COUNT" >&2
  exit 1
fi

echo "${COUNT%%.*}"
