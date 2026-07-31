#!/usr/bin/env bash
# Verify a resolved UI bundle directory is actually scaffolded before any
# rule in this skill applies.
# Usage: check-preconditions.sh <bundle-dir>
#   <bundle-dir> is the path printed by resolve-ui-bundle.sh.
#
# Exit 0 if the bundle is scaffolded (src/appLayout.tsx, src/routes.tsx, and
# src/components/ui/ all present).
# Exit 1 with the missing pieces listed if the bundle is a fresh SFDX
# project, a non-UI-bundle React project, or only partially scaffolded —
# the caller must stop and redirect the user to
# experience-ui-bundle-app-coordinate (or experience-ui-bundle-metadata-generate)
# instead of falling back to generic React knowledge.

set -uo pipefail

BUNDLE_DIR="${1:-}"

if [ -z "$BUNDLE_DIR" ] || [ ! -d "$BUNDLE_DIR" ]; then
  echo "ERROR: check-preconditions.sh requires a valid bundle directory argument" >&2
  exit 1
fi

MISSING=()
[ -f "$BUNDLE_DIR/src/appLayout.tsx" ] || MISSING+=("src/appLayout.tsx")
[ -f "$BUNDLE_DIR/src/routes.tsx" ] || MISSING+=("src/routes.tsx")
[ -d "$BUNDLE_DIR/src/components/ui" ] || MISSING+=("src/components/ui/")

if [ "${#MISSING[@]}" -gt 0 ]; then
  echo "ERROR: $BUNDLE_DIR is not a scaffolded UI bundle. Missing:" >&2
  printf '  - %s\n' "${MISSING[@]}" >&2
  echo "Stop here. Tell the user the bundle isn't scaffolded yet and direct them to experience-ui-bundle-app-coordinate (or experience-ui-bundle-metadata-generate) to scaffold it first." >&2
  exit 1
fi

echo "SUCCESS: $BUNDLE_DIR is scaffolded (src/appLayout.tsx, src/routes.tsx, src/components/ui/ present)"
exit 0
