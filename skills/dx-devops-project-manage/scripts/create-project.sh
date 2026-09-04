#!/usr/bin/env bash
# Deterministically create a DevOps Center project, idempotently: if a project
# with the same name already exists, return its ID instead of creating a
# duplicate. Verifies success by re-reading the project list, so it never
# depends on the create command's own output envelope.
# Usage:
#   scripts/create-project.sh <name> [description] [target-org]
# Prints "EXISTING <id>" or "CREATED <id>" on success; exits 2 on error.

set -euo pipefail

NAME="${1:?Usage: create-project.sh <name> [description] [target-org]}"
DESC="${2:-}"
ORG="${3:-}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Idempotency preflight. list-projects.sh --resolve exits 0 (found), 3 (no such
# project), or 2 (auth / CLI / JSON failure). Only a clean "not found" (3) is
# safe to proceed on — any other failure means the list could not be read, so we
# must abort rather than risk a duplicate or writing to an unreadable org.
err=$(mktemp); rc=0
EXISTING=$("$HERE/list-projects.sh" --resolve "$NAME" "$ORG" 2>"$err") || rc=$?
if [ "$rc" -eq 0 ]; then
  rm -f "$err"; echo "EXISTING $EXISTING"; exit 0
elif [ "$rc" -ne 3 ]; then
  echo "ERROR: idempotency preflight failed (exit $rc); aborting create to avoid a duplicate or writing to an org whose project list could not be read: $(tr '\n' ' ' <"$err")" >&2
  rm -f "$err"; exit "$rc"
fi
rm -f "$err"
# rc == 3: no existing project with this name — safe to create.

flag=(); [ -n "$ORG" ] && flag=(--target-org "$ORG")
dflag=(); [ -n "$DESC" ] && dflag=(--description "$DESC")

err=$(mktemp); rc=0
sf devops project create --name "$NAME" "${dflag[@]+"${dflag[@]}"}" "${flag[@]+"${flag[@]}"}" --json >/dev/null 2>"$err" || rc=$?
if [ "$rc" -ne 0 ]; then
  echo "ERROR: project create failed (sf exited $rc): $(tr '\n' ' ' <"$err")" >&2
  rm -f "$err"; exit 2
fi
rm -f "$err"

# Verify by re-reading the list (authoritative .result.projects[] envelope).
if ID=$("$HERE/list-projects.sh" --resolve "$NAME" "$ORG"); then
  echo "CREATED $ID"; exit 0
fi
echo "ERROR: create reported success but project '$NAME' is not in the project list" >&2
exit 2
