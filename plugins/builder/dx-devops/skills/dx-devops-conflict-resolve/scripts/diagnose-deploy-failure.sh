#!/usr/bin/env bash
# diagnose-deploy-failure.sh — Classify a DevOps Center promotion/deploy failure
# and decide whether a FULL PROMOTION can fix it.
#
# DevOps Center promotes by deploying a work item's feature branch into the target
# stage branch. A promotion can fail for two broad reasons:
#   1. Merge conflict  — the branches conflict; re-promoting will not help. Resolve
#      the conflict first (scripts/detect-conflicts.sh + the resolve workflow).
#   2. Deploy error    — frequently a MISSING DEPENDENCY: the deployed set
#      references a component it does not include. A FULL promotion (promote ALL
#      pending changes for the work item, not a partial/selective set) can fix this
#      ONLY if the missing component actually exists on the feature branch.
#
# This script parses the error text; when it finds a missing dependency it checks,
# with `git show`, whether that component's source file is present on the branch.
#
# Usage:   diagnose-deploy-failure.sh <error-file|-> <feature-branch> [target-branch] [remote]
#          Pass '-' as the first argument to read the error text from stdin.
# Example: sf project deploy start ... 2>&1 \
#            | scripts/diagnose-deploy-failure.sh - feature/WI-101 uat origin
#
# Output: key=value lines the agent parses —
#   REASON, CAN_FULL_PROMOTION_FIX, RECOMMENDATION, and when a dependency is parsed
#   MISSING_DEPENDENCY_TYPE / MISSING_DEPENDENCY_NAME / IN_FEATURE_BRANCH
#   (+ IN_TARGET_BRANCH when a target branch is given).
#
# Exit codes:
#   0  full promotion CAN fix   — missing component exists on the feature branch
#   2  merge conflict           — resolve the conflict, do not just re-promote
#   3  dependency not on branch  — component must be added before promoting
#   4  no dependency parsed      — inspect the error; a full promotion likely won't help
#   1  usage / environment error
set -euo pipefail

ERR_SRC="${1:?usage: diagnose-deploy-failure.sh <error-file|-> <feature-branch> [target-branch] [remote]}"
FEATURE="${2:?usage: diagnose-deploy-failure.sh <error-file|-> <feature-branch> [target-branch] [remote]}"
TARGET="${3:-}"
REMOTE="${4:-origin}"

# Read the error text from a file or stdin.
if [ "$ERR_SRC" = "-" ]; then
  ERR="$(cat)"
elif [ -f "$ERR_SRC" ]; then
  ERR="$(cat "$ERR_SRC")"
else
  echo "ERROR: error source '$ERR_SRC' is not a readable file (use '-' to read stdin)." >&2
  exit 1
fi

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "ERROR: not inside a git repository." >&2
  exit 1
fi

shopt -s nocasematch

# 1. Merge conflict? A full promotion cannot fix it — resolve the conflict instead.
if [[ "$ERR" =~ (MERGE_CONFLICT|CONFLICTS:) ]]; then
  echo "REASON=merge_conflict"
  echo "CAN_FULL_PROMOTION_FIX=false"
  echo "RECOMMENDATION=This is a merge conflict, not a missing dependency. Resolve it with the conflict workflow (scripts/detect-conflicts.sh, then merge/resolve/commit/push the feature branch), then re-promote."
  exit 2
fi

# 2. Try to parse a missing dependency (type + name) from the error text.
#    Order mirrors the DevOps Center provider: "Variable does not exist" first.
DEP_TYPE=""
DEP_NAME=""
if [[ "$ERR" =~ Variable[[:space:]]+does[[:space:]]+not[[:space:]]+exist:[[:space:]]*([A-Za-z0-9_]+) ]]; then
  DEP_TYPE="ApexClass"; DEP_NAME="${BASH_REMATCH[1]}"
elif [[ "$ERR" =~ no[[:space:]]+(ApexClass|ApexTrigger|ApexPage|CustomObject|Flow)[[:space:]]+named[[:space:]]+([A-Za-z0-9_]+)[[:space:]]+found ]]; then
  DEP_TYPE="${BASH_REMATCH[1]}"; DEP_NAME="${BASH_REMATCH[2]}"
elif ! [[ "$ERR" =~ (Variable[[:space:]]does[[:space:]]not[[:space:]]exist|Problem:) ]] \
     && [[ "$ERR" =~ Type:[[:space:]]*(ApexClass|ApexTrigger|ApexPage|Profile|CustomObject|Flow) ]]; then
  DEP_TYPE="${BASH_REMATCH[1]}"
  if [[ "$ERR" =~ Component:[[:space:]]*([A-Za-z0-9_]+) ]]; then
    DEP_NAME="${BASH_REMATCH[1]}"
  else
    DEP_TYPE=""   # need both type and name to act
  fi
fi

# Canonicalize the metadata type (nocasematch may capture any casing from the error).
canon_type() {
  case "$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')" in
    apexclass)    echo "ApexClass" ;;
    apextrigger)  echo "ApexTrigger" ;;
    apexpage)     echo "ApexPage" ;;
    profile)      echo "Profile" ;;
    customobject) echo "CustomObject" ;;
    flow)         echo "Flow" ;;
    *)            echo "" ;;
  esac
}

CANON=""
[ -n "$DEP_TYPE" ] && CANON="$(canon_type "$DEP_TYPE")"

if [ -z "$CANON" ] || [ -z "$DEP_NAME" ]; then
  echo "REASON=no_dependency_parsed"
  echo "CAN_FULL_PROMOTION_FIX=false"
  echo "RECOMMENDATION=Could not identify a missing component from the error. Inspect the full deploy error and fix the underlying metadata/test issue, then re-promote. A full promotion is unlikely to help unless the failure is a missing dependency."
  exit 4
fi

# Candidate source paths for the component (standard SFDX layouts).
paths_for() {
  local t="$1" n="$2"
  case "$t" in
    ApexClass)    printf '%s\n' "force-app/main/default/classes/$n.cls" "main/default/classes/$n.cls" "classes/$n.cls" ;;
    ApexTrigger)  printf '%s\n' "force-app/main/default/triggers/$n.trigger" "main/default/triggers/$n.trigger" ;;
    ApexPage)     printf '%s\n' "force-app/main/default/pages/$n.page" "main/default/pages/$n.page" ;;
    Profile)      printf '%s\n' "force-app/main/default/profiles/$n.profile-meta.xml" "main/default/profiles/$n.profile-meta.xml" ;;
    CustomObject) printf '%s\n' "force-app/main/default/objects/$n/$n.object-meta.xml" "main/default/objects/$n/$n.object-meta.xml" ;;
    Flow)         printf '%s\n' "force-app/main/default/flows/$n.flow-meta.xml" "main/default/flows/$n.flow-meta.xml" ;;
  esac
}

# Is at least one candidate path present in the branch? Try the local ref, then the remote ref.
present_in_branch() {
  local branch="$1" t="$2" n="$3" p
  while IFS= read -r p; do
    [ -z "$p" ] && continue
    if git show "$branch:$p" >/dev/null 2>&1 || git show "$REMOTE/$branch:$p" >/dev/null 2>&1; then
      return 0
    fi
  done <<EOF
$(paths_for "$t" "$n")
EOF
  return 1
}

IN_FEATURE=false
if present_in_branch "$FEATURE" "$CANON" "$DEP_NAME"; then IN_FEATURE=true; fi

IN_TARGET=""
if [ -n "$TARGET" ]; then
  if present_in_branch "$TARGET" "$CANON" "$DEP_NAME"; then IN_TARGET=true; else IN_TARGET=false; fi
fi

echo "MISSING_DEPENDENCY_TYPE=$CANON"
echo "MISSING_DEPENDENCY_NAME=$DEP_NAME"
echo "IN_FEATURE_BRANCH=$IN_FEATURE"
[ -n "$IN_TARGET" ] && echo "IN_TARGET_BRANCH=$IN_TARGET"

if [ "$IN_FEATURE" = true ]; then
  echo "REASON=dependency_in_feature_branch"
  echo "CAN_FULL_PROMOTION_FIX=true"
  echo "RECOMMENDATION=The missing component $CANON '$DEP_NAME' exists on the feature branch but was not in the deployed set. A FULL promotion (promote all pending changes for this work item, not a partial set) should include it and fix the failure. Confirm with the user, then re-promote as a full promotion via dx-devops-promote."
  exit 0
fi

echo "REASON=dependency_not_in_feature_branch"
echo "CAN_FULL_PROMOTION_FIX=false"
echo "RECOMMENDATION=The missing component $CANON '$DEP_NAME' is NOT on the feature branch, so promoting the branch cannot supply it. Add and commit the missing $CANON to the work item's feature branch (or include the work item that owns it), then re-promote."
exit 3
