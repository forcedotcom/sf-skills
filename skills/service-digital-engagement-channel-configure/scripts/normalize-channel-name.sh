#!/bin/bash
# Derives a Metadata API-safe file name from a channel label.
# Usage: normalize-channel-name.sh "<LABEL>"
# Prints the name (max 80 chars). A label starting with a digit gets a "Ch_" prefix.
# Exits non-zero if nothing usable remains or the label exceeds 40 characters (masterLabel limit).

LABEL="$1"
if [ -z "$LABEL" ]; then
  echo "Error: No label provided." >&2
  exit 1
fi

if [ ${#LABEL} -gt 40 ]; then
  echo "Error: Label '$LABEL' exceeds 40 characters; ask for a shorter label." >&2
  exit 1
fi

NAME=$(printf '%s' "$LABEL" | sed 's/[^a-zA-Z0-9]/_/g' | sed 's/__*/_/g' | sed 's/^_//;s/_$//' | cut -c1-80)

case "$NAME" in
  [0-9]*) NAME="Ch_$NAME" ;;
esac

if ! printf '%s' "$NAME" | grep -qE '^[a-zA-Z][a-zA-Z0-9_]*$'; then
  echo "Error: Could not derive a valid name from '$LABEL'; ask for a label with letters." >&2
  exit 1
fi

echo "$NAME"
