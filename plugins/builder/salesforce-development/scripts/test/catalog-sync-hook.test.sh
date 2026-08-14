#!/bin/bash
# Tests for sync-discovery-catalog.sh — the pre-commit / pre-merge-commit hook that
# regenerates catalog/discovery.json when its inputs change, so the artifact can't
# drift from the skills it advertises.
#
# Two layers: (1) the input MATCHER (check-only mode, no git side effects) decides
# regen-vs-skip on the right paths; (2) the hooks are actually WIRED to the script;
# (3) an end-to-end regen run leaves the (already-current) catalog current.
#
# Run: bash plugins/builder/salesforce-development/scripts/test/catalog-sync-hook.test.sh
set -uo pipefail

REPO="$(cd "$(dirname "$0")/../../../../.." && pwd)"
SYNC="plugins/builder/salesforce-development/scripts/sync-discovery-catalog.sh"
PASS=0
FAIL=0

cd "$REPO"

# decide <expected: regen-needed|skip> <desc> <newline-separated staged paths>
decide() {
  local expected="$1" desc="$2" files="$3" got
  got=$(CATALOG_SYNC_CHECK_ONLY=1 CATALOG_SYNC_FILES="$files" sh "$SYNC")
  if [ "$got" = "$expected" ]; then
    PASS=$((PASS + 1)); printf '  ok   %-52s → %s\n' "$desc" "$got"
  else
    FAIL=$((FAIL + 1)); printf '  FAIL %-52s → got "%s" want "%s"\n' "$desc" "$got" "$expected"
  fi
}

echo "sync-discovery-catalog — input matcher (check-only)"

# Inputs that DO feed build_catalog → must regenerate.
decide regen-needed "foundation skill SKILL.md" \
  "plugins/builder/salesforce-development/skills/agentforce-generate/SKILL.md"
decide regen-needed "foundation skill reference file (tree hash)" \
  "plugins/builder/salesforce-development/skills/agentforce-generate/references/x.md"
decide regen-needed "public release manifest" \
  "plugins/builder/salesforce-development/catalog/public-release-manifest.json"
decide regen-needed "the generator itself" \
  "plugins/builder/salesforce-development/scripts/discovery_catalog.py"
decide regen-needed "the registry (source_variant/tree hash)" \
  "plugins/builder/salesforce-development/scripts/capability_registry.py"
decide regen-needed "mixed: unrelated + one foundation skill" \
  "README.md
plugins/builder/salesforce-development/skills/agentforce-observe/SKILL.md"

# Paths that do NOT affect the catalog → must skip (build_catalog ignores repo_root,
# so flat skills/ don't count; nor do unrelated plugin files).
decide skip "flat skills/ SKILL.md (not a catalog input)" \
  "skills/platform-apex-generate/SKILL.md"
decide skip "unrelated plugin script (deploy-gate)" \
  "plugins/builder/salesforce-development/scripts/sf-deploy-gate"
decide skip "repo docs" \
  "README.md
docs/design/decisions.md"
decide skip "no staged files" ""

echo ""
echo "sync-discovery-catalog — hooks wired"

for hook in .husky/pre-commit .husky/pre-merge-commit; do
  if grep -q "sync-discovery-catalog.sh" "$hook"; then
    PASS=$((PASS + 1)); printf '  ok   %-52s → wired\n' "$hook invokes the sync script"
  else
    FAIL=$((FAIL + 1)); printf '  FAIL %-52s → NOT wired\n' "$hook invokes the sync script"
  fi
done

echo ""
echo "sync-discovery-catalog — end-to-end regen keeps catalog current"

# Force the regen branch via a foundation-skill path. Run against an isolated
# temporary index seeded with the intentional worktree catalog: this test exercises
# the hook's `git add` without ever staging or rewriting a developer's real index.
real_tree_before=$(git write-tree)
index_path=$(git rev-parse --git-path index)
tmp_index=$(mktemp)
cp "$index_path" "$tmp_index"
GIT_INDEX_FILE="$tmp_index" git add plugins/builder/salesforce-development/catalog/discovery.json
before=$(GIT_INDEX_FILE="$tmp_index" git rev-parse ":plugins/builder/salesforce-development/catalog/discovery.json" 2>/dev/null || echo none)
out=$(GIT_INDEX_FILE="$tmp_index" CATALOG_SYNC_FILES="plugins/builder/salesforce-development/skills/agentforce-generate/SKILL.md" sh "$SYNC")
after=$(GIT_INDEX_FILE="$tmp_index" git rev-parse ":plugins/builder/salesforce-development/catalog/discovery.json" 2>/dev/null || echo none)
real_tree_after=$(git write-tree)
rm -f "$tmp_index"
if printf '%s' "$out" | grep -q "regenerated and staged" \
   && [ "$before" = "$after" ] \
   && [ "$real_tree_before" = "$real_tree_after" ]; then
  PASS=$((PASS + 1)); printf '  ok   %-52s → regenerated, current, real index untouched\n' "end-to-end regen"
else
  FAIL=$((FAIL + 1)); printf '  FAIL %-52s → out=%s before=%s after=%s real-before=%s real-after=%s\n' \
    "end-to-end regen" "$out" "$before" "$after" "$real_tree_before" "$real_tree_after"
fi

echo ""
echo "sync-discovery-catalog — hostile CRLF git config"

# Reproduce a Windows-style checkout policy even on Linux CI. The sync script
# must override both autocrlf and eol while materializing its index snapshot.
real_tree_before=$(git write-tree)
index_path=$(git rev-parse --git-path index)
tmp_index=$(mktemp)
cp "$index_path" "$tmp_index"
GIT_INDEX_FILE="$tmp_index" git add plugins/builder/salesforce-development/catalog/discovery.json
before=$(GIT_INDEX_FILE="$tmp_index" git rev-parse ":plugins/builder/salesforce-development/catalog/discovery.json")
out=$(GIT_CONFIG_COUNT=2 \
  GIT_CONFIG_KEY_0=core.autocrlf GIT_CONFIG_VALUE_0=true \
  GIT_CONFIG_KEY_1=core.eol GIT_CONFIG_VALUE_1=crlf \
  GIT_INDEX_FILE="$tmp_index" \
  CATALOG_SYNC_FILES="plugins/builder/salesforce-development/skills/agentforce-generate/SKILL.md" \
  sh "$SYNC")
after=$(GIT_INDEX_FILE="$tmp_index" git rev-parse ":plugins/builder/salesforce-development/catalog/discovery.json")
real_tree_after=$(git write-tree)
rm -f "$tmp_index"
if printf '%s' "$out" | grep -q "regenerated and staged" \
   && [ "$before" = "$after" ] \
   && [ "$real_tree_before" = "$real_tree_after" ]; then
  PASS=$((PASS + 1)); printf '  ok   %-52s → canonical LF catalog preserved\n' "CRLF checkout policy"
else
  FAIL=$((FAIL + 1)); printf '  FAIL %-52s → out=%s before=%s after=%s real-before=%s real-after=%s\n' \
    "CRLF checkout policy" "$out" "$before" "$after" "$real_tree_before" "$real_tree_after"
fi

echo ""
echo "  $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
