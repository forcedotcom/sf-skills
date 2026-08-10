#!/bin/sh
# sync-discovery-catalog.sh — keep catalog/discovery.json in sync with its inputs.
#
# The discovery catalog is a GENERATED artifact (discovery_catalog.py --generate).
# build_catalog() derives it from exactly two things (repo_root is ignored):
#   1. the public manifest  catalog/public-release-manifest.json
#   2. the plugin's foundation skills  skills/**  (source_variant hashes the WHOLE
#      skill tree, so ANY file under a foundation skill dir changes the output)
# plus the generator/registry code itself. When any of those is staged, regenerate
# and re-stage the artifact so it can never drift out of sync.
#
# Wired into .husky/pre-commit (authoring) and .husky/pre-merge-commit (the drift a
# plain `git merge develop` caused when it pulled in others' SKILL.md edits). The
# catalog's "is current" contract test (test_discovery_catalog.py, run by
# `npm run test:gates` in CI) is the HARD guarantee; this hook just keeps authors
# and mergers from ever hitting that red check.
#
# Test hooks (no git side effects): set CATALOG_SYNC_FILES to a newline-separated
# path list to bypass `git diff`, and CATALOG_SYNC_CHECK_ONLY=1 to print the
# decision (regen-needed|skip) instead of regenerating/staging.
set -e

PLUGIN="plugins/builder/salesforce-development"
GENERATOR="${PLUGIN}/scripts/discovery_catalog.py"
ARTIFACT="${PLUGIN}/catalog/discovery.json"

# Paths whose change can alter the generated catalog.
PATTERN="^${PLUGIN}/skills/|^${PLUGIN}/catalog/public-release-manifest\.json$|^${PLUGIN}/scripts/(discovery_catalog|capability_registry)\.py$"

if [ "${CATALOG_SYNC_FILES+x}" = "x" ]; then
  changed="$CATALOG_SYNC_FILES"
else
  changed="$(git diff --cached --name-only --diff-filter=ACMRD)"
fi

if ! printf '%s\n' "$changed" | grep -qE "$PATTERN"; then
  [ "${CATALOG_SYNC_CHECK_ONLY:-}" = "1" ] && echo "skip"
  exit 0
fi

if [ "${CATALOG_SYNC_CHECK_ONLY:-}" = "1" ]; then
  echo "regen-needed"
  exit 0
fi

python3 "$GENERATOR" --generate >/dev/null
git add "$ARTIFACT"
echo "sync-discovery-catalog: regenerated and staged ${ARTIFACT}"
