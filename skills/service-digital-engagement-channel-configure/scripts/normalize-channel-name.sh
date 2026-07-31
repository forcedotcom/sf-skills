#!/bin/bash
# Derives a Metadata API-safe file name from a channel label.
# Usage: normalize-channel-name.sh "<LABEL>"
# Exits non-zero and prints violations if the result doesn't match ^[a-zA-Z][a-zA-Z0-9_]*$

LABEL="$1"
if [ -z "$LABEL" ]; then
  echo "Error: No label provided." >&2
  exit 1
fi

NAME=$(echo "$LABEL" | sed 's/[^a-zA-Z0-9]/_/g' | sed 's/__*/_/g' | sed 's/^_//;s/_$//' | cut -c1-80)

if ! echo "$NAME" | grep -qE '^[a-zA-Z][a-zA-Z0-9_]*$'; then
  echo "Error: Derived name '$NAME' violates pattern ^[a-zA-Z][a-zA-Z0-9_]*$" >&2
  exit 1
fi

if [ ${#NAME} -gt 80 ]; then
  echo "Error: Derived name '$NAME' exceeds 80 characters" >&2
  exit 1
fi

echo "$NAME"
