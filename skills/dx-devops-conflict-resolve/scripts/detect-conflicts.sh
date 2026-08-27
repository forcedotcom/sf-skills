#!/usr/bin/env bash
# detect-conflicts.sh — Non-destructively detect Git merge conflicts between a
# DevOps Center work item feature branch and a target pipeline-stage branch.
#
# DevOps Center is Git-backed: it promotes the work item's feature branch into
# the target stage branch. This script trial-merges the target INTO the feature
# branch WITHOUT committing, records the conflicting files, then aborts the trial
# so the working tree is left exactly as it was found.
#
# Usage:   detect-conflicts.sh <feature-branch> <target-branch> [remote]
# Example: detect-conflicts.sh feature/WI-101 uat origin
#
# Exit codes:
#   0  clean merge  — no conflicts, safe to promote
#   2  conflicts    — the conflicting files are printed to stdout
#   1  error        — dirty tree, unknown branch, or fetch failure (stderr)
set -euo pipefail

FEATURE="${1:?usage: detect-conflicts.sh <feature-branch> <target-branch> [remote]}"
TARGET="${2:?usage: detect-conflicts.sh <feature-branch> <target-branch> [remote]}"
REMOTE="${3:-origin}"

# Must be inside a git work tree.
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "ERROR: not inside a git repository." >&2
  exit 1
fi

# Refuse to run with a dirty working tree — a trial merge could clobber changes.
if [ -n "$(git status --porcelain)" ]; then
  echo "ERROR: working tree is not clean. Commit or stash changes before detecting conflicts." >&2
  exit 1
fi

# Remember where to return to, so detection leaves the checkout untouched.
ORIG_REF="$(git symbolic-ref --quiet --short HEAD || git rev-parse HEAD)"

cleanup() {
  git merge --abort >/dev/null 2>&1 || git reset --merge >/dev/null 2>&1 || true
  git checkout --quiet "$ORIG_REF" >/dev/null 2>&1 || true
}
trap cleanup EXIT

if ! git fetch "$REMOTE" >/dev/null 2>&1; then
  echo "ERROR: git fetch $REMOTE failed." >&2
  exit 1
fi

# Check out the feature branch as a tracking branch if it is not local yet.
if ! git checkout --quiet "$FEATURE" >/dev/null 2>&1; then
  if ! git checkout --quiet -b "$FEATURE" "$REMOTE/$FEATURE" >/dev/null 2>&1; then
    echo "ERROR: cannot check out feature branch '$FEATURE' (local or $REMOTE/$FEATURE)." >&2
    exit 1
  fi
fi

# Confirm the target branch exists on the remote.
if ! git rev-parse --verify --quiet "$REMOTE/$TARGET" >/dev/null; then
  echo "ERROR: target branch '$REMOTE/$TARGET' not found." >&2
  exit 1
fi

# Trial-merge the target INTO the feature branch, without committing. Capture the
# merge exit status explicitly — a non-zero status means either merge conflicts
# (unmerged paths present) OR a non-conflict failure such as unrelated histories.
set +e
MERGE_OUT="$(git merge --no-commit --no-ff "$REMOTE/$TARGET" 2>&1)"
MERGE_STATUS=$?
set -e
CONFLICTS="$(git diff --name-only --diff-filter=U || true)"

# Trap-based cleanup aborts the trial merge and restores the original checkout.

# Real merge conflicts: unmerged paths exist. Report them and signal "conflicts".
if [ -n "$CONFLICTS" ]; then
  echo "CONFLICTS: merging $REMOTE/$TARGET into $FEATURE conflicts on these files:"
  printf '%s\n' "$CONFLICTS"
  exit 2
fi

# No unmerged paths but the merge still failed — a non-conflict error (e.g.
# unrelated histories). Never report CLEAN in this case; surface the error.
if [ "$MERGE_STATUS" -ne 0 ]; then
  echo "ERROR: git merge of $REMOTE/$TARGET into $FEATURE failed for a non-conflict reason:" >&2
  printf '%s\n' "$MERGE_OUT" >&2
  exit 1
fi

# Merge succeeded with no conflicts — safe to promote.
echo "CLEAN: no merge conflicts between $FEATURE and $REMOTE/$TARGET."
exit 0
